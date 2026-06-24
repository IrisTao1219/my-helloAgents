"""
美股实时行情查询应用
基于 Streamlit + yfinance (Yahoo Finance) 实现

Features:
    - 输入股票代码查询实时行情（默认 AAPL）
    - 6 只热门股票一键快选（响应式 2x3 布局）
    - 当日涨跌幅、涨跌额、成交量、市值、日内高低展示
    - 交易状态提示（盘中/盘前/盘后/休市）
    - 手动刷新 + 自动刷新（基于 meta refresh，非阻塞）
    - 完善的异常处理（含限流识别）
    - 性能优化：优先使用 fast_info，降级到 info
"""

from __future__ import annotations  # 类型注解兼容 Python 3.7+

import re
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

import streamlit as st
import yfinance as yf

# ============ 常量配置 ============
DEFAULT_SYMBOL = "AAPL"
POPULAR_SYMBOLS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA"]

# 美股代码格式：1-5 个大写字母，可选 .X 或 -X 后缀（兼容 BRK.B / BRK-B）
SYMBOL_PATTERN = re.compile(r"^[A-Z]{1,5}([.\-][A-Z]{1,2})?$")

CACHE_TTL = 60                 # 数据缓存时长（秒）
AUTO_REFRESH_INTERVAL = 60     # 自动刷新间隔（秒）


# ============ 工具函数 ============
def normalize_symbol(symbol: str) -> str:
    """规范化股票代码：去空格、转大写"""
    return symbol.strip().upper() if symbol else ""


def is_valid_symbol(symbol: str) -> bool:
    """
    校验股票代码格式合法性。
    
    支持：1-5 个大写字母，可选 .X 或 -X 后缀（如 AAPL、BRK.B、BRK-B）
    """
    return bool(symbol and SYMBOL_PATTERN.match(symbol))


def format_market_cap(market_cap: Optional[float]) -> str:
    """格式化市值（自动转换为 T/B/M 单位）"""
    if not market_cap or market_cap <= 0:
        return "暂无数据"
    if market_cap >= 1e12:
        return f"${market_cap / 1e12:.2f} T"
    if market_cap >= 1e9:
        return f"${market_cap / 1e9:.2f} B"
    if market_cap >= 1e6:
        return f"${market_cap / 1e6:.2f} M"
    return f"${market_cap:,.0f}"


def format_volume(volume: Optional[int]) -> str:
    """格式化成交量"""
    if not volume or volume <= 0:
        return "暂无数据"
    if volume >= 1e9:
        return f"{volume / 1e9:.2f} B"
    if volume >= 1e6:
        return f"{volume / 1e6:.2f} M"
    if volume >= 1e3:
        return f"{volume / 1e3:.2f} K"
    return f"{volume:,}"


def get_market_state_label(state: str) -> Tuple[str, str]:
    """
    将 yfinance 的 marketState 转为中文提示。
    
    Returns:
        (emoji+文案, 状态级别)：状态级别为 success/info/warning
    """
    mapping = {
        "REGULAR": ("🟢 盘中交易", "success"),
        "PRE": ("🟡 盘前交易", "info"),
        "POST": ("🟡 盘后交易", "info"),
        "POSTPOST": ("🟡 盘后交易", "info"),
        "CLOSED": ("🔴 美股休市（显示最近收盘价）", "warning"),
        "PREPRE": ("🔴 美股休市（显示最近收盘价）", "warning"),
    }
    return mapping.get(state, ("ℹ️ 交易状态未知", "info"))


def is_rate_limit_error(error: Exception) -> bool:
    """识别 yfinance 限流错误（401/429/Too Many Requests）"""
    error_str = str(error).lower()
    return any(keyword in error_str for keyword in ["401", "429", "too many", "rate limit"])


