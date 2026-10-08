# Meteora DLMM & LP knowledge base

Everything learned while building @SinClair_0000's LP content: the LP Army Academy course,
Meteora's docs and APIs, and live pool research. `knowledge/lp-notes.md` is the short version
the routines read; this is the full reference.

---

## 1. LP Army & the Academy

- **LP Army** (@met_lparmy) is Meteora's LP education community: free Academy at lparmy.com/academy,
  Discord with ranked roles, coaching/AMA sessions, community tools.
- **Roles seen**: Academy Trainee → **LP Army Private** (plus Engagement Squad, Degen, etc.).
- **How Private is earned (Academy path)**: complete the courses, pass **≥80% of the quizzes in
  "Practical"** to unlock the graduation task, pass the graduation task.
- **Bootcamp path (alternative)**: day 1 deposit ≥$100 in a non-stablecoin pair and hold ≥1h →
  "Boot Camp Trainee"; day 2 prove positive returns via exam + screenshots, manual review →
  NFT certificate + Private.
- **Private unlocks**: advanced training, exclusive channels, community tools (profit trackers,
  Dune dashboards), NFT certificate.

### Course map (lesson URLs)
1-1 intro & key terms · 1-4 DLMM mechanics · 2-2 LP safety · 2-3 price charts & tools ·
2-5 finding opportunities · 2-7 practical DLMM · 2-8 monitoring positions & portfolio ·
2-9 generating PnL cards. (`lparmy.com/academy/lesson-…`)

---

## 2. DeFi basics (course part 1)

- **Coin** = native to its chain (SOL). **Token** = issued on a chain (USDC on Solana).
- **CA (contract address)** uniquely identifies a token. Always use the verified CA, never the
  ticker; many tokens share a symbol.
- **CEX** custodial (exchange holds keys). **DEX** non-custodial (you sign).
- **Aggregator** (Jupiter) routes swaps across venues for better execution.
- **Validators** confirm Solana txs; staked SOL is collateral, misbehaviour is penalised.
- **RPC** = your wallet/app's connection to the network. Bad RPC or low priority fee → slow/failed txs.
- **AMM**: on-chain swaps against pooled liquidity, no order book. LPs deposit, traders swap,
  LPs earn a share of fees.
- **Concentrated liquidity**: capital focused around chosen prices → more fee capture per $, but
  the position can go out of range and become one-sided.

---

## 3. Meteora products

| Product | What it is | Key facts |
|---|---|---|
| **DLMM** | Dynamic Liquidity Market Maker: price split into discrete **bins** | You pick range, shape, bin step. Base + dynamic fees. Up to **1,400 bins/position**, resizable ranges. Some pools support limit-order style liquidity. Token-2022 support. |
| **DAMM v2** | Configurable constant-product AMM | Dynamic fees, **fee schedulers** (time- and market-cap-based, rate limiting), concentration options, **NFT positions**. Both tokens required. Fees **not** auto-compounded. **Earns MET points**. No lending yield. |
| **DAMM v1** (legacy) | Classic AMM + **Dynamic Vaults** | Lending yield on idle liquidity, auto-compounding. **PnL must be calculated manually.** One-sided deposits get **auto-swapped**. **No MET points.** |
| **DBC** | Dynamic Bonding Curve | Token launches; graduate automatically into DAMM v2. |
| **Alpha Vault** | Pre-launch deposits | Protected buys before public trading, pro-rata or FCFS. |
| **Presale Vault** | Presales | Fixed-price, FCFS, pro-rata. |
| Helpers | Zap, Dynamic Fee Sharing, Stake2Earn | Zap = enter/exit in one asset. |

### MET token & referral staking
- MET's main uses are **staking and revenue share**, not governance votes.
- **Referral Staking**: stakers get a share of eligible DLMM protocol fees.
  Cycle 1 paid $262K USDC to 3,977 wallets; Cycle 2 (ended 21 Sep 2026) paid **$700K+**, 89M+ MET
  staked, 11,000+ users referred.

