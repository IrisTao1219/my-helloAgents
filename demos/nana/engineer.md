# 纳斯达克股票数据应用 - 代码实现

收到产品经理的详细需求分析！按照默认方案推进：**方案 B + 支持所有美股 + 默认 AAPL**。我将基于现有架构进行改造，最大化复用已有的优秀设计。

## 实施方案确认

| 维度 | 决策 |
|------|------|
| 数据源 | yfinance（无需 API Key） |
| 默认股票 | AAPL |
| 支持范围 | 所有美股代码 |
| 热门快选 | AAPL/MSFT/GOOGL/AMZN/TSLA/NVDA |
| 缓存策略 | 按 symbol 参数独立缓存 |
| 状态管理 | 使用 `st.session_state` 管理当前选中股票 |

---

## 完整代码实现

```python
"""
美股实时行情查询应用
基于 Streamlit + yfinance (Yahoo Finance) 实现

Features:
    - 输入股票代码查询实时行情（默认 AAPL）
    - 6 只热门股票一键快选
    - 当日涨跌幅、涨跌额、成交量、市值展示
    - 交易状态提示（盘中/盘后/休市）
    - 手动刷新 + 自动刷新（基于 meta refresh，非阻塞）
    - 完善的异常处理与友好提示
"""

import re
from datetime import datetime
from typing import Dict, Any, Optional

import streamlit as st
import yfinance as yf

# ============ 常量配置 ============
DEFAULT_SYMBOL = "AAPL"
POPULAR_SYMBOLS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA"]
SYMBOL_PATTERN = re.compile(r"^[A-Z]{1,5}(\.[A-Z])?$")  # 美股代码：1-5 个大写字母

CACHE_TTL = 60                 # 数据缓存时长（秒）
AUTO_REFRESH_INTERVAL = 60     # 自动刷新间隔（秒）
REQUEST_TIMEOUT = 15           # yfinance 内部请求超时参考（秒）

# 美股交易时段（美东时间 9:30 - 16:00，对应 UTC 14:30 - 21:00，夏令时调整）
# 简化处理：使用 yfinance 返回的 marketState 字段


# ============ 工具函数 ============
def normalize_symbol(symbol: str) -> str:
    """
    规范化股票代码：去空格、转大写。
    
    Args:
        symbol: 原始输入
    
    Returns:
        规范化后的代码
    """
    return symbol.strip().upper() if symbol else ""


def is_valid_symbol(symbol: str) -> bool:
    """
    校验股票代码格式合法性（1-5 个大写字母，可选 .X 后缀）。
    
    Args:
        symbol: 已规范化的股票代码
    
    Returns:
        是否合法
    """
    return bool(symbol and SYMBOL_PATTERN.match(symbol))


def format_market_cap(market_cap: Optional[float]) -> str:
    """
    格式化市值（自动转换为 B/M 单位）。
    
    Args:
        market_cap: 市值（美元）
    
    Returns:
        格式化字符串
    """
    if not market_cap or market_cap <= 0:
        return "暂无数据"
    if market_cap >= 1e12:
        return f"${market_cap / 1e12:.2f} T"
    if market_cap >= 1e9:
        return f"${market_cap / 1e9:.2f} B"
    if market_cap >= 1e6:
        return f"${market_cap / 1e6:.2f} M"
    return f"${market_cap:,.0f}"


def get_market_state_label(state: str) -> tuple[str, str]:
    """
    将 yfinance 的 marketState 转为中文提示。
    
    Args:
        state: yfinance 返回的 marketState（REGULAR/PRE/POST/CLOSED 等）
    
    Returns:
        (emoji+文案, 状态级别) 状态级别用于决定渲染颜色：success/info/warning
    """
    mapping = {
        "REGULAR": ("🟢 盘中交易", "success"),
        "PRE": ("🟡 盘前交易", "info"),
        "POST": ("🟡 盘后交易", "info"),
        "POSTPOST": ("🟡 盘后交易", "info"),
        "CLOSED": ("🔴 美股休市（显示最近收盘价）", "warning"),
        "PREPRE": ("🔴 美股休市（显示最近收盘价）", "warning"),
    }
    return mapping.get(state, ("ℹ️ 状态未知", "info"))


# ============ 数据获取模块 ============
@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def fetch_stock_data(symbol: str) -> Dict[str, Any]:
    """
    通过 yfinance 获取股票实时行情数据。
    
    Args:
        symbol: 股票代码（已规范化）
    
    Returns:
        包含价格、涨跌、成交量、公司信息等字段的字典
    
    Raises:
        ValueError: 股票代码不存在或返回数据无效
        Exception: 其他网络/API 异常
    
    Note:
        - 缓存按 symbol 独立生效
        - Yahoo Finance 行情通常延迟 15 分钟
        - 休市期间使用最近收盘价计算
    """
    ticker = yf.Ticker(symbol)
    
    # info 包含公司信息和实时价格（部分字段在休市时可能缺失）
    info = ticker.info or {}
    
    # 获取近 2 个交易日的历史数据，用于计算当日涨跌
    # 使用 5d 兜底，避免遇到节假日数据不足
    hist = ticker.history(period="5d")
    
    # 校验：股票代码不存在时，hist 为空 DataFrame，info 也几乎为空
    if hist.empty or not info.get("symbol") and not info.get("shortName"):
        raise ValueError(f"股票代码「{symbol}」不存在或暂无数据")
    
    # ----- 价格计算 -----
    # 当前价格优先使用 info 中的实时字段，回退到最新收盘价
    current_price = (
        info.get("currentPrice")
        or info.get("regularMarketPrice")
        or float(hist["Close"].iloc[-1])
    )
    
    # 前收盘价：优先 info，回退到历史数据的倒数第二天
    previous_close = info.get("previousClose") or info.get("regularMarketPreviousClose")
    if not previous_close and len(hist) >= 2:
        previous_close = float(hist["Close"].iloc[-2])
    
    if not previous_close or previous_close <= 0:
        raise ValueError(f"无法获取「{symbol}」的前收盘价")
    
    change_amount = current_price - previous_close
    change_pct = (change_amount / previous_close) * 100
    
    # ----- 成交量 -----
    volume = info.get("volume") or info.get("regularMarketVolume")
    if not volume and not hist.empty:
        volume = int(hist["Volume"].iloc[-1])
    
    # ----- 行情时间 -----
    market_time_ts = info.get("regularMarketTime")
    if market_time_ts:
        market_time = datetime.fromtimestamp(market_time_ts).strftime("%Y-%m-%d %H:%M:%S")
    elif not hist.empty:
        market_time = hist.index[-1].strftime("%Y-%m-%d %H:%M:%S")
    else:
        market_time = "未知"
    
    return {
        "symbol": info.get("symbol", symbol),
        "company_name": info.get("longName") or info.get("shortName") or symbol,
        "exchange": info.get("exchange", "N/A"),
        "currency": info.get("currency", "USD"),
        "market_state": info.get("marketState", "UNKNOWN"),
        "price": float(current_price),
        "previous_close": float(previous_close),
        "change_amount": float(change_amount),
        "change_pct": float(change_pct),
        "volume": int(volume) if volume else 0,
        "market_cap": info.get("marketCap"),
        "day_high": info.get("dayHigh") or (float(hist["High"].iloc[-1]) if not hist.empty else None),
        "day_low": info.get("dayLow") or (float(hist["Low"].iloc[-1]) if not hist.empty else None),
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


def render_symbol_input() -> str:
    """
    渲染股票代码输入区（输入框 + 热门快选）。
    
    Returns:
        当前选中的股票代码（已规范化）
    """
    # 初始化 session_state
    if "current_symbol" not in st.session_state:
        st.session_state.current_symbol = DEFAULT_SYMBOL
    
    # 输入框（受 session_state 控制，便于快选按钮联动）
    input_col, _ = st.columns([2, 1])
    with input_col:
        user_input = st.text_input(
            "🔍 输入股票代码",
            value=st.session_state.current_symbol,
            help="例如：AAPL（苹果）、MSFT（微软）、TSLA（特斯拉）",
            key="symbol_input",
        )
    
    # 热门股票快选按钮
    st.markdown("**🔥 热门股票**")
    cols = st.columns(len(POPULAR_SYMBOLS))
    for idx, sym in enumerate(POPULAR_SYMBOLS):
        with cols[idx]:
            if st.button(sym, use_container_width=True, key=f"quick_{sym}"):
                st.session_state.current_symbol = sym
                # 清除当前股票的缓存，确保重新拉取
                fetch_stock_data.clear()
                st.rerun()
    
    # 以输入框的值作为最终查询目标
    return normalize_symbol(user_input)


def render_price_card(data: Dict[str, Any]):
    """
    渲染主价格卡片。
    
    Args:
        data: 股票数据字典
    """
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
    
    # 趋势语义化提示