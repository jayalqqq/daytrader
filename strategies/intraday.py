"""
Intraday strategy: patterns + REQUIRED context.

A signal only fires when a candlestick pattern appears TOGETHER with the
confirming context the research says is essential. This is the whole point —
patterns alone lose; patterns + trend + volume + level is what has a shot.

Entry logic (long):
  bullish pattern  AND  prior downtrend  AND  volume confirms  AND  near VWAP
Entry logic (short is NOT taken — this bot is long/flat only, no shorting,
matching the rest of your setup and avoiding margin/borrow complexity).

Returns a dict describing the decision so the report can explain WHY.
"""

import pandas as pd

from strategies.candlesticks import BULLISH_PATTERNS
from strategies.filters import short_trend, volume_confirms, near_vwap


def evaluate(df: pd.DataFrame) -> dict:
    """Evaluate the latest bar. Returns:
    {signal: 1/0, pattern: name or None, reasons: [...], blocked: [...]}"""
    result = {"signal": 0, "pattern": None, "reasons": [], "blocked": []}

    trend = short_trend(df)
    vol_ok = volume_confirms(df)
    vwap_ok = near_vwap(df)

    # Look for any bullish pattern on the latest bar
    found = None
    for name, fn in BULLISH_PATTERNS.items():
        if fn(df):
            found = name
            break

    if not found:
        result["blocked"].append("no bullish pattern on latest bar")
        return result

    result["pattern"] = found

    # Now require the confirming context
    if trend != "down":
        result["blocked"].append(f"trend is {trend}, need a prior downtrend to reverse")
    else:
        result["reasons"].append("prior downtrend present")

    if not vol_ok:
        result["blocked"].append("volume below average (no conviction)")
    else:
        result["reasons"].append("above-average volume")

    if not vwap_ok:
        result["blocked"].append("price not near VWAP (no key level)")
    else:
        result["reasons"].append("price at VWAP level")

    # Fire only if ALL filters pass
    if trend == "down" and vol_ok and vwap_ok:
        result["signal"] = 1

    return result


# Watchlist: ETF equivalents of the instruments futures day-traders watch,
# plus leveraged ETFs so the P&L reflects a futures-style leverage dynamic.
# All trade on clean data and are things you could actually access.
#   SPY  -> S&P 500      (like ES futures)
#   QQQ  -> Nasdaq 100   (like NQ futures)
#   USO  -> Crude oil    (like CL futures)
#   GLD  -> Gold         (like GC futures)
#   SSO  -> 2x S&P 500   (leverage dynamic)
#   UPRO -> 3x S&P 500   (higher leverage dynamic)
#   TQQQ -> 3x Nasdaq    (higher leverage dynamic)
WATCHLIST = ["SPY", "QQQ", "USO", "GLD", "SSO", "UPRO", "TQQQ"]

# Exit rule for open positions is handled by the engine: a hard stop-loss plus
# a same-day time exit (intraday trades don't hold overnight).