### Protocol numbers (for data posts)
- **H1 2026**: LPs earned **~$140M fees on ~$32B volume**; **~75% ($105M)** from tokens **not**
  launched on Meteora.
- **August 2026**: $5.4B volume (+37.9% MoM), $27.5M fees; DLMM volume +39.8% MoM, DLMM fees +56.4% MoM.

---

## 4. DLMM mechanics (course 1-4)

- **Bin** = a discrete price container holding liquidity. Only bins that price trades through earn
  fees (the active bin does the work).
- **Bin step** = price gap between neighbouring bins in basis points. **100 bps = 1%.**
  Small step → tight spacing, calmer pairs (SOL-USDC uses 4 bps). Large step (80–200+) → wide
  spacing, survives volatility, typical for memecoins.
- **Bins needed for a range** ≈ ln(upper/lower) / ln(1 + binstep/10000).
  e.g. bin step 100, −85% → 0%: ln(1/0.15)/ln(1.01) ≈ **191 bins**.
- Pools and bins hold liquidity from many LPs; one LP leaving doesn't destroy the pool.

### The three shapes (Meteora's definitions)
| Shape | Distribution | Use when |
|---|---|---|
| **Spot** | Even across the range | Versatile default; most conditions |
| **Curve** | Stacked in the middle, tapering out | Calm / ranging markets, stable-ish pairs; most capital-efficient if price stays put |
| **Bid-Ask** | Stacked at the edges (inverse of curve) | Volatility; DCA in on dips / out on pumps; catching big swings |

- The shape is your **thesis**: pick it from what you expect price to do, not from a screenshot.
- **One-sided SOL Bid-Ask below price** = DCA into the token as it drops while earning fees.
  Risk: if it keeps dropping you end up **100% in the token**. Only on tokens you'd hold.
- Tight range = high fee density, out of range fast. Wide range = tolerance, thinner capital.

### Fees
- Base fee (set per pool, e.g. 0.04% SOL-USDC, 1–3%+ on memes) + **dynamic fee** that rises with
  volatility. Some pools have farm rewards.
- **High fee % is not automatically good**: it often just reflects extreme volatility, poor
  liquidity, or big inventory risk. The real question: *will real trading flow pay more than the
  inventory conversion, divergent loss and execution costs?*

---

## 5. Impermanent / divergent loss & PnL

- **IL / divergent loss** = value of LPing minus value of just holding. As price moves through your
  range, your mix shifts toward the falling asset.
- **Net result = fee income + token price change − divergent loss − costs** (rent, slippage, tx fees).
- **Green fees ≠ green position.** A position can be +20% in fees and −40% overall after the token
  dumps through the range. Conversely a volatile pool can be very profitable if fees outrun it.
- **USD vs SOL**: Metlex and others show PnL in **USD**; if SOL moved, the USD number moves even if
  the SOL result didn't. Always know your unit.
- The real performance question: after fees, divergent loss, price movement, slippage, rent and
  tx costs, did the **strategy** produce a **repeatable** net result?

---

## 6. LP safety (course 2-2): volume is NOT safety

A pool can show huge volume and still be manipulated, bundled, or one wallet from zero.

### Pre-entry checks
1. **Exact token CA** from a trusted source, never the ticker.
2. **Exact pool address**: same token, many pools with different bin step, fee, liquidity, locks.
3. **Mint & freeze authority**: revoked removes 2 admin risks but **does not** make it safe.
4. **Top holders & dev wallets**: concentration, linked wallets, unexplained supply control.
5. **Bundling / wallet relationships**: GMGN + **Bubblemaps** reveal wallets funded together or
   receiving tokens together. Spiderweb map = you're exit liquidity.
6. **Wash trading / fake volume**: volume insanely high vs liquidity, few unique traders, huge
   volume but price barely moves. Real flow is messy; fake flow is suspiciously smooth.
7. **LP lock for THAT pool**: a "locked" headline may refer to another pool.
8. **Token age & narrative timing**: the narrative may already be priced in or fading.
9. **Market-cap-per-holder** and other concentration signals (warnings, not decisions).
10. **Price divergence vs Jupiter / external markets**: arbs rebalance through your liquidity and
    you're the cheap side.

