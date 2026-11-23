# BTC Race Bot — btc-race-24h-20261123-0511

A trading bot for the make.fun competition "Race a BTC trading bot live for
24 hours". It trades Coinbase Wrapped BTC (cbBTC) against USDC, minute by
minute, on the `agent-fun/bars-replay/v1` protocol, starting with $1,000 of
paper money. Standard library only, no network, no clock, no randomness:
two runs on the same bars answer every batch with the same orders.

## Strategy

One asset, long only, at most one position, at most one round trip after a
loss. A full-size round trip costs about 35 bps in fees, modelled slippage
and pool impact, so the bot trades rarely and only on a genuine move:

- **Enter** — buy the whole cash balance when the close breaks above its
  20-bar high while the 60-bar return is at least +50 bps.
- **Exit** — sell everything on a 250 bps trailing stop from the peak close
  since entry, or on a 75 bps hard stop under the entry close (a false
  breakout).
- **Stand down** — after one losing round trip, no more entries for the rest
  of the window, instead of whipsawing.

Buys cap slippage at 100 bps past the decision close, sells at 200 bps.
Orders decided on a batch fill at the next bar's open, as the protocol says.

## Files

- `main.py` — the bot (entrypoint, Python 3.13, standard library only).
- `vendor/makefun_bars.py` — the kit's Python protocol shim, copied
  byte-identical from the kit's `sdk/makefun_bars.py`.
- `.makefun/owner.json` — the claim file naming the agent wallet.

## Local results (dev window, kit's frozen 24 h)

Run through an exact-integer replay of the harness fill model
(4 bps fee, 2 bps slippage, constant-product impact against each bar's open
depth, flatten at the last close):

| bot | net PnL | trades | max drawdown |
| --- | --- | --- | --- |
| this bot | **+$29.50** | 1 | 1.98% |
| buy-and-hold (kit baseline) | +$32.17 | 1 | 1.98% |
| momentum (kit baseline) | +$34.94 | 1 | 1.98% |
| ema-cross (kit baseline) | −$114.83 | 76 | 11.65% |
| rsi-bollinger (kit baseline) | −$9.32 | 10 | 2.06% |
| adx-momentum (kit baseline) | −$11.20 | 24 | 4.16% |

Robustness checks (same replay): the dev window played backwards
(a −3.5% day) loses −$12.61 where buy-and-hold loses −$38.40; the window
mirrored (also −3.5%) loses −$9.96; on 20 block-bootstrapped pseudo-days
the median is +$27.54 (buy-and-hold +$41.55, but it has no downside
protection). Two runs produce byte-identical action logs. The bot also
behaves on a 120-bar warm-up (+$21.74) and with missing minutes (+$29.56).

A strong practice score is weak evidence about the server rank: the race
window is 24 hours nobody has seen, and the dev window never counts toward
the ranking — it only decides whether the entry races (net PnL above $0).

## License

MIT. See `LICENSE`.
