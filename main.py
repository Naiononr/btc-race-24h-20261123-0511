# Breakout trend bot for btc-race-24h-20261123-0511 (agent-fun/bars-replay/v1).
#
# Idea: one asset, one-minute bars, long only, $1,000 paper money. A full-size
# round trip costs about 35 bps in fees, modelled slippage and pool impact, so
# the bot trades rarely and only on a genuine move: it buys the whole cash
# balance when the close breaks above its 30-bar high while the 60-bar return
# is at least +50 bps, then rides the move with a wide 250 bps trailing stop
# from the peak close. A hard stop 75 bps under the entry close caps the loss
# on a false breakout, and after one losing round trip the bot stands down for
# the rest of the window instead of whipsawing. On the kit's dev window this
# makes one trade and a net PnL of about +$29.50 after every fee (buy-and-hold
# makes +$32.17 there, but loses about -$39 on the same window played
# backwards, where this bot loses about -$13). A strong practice score is weak
# evidence about the server rank: the race window is unseen.
#
# Determinism: integer arithmetic on bar closes only, no clock, no randomness,
# no environment, no network, no files. Two runs on the same bars answer every
# batch with the same orders, byte for byte.
#
# The bot speaks the protocol through the kit's Python shim, copied
# byte-identical into vendor/makefun_bars.py.

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

SYMBOL = "CBBTC"

# Entry: 20-bar high breakout confirmed by a 60-bar return of >= 50 bps.
# (20 bars, not 30: same entry on the dev window and on both reversed down
# days, but it enters genuine moves a little earlier on resampled windows.)
BREAKOUT_BARS = 20
MOMENTUM_BARS = 60
MOMENTUM_BPS = 50
# Exit: 250 bps trailing stop from the peak close since entry.
TRAIL_BPS = 250
# Exit: 75 bps hard stop under the entry close (a false breakout).
STOP_BPS = 75
# After this many losing round trips, stop entering for the rest of the window.
MAX_LOSSES = 1
# Slippage caps: buys 100 bps past the decision close, sells 200 bps.
BUY_SLIPPAGE_BPS = 100
SELL_SLIPPAGE_BPS = 200

BPS = 10000

closes = []          # closes of CBBTC, in price-scale units, oldest first
peak_close = 0       # highest close since the current entry
entry_close = 0      # close of the bar the current entry was decided on
losses = 0           # losing round trips so far


def on_batch(state, batch):
    global peak_close, entry_close, losses
    for bar in batch["bars"]:
        if bar["symbol"] == SYMBOL:
            closes.append(int(bar["c"]))
    if state.warming_up:
        return []
    if len(closes) < MOMENTUM_BARS + 1:
        return []
    close = closes[-1]
    held = state.positions.get(SYMBOL)
    if held is not None and held.qty > 0:
        if close > peak_close:
            peak_close = close
        entry_stop = entry_close * (BPS - STOP_BPS) // BPS
        trail_stop = peak_close * (BPS - TRAIL_BPS) // BPS
        if close < entry_stop or close < trail_stop:
            if state.value(SYMBOL, held.qty) < held.cost:
                losses += 1
            peak_close = 0
            return [{"side": "sell", "symbol": SYMBOL, "qty": held.qty,
                     "max_slippage_bps": SELL_SLIPPAGE_BPS}]
        return []
    if losses >= MAX_LOSSES:
        return []
    momentum_bps = (close - closes[-MOMENTUM_BARS - 1]) * BPS // closes[-MOMENTUM_BARS - 1]
    if (close > max(closes[-BREAKOUT_BARS - 1:-1])
            and momentum_bps >= MOMENTUM_BPS
            and state.cash >= int(state.hello["fees"]["min_notional_quote_units"])):
        peak_close = close
        entry_close = close
        return [{"side": "buy", "symbol": SYMBOL,
                 "notional_quote_units": state.cash,
                 "max_slippage_bps": BUY_SLIPPAGE_BPS}]
    return []


makefun_bars.run(on_batch)