Tools answer different questions: **RugCheck** (authorities, risks, LP lock %), **Bubblemaps**
(clusters), **GMGN** (holders, dev, bundles), **DexScreener** (flow, charts), **Solscan** (txs),
**Jupiter** (reference price), **Meteora** (pool data). No single "safety score" replaces the process.
**Even a token that passes every check can still collapse.** Checks reduce avoidable risk, not market risk.

---

## 7. Charts & timing (course 2-3)

- **RSI**: overbought (>70) / oversold (<30).
- **MACD**: momentum and trend changes.
- **VPVR** (volume profile): where volume traded across price levels. The point of control (POC)
  and high-volume nodes are natural places to put liquidity; LP-relevant.
- **SuperTrend**: trend following. **Heikin Ashi**: smoothed candles, clearer trend structure.
- Volume analysis matters most for LPs: no trading = no fees.
- TA on new tokens is low-confidence; combine with liquidity, flow, age and safety. The goal is a
  better probability estimate, not a prediction.

---

## 8. Finding opportunities (course 2-5)

Sources: Meteora pool screens, DexScreener, GMGN, community channels, holder data.
1. Find pools with meaningful activity.
2. Compare **volume vs active liquidity vs fees** (fee/TVL, volume/TVL).
3. Check the activity is organic enough to bother.
4. Run the full safety process.
5. Pick the best mix of liquidity, fee structure, activity and manageable risk.

**"Volume is king"** = no trading, no fees. It does **not** mean the highest-volume pool is best.

---

## 9. Strategy & range selection

| Market | Shape | Side | Range idea |
|---|---|---|---|
| Downtrend (24h ≤ −30%) | Bid-Ask | one-sided SOL below | −40% to −85%; DCA in, fees on the chop |
| After a pump (24h ≥ +40%) | Spot | one-sided SOL below | −25% to −60%; catch the pullback, don't chase |
| High volatility / pool < 2 days old | Bid-Ask | one-sided SOL below | −35% to −80%, **small size** |
| Range-bound, calm | Spot (or Curve) | two-sided | ± half the 24h range (min ±8%) |

- Range width is a **risk control**. Volatile/uncertain tokens: start small, wider downside range.
- Adapt to the market regime; no setup is universal.
- These are rules of thumb used for the "example setup" panel in research charts, never advice.

---

## 10. Operating positions on Meteora (course 2-7)

- Create position; one-sided or two-sided deposit; **Ape In** for quick entry; **Zap Out** to exit
  into one asset; partial withdraw; withdraw from specific bins; rebalance / new position;
  liquidity & swap slippage; RPC and global priority-fee settings.
- Follow pool warnings before depositing.
- **Creating pools and bin arrays costs rent that is NOT refunded.**
- **Position rent IS refunded** when you close the position (closing dust positions reclaims SOL).
- **Zap Out has a bin limit**: very wide positions may need a normal withdraw + Jupiter swap.

---

## 11. Managing & exiting

**Before entry, write down**: reason, max size, holding period, range + shape, rebalance rule,
close rule, max acceptable loss.

**Out of range? Don't react emotionally.** Options: hold, compound, claim/sell fees, withdraw,
close, or open a new range. Depends on trend, token risk, liquidity, fee flow, inventory exposure.

**Close or reassess when**: price leaves the intended range · fee flow fades · volume looks
artificial · price diverges from external markets · risk profile worsens · the thesis is no longer
true · the position is too concentrated in one asset. "It might come back" is not on the list.

Don't blindly rebalance just because fees are positive.

---

## 12. Monitoring & PnL cards (course 2-8, 2-9)

- Monitor regularly: Meteora portfolio, **Ultra LP**, **Metlex**, Solscan, DexScreener, GMGN, safety tools.
- Track **realized** (closed) and **unrealized** (open) PnL. Tools calculate differently.
- **PnL cards**: find open/close txs on Solscan; Meteora keeps history for eligible closed positions;
  pool pages show position history; **Metlex** turns a position into a shareable card.
