"""
Intraday paper-trading engine. Real prices, pretend money, no overnight holds.

Key intraday rules baked in:
  - Hard stop-loss per trade (default 0.5%, tighter than swing trading)
  - Take-profit target (default 1%) — intraday moves are small
  - Same-day time exit: any position still open near session end is closed.
    Day trading means FLAT by the close, no overnight risk.
  - Realistic slippage on every fill.

PAPER ONLY. No broker, no keys, no real orders.
"""

import json
from datetime import datetime, time
from zoneinfo import ZoneInfo
from pathlib import Path

import yfinance as yf
import pandas as pd

STATE_FILE = Path(__file__).resolve().parent.parent / "portfolio.json"
INITIAL = 10_000
SLIPPAGE = 0.0005      # 5 bps per fill
STOP_LOSS = 0.005      # 0.5% hard stop
TAKE_PROFIT = 0.01     # 1% target
RISK_PER_TRADE = 0.02  # deploy up to 2% of book per position idea
MAX_CONCURRENT = 3     # don't over-diversify intraday

EASTERN = ZoneInfo("America/New_York")


def market_now():
    """Current time in US market (Eastern) timezone, regardless of server TZ.
    This is the fix: the cloud runs in UTC, so datetime.now() was always past
    the old cutoff and triggered a sell+rebuy loop every run."""
    return datetime.now(EASTERN)


def is_session_ending():
    """True only in the real last 15 min of the US session (3:45-4:00pm ET)."""
    t = market_now().time()
    return time(15, 45) <= t <= time(16, 0)


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"cash": INITIAL, "positions": {}, "history": [],
            "daily_snapshots": []}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2))
    js = STATE_FILE.parent / "dashboard_data.js"
    js.write_text("window.PORTFOLIO = " + json.dumps(state) + ";")


def fetch_intraday(ticker, interval="5m", period="5d"):
    df = yf.download(ticker, interval=interval, period=period,
                     progress=False, auto_adjust=True)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df.dropna()


def current_price(ticker):
    df = yf.Ticker(ticker).history(period="1d", interval="5m")
    return float(df["Close"].iloc[-1]) if not df.empty else None


def manage_open_positions(state):
    """Apply stop-loss, take-profit, and end-of-day exit."""
    session_ending = is_session_ending()

    for ticker in list(state["positions"].keys()):
        pos = state["positions"][ticker]
        price = current_price(ticker)
        if price is None:
            continue
        reason = None
        if price <= pos["stop"]:
            reason = "STOP-LOSS"
        elif price >= pos["target"]:
            reason = "TAKE-PROFIT"
        elif session_ending:
            reason = "EOD-EXIT"
        if reason:
            proceeds = price * pos["shares"] * (1 - SLIPPAGE)
            state["cash"] += proceeds
            pnl = (price - pos["entry"]) * pos["shares"]
            state["history"].append({
                "time": datetime.now(EASTERN).isoformat(timespec="seconds"),
                "action": f"SELL ({reason})", "ticker": ticker,
                "shares": pos["shares"], "price": round(price, 2),
                "pnl": round(pnl, 2),
            })
            del state["positions"][ticker]
            print(f"  EXIT {ticker} @ ${price:.2f} ({reason}, P&L ${pnl:+.2f})")


def open_position(state, ticker, price, pattern):
    # Don't open new positions in the last 15 min — we're trying to go flat,
    # not re-enter right before close (that was half the churn bug).
    if is_session_ending():
        return
    if len(state["positions"]) >= MAX_CONCURRENT:
        print(f"  {ticker}: signal but at max {MAX_CONCURRENT} positions")
        return
    portfolio_value = state["cash"] + sum(
        current_price(t) * p["shares"] for t, p in state["positions"].items()
        if current_price(t))
    dollars = portfolio_value * RISK_PER_TRADE / STOP_LOSS  # risk-based size
    dollars = min(dollars, state["cash"] * 0.9)
    shares = int(dollars // price)
    if shares < 1:
        return
    cost = shares * price * (1 + SLIPPAGE)
    if cost > state["cash"]:
        return
    state["cash"] -= cost
    state["positions"][ticker] = {
        "shares": shares, "entry": price,
        "stop": round(price * (1 - STOP_LOSS), 2),
        "target": round(price * (1 + TAKE_PROFIT), 2),
        "pattern": pattern,
    }
    state["history"].append({
        "time": datetime.now(EASTERN).isoformat(timespec="seconds"),
        "action": "BUY", "ticker": ticker, "shares": shares,
        "price": round(price, 2), "pattern": pattern,
    })
    print(f"  BUY {shares} {ticker} @ ${price:.2f} on {pattern} "
          f"(stop ${price*(1-STOP_LOSS):.2f}, target ${price*(1+TAKE_PROFIT):.2f})")
