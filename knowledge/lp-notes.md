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

## What experienced LPs teach on X (full detail: DLMM_KNOWLEDGE.md §15)
- Every strategy = **coin selection → pool selection → entry → exit**. Coin selection is ~80–90% of it.
- **Evil Panda strat** (@EvilPanda): coin pumping near ATH with real volume (MC ≥ $250K, 24h vol ≥ $1M,
  GMGN bundling < 60%, insiders < 10%, top-10 < 30%, ≥ 12h old) → **one-sided SOL Spot, −86% to −95%,
  in a 5–10% fee pool** (80/100/125 bin step) after a 15m SuperTrend break → let panic sellers pay fees on
  the dump → exit on **2 signals: RSI(2) close > 90 + close above upper Bollinger Band** (or MACD's first
  green bar). Wide range = rug insurance, Spot = more fees if the dip is only ~50%.
- **New/volatile coins: 5–10% fee pools.** A 100/2% pool on a fresh coin can be a dev or DAMM offloader.
- **Bonus Stage** (EvilPanda/@bengsharksol): after a big dump, when it chops sideways, open a **two-sided
  Bid-Ask** (Ape In default), layer another near the low if it bleeds, take profit on the pump, repeat.
  Never open two-sided near highs ("top blasting").
- **Token-sided Bid-Ask** = DCA out with fees; **flip**: SOL BA below fills → reopen as token BA above.
- **Spot vs Bid-Ask** (@ConstantineDeFi test): Spot earns more fees while price stays high in the range;
  Bid-Ask wins after a deep dump (lower average entry, profitable on a smaller bounce).
- **Risk**: 6–10 positions, start with 0.5–1 SOL, no revenge LP, size up only after clean days, don't
  babysit overnight. Tight-range LPs cut at the range floor (below −50% is "hell mode", @ChivesWork).
- **Weekly cycle**: normal → hot → crime season (rugs) → dry. Ease off when it's hot.
- **Pool structure**: lots of copy-trader TVL in one pool = they all dump when the lead wallet exits.
- Dynamic positions allow 1,400 bins; Ape In is 69 bins (≈ −50% on bin step 100). Quote Token Fees let
  fees accrue in SOL/USDC.
- **@0xMrBeefman**: check pool price vs Jupiter first (Sync with Jupiter, gap > 10–20% = you get arbed);
  add in parts; wide ≠ safe (low fees + −95% is just inefficient); hybrids (Spot near price + Bid-Ask
  below) print from the start where pure Bid-Ask sits idle; open below price and wait unless fees are hot
  now; Fri evening–Sat (EU) is the worst for slow cooks; cut positions that aren't printing.
- **HawkFi models** (automation): HFL (tight range, instant swapless rebalance), Precision Hybrid (50/50
  Spot+BA reshaped around price), MCU (Spot + compound + up-only rebalance, multi-day), Heart Attack
  (tight Spot for shallow corrections on launches). Theme: keep liquidity where price trades.

## What our data says (full detail: DLMM_KNOWLEDGE.md §17)
- 9 profitable wallets, 1,066 positions: +0.49% per position on average, fees outrun IL many times a day.
  Holds are minutes to hours (only > 24 h holds lose on average); 35–71% reopened in the same pool within
  3 min (they follow price); ~70–150 bins; worst 2% ≈ −10%, mostly < 1 h-old pools that rugged.
- Backtest of that style (1,005 trades): pool ≥ 6 h old, ≥ $60K/h volume, not down > 20% in 1 h → Spot
  +5%/−90% → re-center when price is +6%, leave when 30-min volume < $5K, max 12 h: +3.0%/trade in the
  model (real results will be worse). Depth matters: −70% ranges took big losses.
- Our alert paper bot: small take-profits worked; losses came from bin-array rent, a 14-minute-old pool
  rugging, and holding a crashing fresh pool for days. Liquidity leaving the pool was the common sign.
