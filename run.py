#!/usr/bin/env python3
"""
Day-trading bot runner. Scans the watchlist on 5-minute bars, enters only on
candlestick patterns CONFIRMED by trend + volume + VWAP, manages open trades
with stop/target/EOD exits.

    python3 run.py           # one scan + manage cycle
    python3 run.py report    # print current standing

PAPER ONLY.
"""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine.paper_engine import (load_state, save_state, fetch_intraday,
                                  current_price, manage_open_positions,
                                  open_position, INITIAL)
from strategies.intraday import evaluate, WATCHLIST
from strategies.orb import evaluate_orb


def scan_and_trade(state):
    print(f"\n=== Day-trade cycle {datetime.now():%Y-%m-%d %H:%M} ===")
    manage_open_positions(state)

    for ticker in WATCHLIST:
        if ticker in state["positions"]:
            continue
        try:
            df = fetch_intraday(ticker)
            if len(df) < 25:
                continue

            # Check both researched strategies: candlestick reversal + ORB
            candle = evaluate(df)
            orb = evaluate_orb(df)

            chosen = None
            if candle["signal"] == 1:
                chosen = candle
            elif orb["signal"] == 1:
                chosen = orb

            if chosen:
                price = current_price(ticker)
                if price:
                    print(f"  {ticker}: CONFIRMED {chosen['pattern']} — "
                          f"{', '.join(chosen['reasons'])}")
                    open_position(state, ticker, price, chosen["pattern"])
            else:
                # show near-misses so you can see what it's watching
                for strat in (candle, orb):
                    if strat["pattern"]:
                        print(f"  {ticker}: {strat['pattern']} seen but skipped "
                              f"({'; '.join(strat['blocked'])})")
        except Exception as e:
            print(f"  {ticker}: error {e}")


def total_value(state):
    total = state["cash"]
    for t, p in state["positions"].items():
        price = current_price(t)
        if price:
            total += price * p["shares"]
    return total


def report(state):
    total = total_value(state)
    pnl = total - INITIAL
    realized = sum(h.get("pnl", 0) for h in state["history"] if "pnl" in h)
    wins = [h for h in state["history"] if h.get("pnl", 0) > 0]
    losses = [h for h in state["history"] if h.get("pnl", 0) < 0]
    closed = len(wins) + len(losses)

    lines = []
    lines.append(f"DAY-TRADER · {datetime.now():%A, %B %d %H:%M}")
    lines.append("-" * 40)
    lines.append(f"Total value:   ${total:,.2f}")
    lines.append(f"All-time P&L:  {'+' if pnl>=0 else ''}${pnl:,.2f} ({pnl/INITIAL*100:+.2f}%)")
    lines.append(f"Realized P&L:  {'+' if realized>=0 else ''}${realized:,.2f}")
    if closed:
        win_rate = len(wins) / closed * 100
        lines.append(f"Closed trades: {closed}  |  Win rate: {win_rate:.0f}%")
    else:
        lines.append("Closed trades: 0 (no completed trades yet)")
    lines.append(f"Open now:      {len(state['positions'])}")
    for t, p in state["positions"].items():
        price = current_price(t) or p["entry"]
        upnl = (price - p["entry"]) * p["shares"]
        lines.append(f"  {t}: {p['shares']} sh @ ${p['entry']:.2f} "
                     f"({p['pattern']}), now ${price:.2f} ({upnl:+.2f})")
    text = "\n".join(lines)
    print(text)
    reports_dir = Path(__file__).resolve().parent / "reports"
    reports_dir.mkdir(exist_ok=True)
    (reports_dir / f"daytrader_{datetime.now():%Y-%m-%d}.txt").write_text(text)


def main():
    state = load_state()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    if cmd == "run":
        scan_and_trade(state)
        save_state(state)
        report(state)
    elif cmd == "report":
        report(state)
    else:
        print("Usage: python3 run.py [run|report]")


if __name__ == "__main__":
    main()
