"""
比特币实时价格显示应用
基于 Streamlit + CoinGecko API 实现

Features:
    - 实时显示比特币 USD 价格
    - 24h 涨跌幅与涨跌额展示
    - 手动刷新 + 自动刷新（基于 meta refresh，非阻塞）
    - 完善的异常处理与友好提示
"""

import requests
import streamlit as st
from datetime import datetime
from typing import Dict, Any

# ============ 常量配置 ============
COINGECKO_API_URL = "https://api.coingecko.com/api/v3/simple/price"
API_PARAMS = {
    "ids": "bitcoin",
    "vs_currencies": "usd",
    "include_24hr_change": "true",
    "include_24hr_vol": "true",
    "include_last_updated_at": "true",
}
REQUEST_TIMEOUT = 10           # API 请求超时（秒）
CACHE_TTL = 60                 # 数据缓存时长（秒）
AUTO_REFRESH_INTERVAL = 60     # 自动刷新间隔（秒）


# ============ 数据获取模块 ============
@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def fetch_bitcoin_price() -> Dict[str, Any]:
    """
    从 CoinGecko API 获取比特币实时价格数据。
    
    Returns:
        Dict[str, Any]: 包含价格、涨跌幅、涨跌额、成交量等信息
    
    Raises:
        requests.exceptions.Timeout: 请求超时
        requests.exceptions.HTTPError: HTTP 错误（含 429 限流）
        requests.exceptions.ConnectionError: 网络连接失败
        requests.exceptions.RequestException: 其他请求异常
        ValueError: API 返回数据格式异常
    
    Note:
        异常由调用方统一处理，本函数不返回 None。
    """
    response = requests.get(
        COINGECKO_API_URL,
        params=API_PARAMS,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    
    data = response.json()
    
    # 数据完整性校验
    if "bitcoin" not in data or "usd" not in data["bitcoin"]:
        raise ValueError("API 返回数据格式异常，缺少必要字段")
    
    btc_data = data["bitcoin"]
    current_price = btc_data["usd"]
    change_pct_24h = btc_data.get("usd_24h_change", 0.0)
    
    # 由当前价格和涨跌幅反推 24 小时前的价格，再计算涨跌额
    # 公式：previous = current / (1 + pct/100)
    # 注意：CoinGecko 返回的 pct 已经过四舍五入，反推会引入微小误差（通常 < $1），
    #      对于价格展示场景影响可忽略不计
    previous_price = current_price / (1 + change_pct_24h / 100)
    change_amount_24h = current_price - previous_price
    
    return {
        "price": current_price,
        "change_pct_24h": change_pct_24h,
        "change_amount_24h": change_amount_24h,
        "volume_24h": btc_data.get("usd_24h_vol", 0.0),
        "last_updated_at": btc_data.get("last_updated_at", 0),
    }


# ============ UI 渲染模块 ============
def render_header():
    """渲染页面头部"""
    st.title("₿ 比特币实时价格")
    st.caption(f"数据来源：CoinGecko API · 缓存 {CACHE_TTL} 秒")
    st.divider()


def render_price_card(data: Dict[str, Any]):
    """
    渲染主价格卡片。
    
    Args:
        data: 包含价格信息的字典
    """
    price = data["price"]
    change_pct = data["change_pct_24h"]
    change_amount = data["change_amount_24h"]
    
    # 主指标区：价格 + 涨跌额（两个卡片信息互补，不冗余）
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # 卡片 1：当前价格 + 24h 百分比涨跌（delta 自动着色）
        st.metric(
            label="💰 BTC / USD",
            value=f"${price:,.2f}",
            delta=f"{change_pct:+.2f}%  (24h)",
        )
    
    with col2:
        # 卡片 2：24h 涨跌金额（带符号显示） + 百分比 delta
        st.metric(
            label="📈 24h 涨跌额",
            value=f"${change_amount:+,.2f}",
            delta=f"{change_pct:+.2f}%",
        )
    
    # 趋势语义化提示（增强用户感知）
    if change_pct > 0:
        st.success(f"📈 比特币在过去 24 小时上涨了 {change_pct:.2f}%")
    elif change_pct < 0:
        st.warning(f"📉 比特币在过去 24 小时下跌了 {abs(change_pct):.2f}%")
    else:
        st.info("➡️ 比特币过去 24 小时价格基本持平")
    
    # 附加信息区
    st.divider()
    info_col1, info_col2 = st.columns(2)
    
    with info_col1:
        volume = data.get("volume_24h", 0)
        st.markdown(f"**24h 成交量**  \n${volume:,.0f}")
    
    with info_col2:
        last_updated = data.get("last_updated_at", 0)
        if last_updated:
            update_time = datetime.fromtimestamp(last_updated).strftime("%Y-%m-%d %H:%M:%S")
            st.markdown(f"**API 更新时间**  \n{update_time} (本地时间)")


def render_footer():
    """渲染页面底部：本地刷新时间 + 免责声明"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.caption(f"🕐 本地最后刷新：{now} (本地时间)")
    st.divider()
    st.caption("⚠️ **免责声明**：本应用数据仅供信息参考，不构成任何投资建议。"
               "加密货币市场波动剧烈，投资有风险，决策需谨慎。")


def render_error(error_msg: str, show_retry_hint: bool = True):
    """
    渲染错误提示。
    
    Args:
        error_msg: 错误描述
        show_retry_hint: 是否显示重试提示
    """
    st.error(f"❌ 数据获取失败：{error_msg}")
    if show_retry_hint:
        st.info("💡 请检查网络连接，或点击「刷新价格」按钮重新尝试。")


def handle_http_error(error: requests.exceptions.HTTPError):
    """
    针对不同 HTTP 状态码给出针对性提示。
    
    Args:
        error: HTTPError 异常对象
    """
    status_code = error.response.status_code
    if status_code == 429:
        render_error(
            "API 请求过于频繁，已触发限流。请稍等片刻后再刷新（CoinGecko 免费版限制约 10-30 次/分钟）",
            show_retry_hint=False,
        )
    elif 500 <= status_code < 600:
        render_error(f"CoinGecko 服务器暂时异常 (HTTP {status_code})，请稍后再试")
    else:
        render_error(f"API 请求失败 (HTTP {status_code})")


# ============ 主程序 ============
def main():
    """应用主入口"""
    # ⚠️ set_page_config 必须是第一个 Streamlit 命令
    st.set_page_config(
        page_title="Bitcoin Price Tracker",
        page_icon="₿",
        layout="centered",
    )
    
    render_header()
    
    # 刷新控制区
    col_btn, col_auto = st.columns([1, 2])
    
    with col_btn:
        refresh_clicked = st.button("🔄 刷新价格", use_container_width=True)
    
    with col_auto:
        auto_refresh = st.checkbox(
            f"自动刷新（每 {AUTO_REFRESH_INTERVAL} 秒）",
            value=False,
            help="启用后页面将自动刷新，可随时取消勾选立即生效",
        )
    
    # 自动刷新：使用浏览器原生 meta refresh，完全非阻塞
    # 用户取消勾选后，下次 rerun 时该 meta 标签不再注入，立即生效
    if auto_refresh:
        st.markdown(
            f'<meta http-equiv="refresh" content="{AUTO_REFRESH_INTERVAL}">',
            unsafe_allow_html=True,
        )
    
    # 用户点击刷新时清除缓存，强制重新请求
    if refresh_clicked:
        fetch_bitcoin_price.clear()
    
    # 数据获取与渲染（移除外层 spinner，避免缓存命中时的"假加载"闪烁）
    try:
        data = fetch_bitcoin_price()
        render_price_card(data)
        render_footer()
    
    except requests.exceptions.Timeout:
        render_error(f"请求超时（>{REQUEST_TIMEOUT} 秒），请检查网络连接")
    except requests.exceptions.ConnectionError:
        render_error("网络连接失败，请检查您的网络后重试")
    except requests.exceptions.HTTPError as e:
        handle_http_error(e)
    except requests.exceptions.RequestException as e:
        render_error(f"请求异常：{str(e)}")
    except ValueError as e:
        render_error(f"数据解析失败：{str(e)}")
    except Exception as e:
        # 兜底异常，避免应用崩溃
        render_error(f"未知错误：{str(e)}")


if __name__ == "__main__":
    main()