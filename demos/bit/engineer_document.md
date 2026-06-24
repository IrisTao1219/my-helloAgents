根据产品需求分析，我将按照 Phase 1 + Phase 2 的优先级实现这个应用，确保 MVP 功能完整且体验良好。

## 技术方案确认

- **数据源**：CoinGecko API（免费、稳定、无需 Key）
- **缓存策略**：`@st.cache_data(ttl=60)` 避免频繁请求
- **错误处理**：分层捕获（网络异常、超时、数据格式异常）
- **UI 核心**：使用 `st.metric()` 实现自带涨跌色的指标卡

## 完整代码实现

```python
"""
比特币实时价格显示应用
基于 Streamlit + CoinGecko API 实现
"""

import streamlit as st
import requests
from datetime import datetime
from typing import Optional, Dict, Any

# ============ 常量配置 ============
COINGECKO_API_URL = "https://api.coingecko.com/api/v3/simple/price"
API_PARAMS = {
    "ids": "bitcoin",
    "vs_currencies": "usd",
    "include_24hr_change": "true",
    "include_24hr_vol": "true",
    "include_last_updated_at": "true",
}
REQUEST_TIMEOUT = 10  # 秒
CACHE_TTL = 60        # 秒，缓存时长


# ============ 数据获取模块 ============
@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def fetch_bitcoin_price() -> Optional[Dict[str, Any]]:
    """
    从 CoinGecko API 获取比特币实时价格数据
    
    Returns:
        dict: 包含价格、24h涨跌幅、成交量等信息的字典
        None: 请求失败时返回 None（异常由上层处理）
    
    Raises:
        requests.exceptions.Timeout: 请求超时
        requests.exceptions.RequestException: 网络异常
        ValueError: 数据格式异常
    """
    response = requests.get(
        COINGECKO_API_URL,
        params=API_PARAMS,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()  # HTTP 4xx/5xx 抛出异常
    
    data = response.json()
    
    # 数据完整性校验
    if "bitcoin" not in data or "usd" not in data["bitcoin"]:
        raise ValueError("API 返回数据格式异常")
    
    btc_data = data["bitcoin"]
    current_price = btc_data["usd"]
    change_pct_24h = btc_data.get("usd_24h_change", 0.0)
    
    # 由当前价格和涨跌幅反推 24 小时前的价格，再计算涨跌额
    # 公式：previous = current / (1 + pct/100)
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
    st.set_page_config(
        page_title="Bitcoin Price Tracker",
        page_icon="₿",
        layout="centered",
    )
    st.title("₿ 比特币实时价格")
    st.caption("数据来源：CoinGecko API · 缓存 60 秒")
    st.divider()


def render_price_card(data: Dict[str, Any]):
    """
    渲染主价格卡片
    
    Args:
        data: 包含价格信息的字典
    """
    price = data["price"]
    change_pct = data["change_pct_24h"]
    change_amount = data["change_amount_24h"]
    
    # 主价格 + 24h 涨跌幅（st.metric 自动根据 delta 正负显示绿/红）
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.metric(
            label="💰 BTC / USD",
            value=f"${price:,.2f}",
            delta=f"{change_pct:+.2f}%  (24h)",
        )
    
    with col2:
        st.metric(
            label="📈 24h 涨跌额",
            value=f"${abs(change_amount):,.2f}",
            delta=f"${change_amount:+,.2f}",
        )
    
    # 附加信息
    st.divider()
    info_col1, info_col2 = st.columns(2)
    
    with info_col1:
        volume = data.get("volume_24h", 0)
        st.markdown(f"**24h 成交量**  \n${volume:,.0f}")
    
    with info_col2:
        last_updated = data.get("last_updated_at", 0)
        if last_updated:
            update_time = datetime.fromtimestamp(last_updated).strftime("%Y-%m-%d %H:%M:%S")
            st.markdown(f"**API 更新时间**  \n{update_time}")


def render_footer():
    """渲染页面底部，显示本地刷新时间"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.caption(f"🕐 本地最后刷新：{now}")


def render_error(error_msg: str):
    """渲染错误提示"""
    st.error(f"❌ 数据获取失败：{error_msg}")
    st.info("💡 请检查网络连接，或稍后重试。点击下方按钮可重新尝试。")


# ============ 主程序 ============
def main():
    """应用主入口"""
    render_header()
    
    # 刷新控制区
    col_btn, col_auto = st.columns([1, 2])
    
    with col_btn:
        refresh_clicked = st.button("🔄 刷新价格", use_container_width=True)
    
    with col_auto:
        auto_refresh = st.checkbox("自动刷新（每 60 秒）", value=False)
    
    # 用户点击刷新时清除缓存，强制重新请求
    if refresh_clicked:
        fetch_bitcoin_price.clear()
    
    # 数据获取与渲染
    with st.spinner("正在获取最新价格数据..."):
        try:
            data = fetch_bitcoin_price()
            
            if data is None:
                render_error("未能获取到有效数据")
                return
            
            render_price_card(data)
            render_footer()
            
        except requests.exceptions.Timeout:
            render_error(f"请求超时（>{REQUEST_TIMEOUT}秒），请检查网络")
        except requests.exceptions.ConnectionError:
            render_error("网络连接失败，请检查您的网络")
        except requests.exceptions.HTTPError as e:
            render_error(f"API 服务异常 (HTTP {e.response.status_code})")
        except requests.exceptions.RequestException as e:
            render_error(f"请求异常：{str(e)}")
        except ValueError as e:
            render_error(f"数据解析失败：{str(e)}")
        except Exception as e:
            # 兜底异常，避免应用崩溃
            render_error(f"未知错误：{str(e)}")
    
    # 自动刷新逻辑（基于 Streamlit 的 rerun 机制）
    if auto_refresh:
        import time
        time.sleep(60)
        fetch_bitcoin_price.clear()
        st.rerun()


if __name__ == "__main__":
    main()
```

## 依赖安装

创建 `requirements.txt`：

```txt
streamlit>=1.28.0
requests>=2.31.0
```

安装并运行：

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 实现要点说明

### 1. 数据获取层
- **缓存机制**：`@st.cache_data(ttl=60)` 防止用户频繁刷新触发 API 限流
- **超时控制**：10 秒超时，避免应用卡死
- **数据校验**：检查 API 返回结构，防止 KeyError

### 2. 涨跌额计算
CoinGecko API 只返回涨跌幅百分比，不直接返回涨跌额。我使用反推公式：
```
previous_price = current_price / (1 + pct/100)
change_amount = current_price - previous_price
```

### 3. 涨跌颜色
利用 `st.metric()` 的 `delta` 参数，Streamlit 会**自动**根据正负值显示绿色（↑）和红色（↓），无需手动处理 CSS。

### 4. 异常处理分层
针对不同异常类型（超时、连接、HTTP、数据格式）给出**针对性提示**，提升用户体验。

### 5. 刷新机制
- **手动刷新**：通过 `fetch_bitcoin_price.clear()` 清除缓存后触发重新请求
- **自动刷新**：使用 `time.sleep + st.rerun()` 实现（简单直接，适合 MVP）

### 6. 容错兜底
最外层 `except Exception` 捕获所有未预料异常，确保应用永不崩溃。