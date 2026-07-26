"""
Candlestick pattern detection for intraday trading.

CRITICAL LESSON FROM THE RESEARCH: candlestick patterns in ISOLATION have win
rates under 50%. Every credible source agrees they only work WITH context:
  1. A prior trend (the pattern must reverse or continue something)
  2. Above-average volume (conviction behind the move)
  3. A key level (VWAP, prior-day high/low, support/resistance)

So this module does two things separately:
  - detect the raw pattern shape
  - a strategy layer (see intraday.py) that only acts when the confirming
    filters are ALSO present. Patterns alone are never traded.

Each detector takes a DataFrame with columns Open/High/Low/Close/Volume and
returns True if the pattern is present on the LATEST completed bar.

Sources reviewed (2026): tradingsim, edgeful, chartinglens, tradealgo,
Bulkowski's Encyclopedia of Candlestick Charts reliability rankings.
"""

import pandas as pd


def _body(o, c):
    return abs(c - o)


def bullish_engulfing(df: pd.DataFrame) -> bool:
    """Most reliable single reversal signal per the research. Green candle
    fully engulfs the prior red candle's body."""
    if len(df) < 2:
        return False
    p_o, p_c = df["Open"].iloc[-2], df["Close"].iloc[-2]
    o, c = df["Open"].iloc[-1], df["Close"].iloc[-1]
    prior_red = p_c < p_o
    now_green = c > o
    engulfs = c >= p_o and o <= p_c
    return prior_red and now_green and engulfs


def bearish_engulfing(df: pd.DataFrame) -> bool:
    """Red candle fully engulfs the prior green candle's body."""
    if len(df) < 2:
        return False
    p_o, p_c = df["Open"].iloc[-2], df["Close"].iloc[-2]
    o, c = df["Open"].iloc[-1], df["Close"].iloc[-1]
    prior_green = p_c > p_o
    now_red = c < o
    engulfs = o >= p_c and c <= p_o
    return prior_green and now_red and engulfs


def hammer(df: pd.DataFrame) -> bool:
    """Small body at top, long lower wick (>=2x body) — rejection of lower
    prices. Bullish when it appears after a decline at support."""
    if len(df) < 1:
        return False
    o, h, l, c = (df["Open"].iloc[-1], df["High"].iloc[-1],
                  df["Low"].iloc[-1], df["Close"].iloc[-1])
    body = _body(o, c)
    if body == 0:
        return False
    lower_wick = min(o, c) - l
    upper_wick = h - max(o, c)
    return lower_wick >= 2 * body and upper_wick <= body


def shooting_star(df: pd.DataFrame) -> bool:
    """Small body at bottom, long upper wick (>=2x body) — rejection of higher
    prices. Bearish at resistance after an advance."""
    if len(df) < 1:
        return False
    o, h, l, c = (df["Open"].iloc[-1], df["High"].iloc[-1],
                  df["Low"].iloc[-1], df["Close"].iloc[-1])
    body = _body(o, c)
    if body == 0:
        return False
    upper_wick = h - max(o, c)
    lower_wick = min(o, c) - l
    return upper_wick >= 2 * body and lower_wick <= body


BULLISH_PATTERNS = {
    "bullish_engulfing": bullish_engulfing,
    "hammer": hammer,
}
BEARISH_PATTERNS = {
    "bearish_engulfing": bearish_engulfing,
    "shooting_star": shooting_star,
}
