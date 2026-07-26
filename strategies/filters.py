"""
Context filters — the part that separates a real strategy from a toy.

The research is unanimous: a candlestick pattern is only tradeable when it
appears WITH confirming context. This module computes that context so the
strategy can require it before entering.

  - trend:   is price in a short-term down/up move? (patterns reverse trends)
  - volume:  is this bar's volume above its recent average? (conviction)
  - vwap:    is price near/at VWAP? (a key intraday level everyone watches)
"""

import pandas as pd


def short_trend(df: pd.DataFrame, lookback=10) -> str:
    """Return 'up', 'down', or 'flat' for the recent short-term trend,
    using the slope of a short moving average."""
    if len(df) < lookback + 1:
        return "flat"
    ma = df["Close"].rolling(lookback).mean()
    recent = ma.iloc[-1]
    earlier = ma.iloc[-lookback]
    if pd.isna(recent) or pd.isna(earlier):
        return "flat"
    change = (recent - earlier) / earlier
    if change > 0.001:
        return "up"
    if change < -0.001:
        return "down"
    return "flat"


def volume_confirms(df: pd.DataFrame, lookback=20, mult=1.2) -> bool:
    """True if the latest bar's volume is at least `mult` x the recent average.
    Above-average volume = conviction behind the move."""
    if "Volume" not in df or len(df) < lookback + 1:
        return False
    avg = df["Volume"].iloc[-lookback-1:-1].mean()
    if avg <= 0:
        return False
    return df["Volume"].iloc[-1] >= mult * avg


def vwap(df: pd.DataFrame) -> float:
    """Volume-weighted average price for the session so far."""
    if "Volume" not in df or df["Volume"].sum() == 0:
        return float(df["Close"].iloc[-1])
    typical = (df["High"] + df["Low"] + df["Close"]) / 3
    return float((typical * df["Volume"]).cumsum().iloc[-1] /
                 df["Volume"].cumsum().iloc[-1])


def near_vwap(df: pd.DataFrame, tol=0.003) -> bool:
    """True if price is within `tol` (0.3%) of VWAP — i.e. at a key level."""
    price = float(df["Close"].iloc[-1])
    vw = vwap(df)
    return abs(price - vw) / vw <= tol