- A credible report shows: exact pool + CA, strategy + range, entry/exit txs, time in position,
  fees + net PnL, risks identified before entry, and what would have made you exit.
- Never present a profitable result as proof the token was safe.

---

## 13. The professional LP mindset

1. Plan, not emotion. 2. Try to **disprove** the trade before justifying it. 3. Verify exact token
and pool. 4. Volume = fee opportunity, not safety. 5. Match shape and range to the market.
6. Start small when testing. 7. Monitor and react to evidence. 8. Some trades should be passed on.
9. Record outcomes and improve. 10. Never risk money you can't lose.

The goal isn't finding a pool that can't rug. It's filtering hard, sizing rationally, earning fees
when real flow exists, and exiting when the thesis breaks.

### Pre-entry checklist
- [ ] CA from a trusted source  - [ ] exact pool address  - [ ] mint/freeze authority
- [ ] top holders, dev, bundling, insider links  - [ ] wash-trading risk
- [ ] active liquidity vs volume vs fees  - [ ] LP lock on this pool  - [ ] price vs Jupiter
- [ ] chart structure + volume  - [ ] shape, bin step, range  - [ ] size + max loss
- [ ] exit and out-of-range rules written down

---

## 14. Lessons from live research (Oct 2026)

- **AUTON-SOL**: top pool by fee/TVL on 7 Oct (fee/TVL 74%, $12.8M vol on $315K TVL, 40x vol/TVL,
  21h old, rugcheck clean, freeze revoked). **Next day: −72% on the day.** A clean safety check
  and huge fees on a <1-day-old pool still meant a knife.
- **GOMO-SOL** (8 Oct): fee/TVL 51%, $600K vol on $39K TVL, but −50% on the day and a 500%+ 24h
  range; volume already fading. Example setup: Bid-Ask, one-sided SOL, −85%→0%, ~191 bins.
- Top fee/TVL lists are dominated by **< 2-day-old memecoin pools**. Treat high fee/TVL there as a
  volatility signal as much as an opportunity.
- Same token often has **several pools** (different bin steps 80/100/125/200). Compare them.

---

## 15. Data sources & APIs (all free unless noted)

| Source | Endpoint | Gives |
|---|---|---|
| Meteora DLMM data API | `https://dlmm.datapi.meteora.ag` | `GET /pools` (`sort_by=fee_tvl_ratio_24h:desc`, `filter_by=tvl>25000 && volume_24h>250000 && is_blacklisted=false`), `/pools/{addr}`, `/pools/{addr}/ohlcv?timeframe=30m|1h&start_time&end_time` (**always pass end_time**), `/portfolio?user=`, `/positions/{pool}/pnl?user=`, `/stats/protocol_metrics`. OpenAPI: docs.meteora.ag/developer-guides/dlmm/api-reference/openapi.json |
| Pool fields | | tvl, volume/fees/fee_tvl_ratio per 30m/1h/2h/4h/12h/24h (fee_tvl_ratio is already in **%**), pool_config (bin_step, base_fee_pct), dynamic_fee_pct, token_x/y (holders, market_cap, freeze_authority_disabled), created_at (ms). OHLCV price = token_y per token_x |
| DexScreener | `api.dexscreener.com/latest/dex/pairs/solana/{a,b,c}` (up to 30) | buys/sells m5/h1/h6/h24, priceChange, liquidity, fdv, socials. Page screenshots are unreliable (stale candles, Cloudflare); use the API |
| RugCheck | `api.rugcheck.xyz/v1/tokens/{mint}/report/summary` | score, risks[{level,name}], lpLockedPct |
| twitterapi.io (paid) | `api.twitterapi.io/twitter/tweet/advanced_search`, `/twitter/user/last_tweets`, `/oapi/my/info` | ~$0.15/1K tweets; header `X-API-Key`; balance = recharge_credits + total_bonus_credits (100K credits = $1) |
| Meteora app | `app.meteora.ag/dlmm/{pool}` | open a position on that exact pool |