# ============ 数据获取模块 ============
@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def fetch_stock_data(symbol: str) -> Dict[str, Any]:
    """
    通过 yfinance 获取股票实时行情数据。
    
    优化策略：
        1. 优先使用 fast_info（快速、稳定，仅含核心价格字段）
        2. 降级使用 info（含公司名称、市值等元数据，但慢且不稳定）
        3. 最终兜底使用 history 历史数据
    
    Args:
        symbol: 股票代码（任意大小写，函数内会规范化）
    
    Returns:
        包含价格、涨跌、成交量、公司信息等字段的字典
    
    Raises:
        ValueError: 股票代码不存在或返回数据无效
        Exception: 网络/API 异常（含限流）
    """
    # 防御性规范化（避免 "aapl" 与 "AAPL" 产生不同缓存项）
    symbol = symbol.strip().upper()
    
    ticker = yf.Ticker(symbol)
    
    # ----- Step 1: fast_info 获取核心价格字段（快速路径）-----
    current_price: Optional[float] = None
    previous_close: Optional[float] = None
    volume: Optional[int] = None
    exchange: str = "N/A"
    currency: str = "USD"
    
    try:
        fast_info = ticker.fast_info
        current_price = fast_info.get("last_price") or fast_info.get("lastPrice")
        previous_close = fast_info.get("previous_close") or fast_info.get("previousClose")
        volume = fast_info.get("last_volume") or fast_info.get("lastVolume")
        exchange = fast_info.get("exchange") or "N/A"
        currency = fast_info.get("currency") or "USD"
    except Exception:
        # fast_info 失败不阻塞流程，继续走降级路径
        pass
    
    # ----- Step 2: history 兜底（用于校验股票存在性 + 补全数据）-----
    try:
        hist = ticker.history(period="5d")
    except Exception as e:
        if is_rate_limit_error(e):
            raise  # 限流错误直接上抛，由调用方友好提示
        raise ValueError(f"无法获取「{symbol}」的历史数据：{e}")
    
    # 校验：股票代码不存在时 hist 为空
    if hist.empty:
        raise ValueError(f"股票代码「{symbol}」不存在或暂无历史数据")
    
    # 用历史数据补全缺失的价格字段
    if current_price is None:
        current_price = float(hist["Close"].iloc[-1])
    if previous_close is None and len(hist) >= 2:
        previous_close = float(hist["Close"].iloc[-2])
    if volume is None:
        volume = int(hist["Volume"].iloc[-1])
    
    # 日内最高/最低（直接从最新交易日提取，相对稳定）
    day_high = float(hist["High"].iloc[-1])
    day_low = float(hist["Low"].iloc[-1])
    
    # ----- Step 3: info 获取元数据（慢速路径，可选获取）-----
    company_name: str = symbol
    market_cap: Optional[float] = None
    market_state: str = "UNKNOWN"
    market_time_ts: Optional[int] = None
    
    try:
        info = ticker.info or {}
        company_name = info.get("longName") or info.get("shortName") or symbol
        market_cap = info.get("marketCap")
        market_state = info.get("marketState", "UNKNOWN")
        market_time_ts = info.get("regularMarketTime")
        # info 可能提供更精确的当前价（覆盖 fast_info 的回退值）
        if info.get("currentPrice"):
            current_price = float(info["currentPrice"])
        # info 可能提供更准确的交易所信息
        if info.get("exchange") and exchange == "N/A":
            exchange = info["exchange"]
    except Exception:
        # info 失败不影响核心功能，使用已有兜底值
        pass
    
    # ----- 最终校验 -----
    if not previous_close or previous_close <= 0:
        raise ValueError(f"无法获取「{symbol}」的前收盘价，数据不完整")
    if not current_price or current_price <= 0:
        raise ValueError(f"无法获取「{symbol}」的当前价格")
    
    # ----- 涨跌计算 -----
    change_amount = current_price - previous_close
    change_pct = (change_amount / previous_close) * 100
    
    # ----- 行情时间格式化 -----
    if market_time_ts:
        market_time = datetime.fromtimestamp(market_time_ts).strftime("%Y-%m-%d %H:%M:%S")
    else:
        market_time = hist.index[-1].strftime("%Y-%m-%d %H:%M:%S")
    
    return {
        "symbol": symbol,
        "company_name": company_name,
        "exchange": exchange,
        "currency": currency,
        "market_state": market_state,
        "price": float(current_price),
        "previous_close": float(previous_close),
        "change_amount": float(change_amount),
        "change_pct": float(change_pct),
        "volume": int(volume) if volume else 0,
        "market_cap": market_cap,
        "day_high": day_high,
        "day_low": day_low,
        "market_time": market_time,
    }


