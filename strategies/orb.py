"""
Opening Range Breakout (ORB) — the most consistently-validated intraday
strategy in the 2026 research.

The idea: the first 15-30 minutes after the open establish a range where buyers
and sellers found agreement. A decisive break of that range, WITH confirmation,
often continues into a trend move.

Research is clear on the honest profile:
  - Win rate is only 40-60%. It is NOT high-hit-rate.
  - It makes money (when it does) from reward-to-risk: winners run to 2R+ on
    trend days, losers get cut fast at the range edge.
  - Anyone claiming 80%+ is ignoring slippage and false breakouts.

Required confirmation (from the research) before taking a breakout:
  1. Candle CLOSES beyond the opening range (not just a wick poke)
  2. Price is on the correct side of VWAP
  3. Above-average volume on the breakout bar

Long-only here (no shorting), consistent with the rest of the setup.
"""

import pandas as pd
from datetime import time

from strategies.filters import volume_confirms, vwap


def opening_range(df: pd.DataFrame, minutes=30) -> tuple:
    """High/low of the first `minutes` of the session. Assumes df index is
    intraday timestamps for the current day. Returns (or_high, or_low) or
    (None, None) if the session hasn't opened enough bars yet."""
    if df.empty:
        return None, None
    # take bars from the day's first timestamp forward `minutes`
    day = df.index[-1].date()
    day_bars = df[df.index.date == day]
    if len(day_bars) < 2:
        return None, None
    start = day_bars.index[0]
    cutoff = start + pd.Timedelta(minutes=minutes)
    opening = day_bars[day_bars.index <= cutoff]
    if opening.empty:
        return None, None
    return float(opening["High"].max()), float(opening["Low"].min())


def evaluate_orb(df: pd.DataFrame, minutes=30) -> dict:
    """Long signal if the latest bar CLOSES above the opening range high,
    with volume + VWAP confirmation."""
    result = {"signal": 0, "pattern": None, "reasons": [], "blocked": []}

    or_high, or_low = opening_range(df, minutes)
    if or_high is None:
        result["blocked"].append("opening range not established yet")
        return result

    close = float(df["Close"].iloc[-1])
    broke_up = close > or_high

    if not broke_up:
        result["blocked"].append(f"no close above opening-range high ({or_high:.2f})")
        return result

    result["pattern"] = "ORB breakout"

    vw = vwap(df)
    above_vwap = close > vw
    vol_ok = volume_confirms(df)

    if not above_vwap:
        result["blocked"].append("price below VWAP (breakout unconfirmed)")
    else:
        result["reasons"].append("price above VWAP")

    if not vol_ok:
        result["blocked"].append("volume below average (likely false breakout)")
    else:
        result["reasons"].append("above-average breakout volume")

    result["reasons"].append(f"closed above opening range ({or_high:.2f})")

    if above_vwap and vol_ok:
        result["signal"] = 1
        # store the range low so the engine can set a logical stop there
        result["stop_hint"] = or_low

    return result
