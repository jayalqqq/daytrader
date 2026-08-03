"""
Intraday strategies — MORE ACTIVE / higher-risk version.

Adds the most widely-used retail day-trading setups from the 2026 research and
LOOSENS entries so the bot actually trades (the old version required 4 rare
conditions at once and never fired).

Strategies (any ONE firing = trade):
  1. RSI + VWAP mean reversion  — the highest win-rate intraday setup
       long when RSI < 35 AND price below VWAP (oversold bounce toward VWAP)
  2. Momentum breakout          — price breaks recent high on volume
  3. MA pullback                — uptrend + price dips to the fast MA then turns

Honest note: research says only 1-4% of day traders are consistently
profitable; 72% net lose. Looser + riskier = MORE trades, bigger swings both
ways, and more fees. Stops are kept to cap downside per trade.
"""

import pandas as pd


def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, 1e-9)
    return 100 - (100 / (1 + rs))


def vwap_value(df):
    if "Volume" not in df or df["Volume"].sum() == 0:
        return float(df["Close"].iloc[-1])
    typical = (df["High"] + df["Low"] + df["Close"]) / 3
    return float((typical * df["Volume"]).cumsum().iloc[-1] /
                 df["Volume"].cumsum().iloc[-1])


def evaluate(df: pd.DataFrame) -> dict:
    """Return {signal:1/0, pattern:name, reasons:[...]}. Fires if ANY setup hits."""
    result = {"signal": 0, "pattern": None, "reasons": []}
    if len(df) < 20:
        return result

    close = df["Close"]
    price = float(close.iloc[-1])

    # --- 1. RSI + VWAP mean reversion (highest win rate) ---
    r = rsi(close).iloc[-1]
    vw = vwap_value(df)
    if r < 35 and price < vw:
        result["signal"] = 1
        result["pattern"] = "RSI+VWAP reversion"
        result["reasons"] = [f"RSI {r:.0f} oversold", "price below VWAP → bounce"]
        return result

    # --- 2. Momentum breakout (looser: 10-bar high, no VWAP requirement) ---
    prior_high = df["High"].rolling(10).max().shift(1).iloc[-1]
    avg_vol = df["Volume"].iloc[-11:-1].mean() if "Volume" in df else 0
    vol_ok = ("Volume" in df) and df["Volume"].iloc[-1] >= avg_vol  # >= average, looser
    if price > prior_high and vol_ok:
        result["signal"] = 1
        result["pattern"] = "Momentum breakout"
        result["reasons"] = ["broke 10-bar high", "volume >= average"]
        return result

    # --- 3. MA pullback in uptrend ---
    fast = close.rolling(9).mean()
    slow = close.rolling(20).mean()
    uptrend = fast.iloc[-1] > slow.iloc[-1]
    dipped = price <= fast.iloc[-1] * 1.002  # near/just below fast MA
    turning = close.iloc[-1] > close.iloc[-2]  # ticking back up
    if uptrend and dipped and turning:
        result["signal"] = 1
        result["pattern"] = "MA pullback"
        result["reasons"] = ["uptrend", "pulled back to 9MA", "turning up"]
        return result

    return result


# Liquid names + leveraged ETFs for bigger intraday swings (higher risk).
WATCHLIST = ["SPY", "QQQ", "AAPL", "NVDA", "TSLA", "AMD", "META",
             "TQQQ", "SOXL", "UPRO"]