# ============ UI 渲染模块 ============
def render_header():
    """渲染页面头部"""
    st.title("📈 美股实时行情")
    st.caption(
        f"数据来源：Yahoo Finance · 缓存 {CACHE_TTL} 秒 · "
        "⏱️ 行情通常延迟 15 分钟"
    )
    st.divider()


def on_quick_select(sym: str):
    """快选按钮回调：同步更新 session_state 并清缓存"""
    st.session_state.current_symbol = sym
    st.session_state.symbol_input = sym  # 同步输入框显示
    fetch_stock_data.clear()


def render_symbol_input() -> str:
    """
    渲染股票代码输入区（输入框 + 热门快选）。
    
    Returns:
        当前输入框中的股票代码（已规范化）
    """
    # 初始化 session_state（单一数据源）
    if "current_symbol" not in st.session_state:
        st.session_state.current_symbol = DEFAULT_SYMBOL
    if "symbol_input" not in st.session_state:
        st.session_state.symbol_input = DEFAULT_SYMBOL
    
    # 输入框（仅用 key 绑定，不用 value，避免冲突）
    input_col, _ = st.columns([2, 1])
    with input_col:
        st.text_input(
            "🔍 输入股票代码",
            help="例如：AAPL（苹果）、MSFT（微软）、TSLA（特斯拉）、BRK.B（伯克希尔）",
            key="symbol_input"
        )
    
    # 热门股票快选按钮（响应式 2x3 布局，移动端友好）
    st.markdown("**🔥 热门股票**")
    rows = 2
    cols_per_row = 3
    for row in range(rows):
        cols = st.columns(cols_per_row)
        for col_idx in range(cols_per_row):
            sym_idx = row * cols_per_row + col_idx
            if sym_idx < len(POPULAR_SYMBOLS):
                sym = POPULAR_SYMBOLS[sym_idx]
                with cols[col_idx]:
                    st.button(
                        sym,
                        use_container_width=True,
                        key=f"quick_{sym}",
                        on_click=on_quick_select,
                        args=(sym,),
                    )
    
    # 返回输入框中的当前值（已规范化）
    return normalize_symbol(st.session_state.get("symbol_input", DEFAULT_SYMBOL))


def render_price_card(data: Dict[str, Any]):
    """渲染主价格卡片"""
    # 公司名称与交易所
    st.subheader(f"{data['company_name']} ({data['symbol']})")
    st.caption(f"交易所：{data['exchange']} · 货币：{data['currency']}")
    
    # 交易状态提示
    state_text, state_level = get_market_state_label(data["market_state"])
    if state_level == "success":
        st.success(state_text)
    elif state_level == "warning":
        st.warning(state_text)
    else:
        st.info(state_text)
    
    # 主指标区：价格 + 涨跌额
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.metric(
            label=f"💰 当前价格 ({data['currency']})",
            value=f"${data['price']:,.2f}",
            delta=f"{data['change_pct']:+.2f}%  (当日)",
        )
    
    with col2:
        st.metric(
            label="📊 当日涨跌额",
            value=f"${data['change_amount']:+,.2f}",
            delta=f"{data['change_pct']:+.2f}%",
        )
    
    # 趋势语义化提示（三态）
    change_pct = data["change_pct"]
    if change_pct > 0:
        st.success(f"📈 {data['symbol']} 当日上涨 {change_pct:.2f}%")
    elif change_pct < 0:
        st.warning(f"📉 {data['symbol']} 当日下跌 {abs(change_pct):.2f}%")
    else:
        st.info(f"➡️ {data['symbol']} 当日价格基本持平")
    
    # 附加信息区
    st.divider()
    st.markdown("### 📋 详细信息")
    
    info_col1, info_col2 = st.columns(2)
    
    with info_col1:
        st.markdown(f"**前收盘价**  \n${data['previous_close']:,.2f}")
        st.markdown(f"**日内最高**  \n${data['day_high']:,.2f}")
        st.markdown(f"**成交量**  \n{format_volume(data['volume'])}")
    
    with info_col2:
        st.markdown(f"**市值**  \n{format_market_cap(data['market_cap'])}")
        st.markdown(f"**日内最低**  \n${data['day_low']:,.2f}")
        st.markdown(f"**行情时间**  \n{data['market_time']} (本地时间)")


