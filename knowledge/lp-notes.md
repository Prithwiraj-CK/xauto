# Meteora LP notes (from LP Army Academy + Meteora docs)

## Pools
- **DLMM**: price split into discrete bins; LP picks range, shape, bin step. Only bins price trades
  through earn fees. Up to 1,400 bins per position. Base fee + dynamic (volatility) fee.
  Some pools support limit-order style liquidity.
- **DAMM v2**: configurable constant-product AMM; dynamic fees, fee schedulers (time / market-cap
  based), NFT positions, both tokens required, fees not auto-compounded, earns MET points.
- **DAMM v1 + Dynamic Vaults**: legacy; vault lending yield, auto-compounding, PnL must be calculated
  manually, one-sided deposits get auto-swapped, no MET points.
- **DBC** (Dynamic Bonding Curve): token launches that graduate into DAMM v2.
- Meteora H1 2026: ~$140M LP fees on ~$32B volume; ~75% of fees from tokens not launched on Meteora.

## DLMM mechanics
- Bin step = price gap between bins in bps (100 bps = 1%). Small step = tight, calmer pairs.
  Big step = wide, survives volatility.
- Shapes: **Spot** (even spread, versatile) · **Curve** (stacked in middle, calm markets) ·
  **Bid-Ask** (stacked at edges, volatility / DCA in-out).
- One-sided SOL bid-ask under a token = DCA into it on the way down while earning fees;
  risk: end 100% in the token.
- Tight range = more fee density, out of range faster. Wide = more tolerance, thinner capital.

## PnL math
- Net = fees + price change − divergent (impermanent) loss − costs (rent, slippage, tx).
- Green fees ≠ green position. High fee % often just reflects extreme volatility.
- Some tools (e.g. Metlex) show PnL in USD; SOL price moves change the number.

## Safety checklist (volume is NOT safety)
1. CA from trusted source, never by ticker.  2. Exact pool address (bin step, fee, liquidity).
3. Mint/freeze authority (revoked ≠ safe).  4. Top holders + dev wallets (GMGN).
5. Bundling / linked wallets (Bubblemaps).  6. Fake volume: volume vs liquidity, unique traders,
   price barely moving.  7. LP lock for THAT pool.  8. Token age / narrative timing.
9. MC-per-holder / concentration.  10. Pool price vs Jupiter (divergence gets arbed through LPs).
Tools: RugCheck, Bubblemaps, GMGN, DexScreener, Solscan, Jupiter, Meteora, Metlex, Ultra LP.

## Operations
- Pool / bin-array creation rent is NOT refunded; position rent IS refunded on close.
- Zap Out has a bin limit: very wide positions may need normal withdraw + Jupiter swap.
- Partial withdraw, withdraw specific bins, rebalance, RPC + priority fee settings.
- Charts: RSI, MACD, VPVR, SuperTrend, Heikin Ashi — combine with flow + safety, never alone.

## Managing / exiting
- Before entry write: reason, size, holding period, range+shape, rebalance rule, close rule, max loss.
- Out of range options: hold, withdraw + re-enter, zap out, close. Depends on whether thesis holds.
- Close/reassess when: range left, fee flow fades, volume looks fake, price diverges from market,
  risk worsens, thesis broken, too concentrated in one asset.
- Process > prediction. Try to disprove the trade first. Start small. Record outcomes.
