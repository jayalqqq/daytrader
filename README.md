# Day-Trader (paper) — intraday bot, ETF / leveraged-ETF watchlist

The closest working equivalent to real day trading, on data that actually works.
Two researched strategies, strict confirmation filters, proper intraday risk.

## What it trades (futures-proxy ETFs + leverage)

  SPY  — S&P 500      (what ES futures track)
  QQQ  — Nasdaq 100   (what NQ futures track)
  USO  — Crude oil    (what CL futures track)
  GLD  — Gold         (what GC futures track)
  SSO  — 2x S&P 500   (leverage dynamic)
  UPRO — 3x S&P 500   (higher leverage dynamic)
  TQQQ — 3x Nasdaq    (higher leverage dynamic)

These give the futures-style experience (index/commodity exposure + leverage) on
clean, free data — unlike raw futures, whose free data is unreliable.

## Two researched strategies (both require confirmation)

1. CANDLESTICK REVERSAL — bullish engulfing / hammer, but ONLY with a prior
   downtrend + above-average volume + price at VWAP. Patterns alone lose;
   patterns + context is what has an edge.

2. OPENING RANGE BREAKOUT (ORB) — the most-validated intraday strategy in the
   2026 research. Marks the first 30 minutes' range; takes a long only when a
   bar CLOSES above the range high WITH VWAP agreement and above-average volume.

Honest reliability (from the research): ORB win rate is 40-60%, NOT higher.
It profits from reward-to-risk on trend days, not from a high hit rate. Anyone
claiming 80%+ is ignoring slippage and false breakouts.

## Risk rules (baked in)

- Hard 0.5% stop-loss per trade
- 1% take-profit target
- End-of-day exit — flat by the close, no overnight risk
- Max 3 concurrent positions
- 5 bps slippage on every fill

## Run it

```
pip install yfinance pandas numpy
python3 run.py          # one scan + manage cycle
python3 run.py report   # standing, realized P&L, WIN RATE, open trades
```

For real day-trading behavior it must run every 5-15 min through the session,
which needs the machine awake all day — the always-on problem again. Cloud
(GitHub Actions) is the honest fix for unattended intraday running.

## The honest part (unchanged and important)

- This is built as well as a candlestick+ORB day-trader reasonably can be. That
  makes it SOUND, not PROFITABLE. There is no online strategy that reliably makes
  money day trading — if there were, it wouldn't be online.
- Day trading is close to zero-sum against professionals. Most retail day traders
  lose money over time. Leveraged ETFs (SSO/UPRO/TQQQ) amplify BOTH directions —
  they can lose faster too, and they decay over time by design.
- A few good paper weeks is NOT proof of edge. Short windows produce winners by
  chance. Real evidence needs a large sample, out-of-sample testing, and survival
  of costs across many trades.
- The report's win rate and P&L exist so you see the TRUTH of what's happening.
  Any decision about real money belongs to you with clear-eyed results in hand.