def render_footer():
    """渲染页面底部：本地刷新时间"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.caption(f"🕐 本地最后刷新：{now} (本地时间)")


def render_disclaimer():
    """渲染免责声明（合规升级版）"""
    st.divider()
    st.caption(
        "⚠️ **免责声明**：本应用数据来源于 Yahoo Finance，"
        "**可能存在 15 分钟以上延迟**，不适用于高频交易决策。"
        "所示数据仅供信息参考，**不构成任何投资建议**。"
        "股市有风险，投资需谨慎，决策请以官方券商行情为准。"
    )


def render_error(error_msg: str, show_retry_hint: bool = True):
    """渲染错误提示"""
    st.error(f"❌ {error_msg}")
    if show_retry_hint:
        st.info("💡 请检查股票代码或网络连接，点击「刷新数据」按钮可重新尝试。")


def handle_fetch_error(error: Exception, symbol: str):
    """
    针对不同异常类型给出友好提示。
    
    Args:
        error: 捕获的异常
        symbol: 当前查询的股票代码
    """
    # 限流错误优先识别
    if is_rate_limit_error(error):
        render_error(
            "Yahoo Finance 触发访问限流，请稍等 1-2 分钟后重试",
            show_retry_hint=False,
        )
        return
    
    # 业务异常（股票不存在等）
    if isinstance(error, ValueError):
        render_error(str(error))
        return
    
    # 网络异常的常见关键字识别
    error_str = str(error).lower()
    if "timeout" in error_str or "timed out" in error_str:
        render_error(f"请求 Yahoo Finance 超时，请检查网络后重试")
    elif "connection" in error_str or "network" in error_str:
        render_error("网络连接失败，请检查您的网络后重试")
    elif "not found" in error_str or "404" in error_str:
        render_error(f"股票代码「{symbol}」不存在，请检查后重试")
    else:
        # 兜底
        render_error(f"获取数据失败：{error}")


# ============ 主程序 ============
def main():
    """应用主入口"""
    # ⚠️ set_page_config 必须是第一个 Streamlit 命令
    st.set_page_config(
        page_title="美股实时行情",
        page_icon="📈",
        layout="centered",
    )
    
    render_header()
    
    # 股票代码输入区
    symbol = render_symbol_input()
    
    # 刷新控制区
    st.divider()
    col_btn, col_auto = st.columns([1, 2])
    
    with col_btn:
        refresh_clicked = st.button("🔄 刷新数据", use_container_width=True)
    
    with col_auto:
        auto_refresh = st.checkbox(
            f"自动刷新（每 {AUTO_REFRESH_INTERVAL} 秒）",
            value=False,
            help="启用后页面将自动刷新，可随时取消勾选立即生效",
        )
    
    # 自动刷新：使用浏览器原生 meta refresh，完全非阻塞
    # 安全说明：AUTO_REFRESH_INTERVAL 为模块级常量，无 XSS 风险
    # 警告：切勿将用户输入拼接到此处
    if auto_refresh:
        st.markdown(
            f'<meta http-equiv="refresh" content="{AUTO_REFRESH_INTERVAL}">',
            unsafe_allow_html=True,
        )
    
    # 用户点击刷新时清除当前股票的缓存
    if refresh_clicked:
        fetch_stock_data.clear()
    
    st.divider()
    
    # ----- 输入校验 -----
    if not symbol:
        st.warning("⚠️ 请输入股票代码或点击下方热门股票按钮")
        render_disclaimer()
        return
    
    if not is_valid_symbol(symbol):
        st.error(
            f"❌ 股票代码「{symbol}」格式无效。"
            "应为 1-5 个英文字母，可带 .X 或 -X 后缀（如 AAPL、BRK.B）"
        )
        render_disclaimer()
        return
    
    # ----- 数据获取与渲染 -----
    try:
        with st.spinner(f"正在获取 {symbol} 的实时行情..."):
            data = fetch_stock_data(symbol)
        render_price_card(data)
        render_footer()
    except Exception as e:
        handle_fetch_error(e, symbol)
    finally:
        # 免责声明任何状态都展示（合规要求）
        render_disclaimer()


if __name__ == "__main__":
    main()