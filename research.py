"""Live Meteora DLMM pool research + chart images. No API key needed.

  python3 research.py scan            -> out/pools.json   (top pools by fee/TVL, with safety data)
  python3 research.py chart <address> -> out/chart.png    (72h price + volume, stats panel)

Data: Meteora DLMM data API (dlmm.datapi.meteora.ag) + RugCheck summary (api.rugcheck.xyz).
"""
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
OUT = ROOT / "out"
METEORA = "https://dlmm.datapi.meteora.ag"
RUGCHECK = "https://api.rugcheck.xyz/v1/tokens/{}/report/summary"
QUOTES = {"So11111111111111111111111111111111111111112", "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
          "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"}


def get(url, params=None):
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "sinclair-x-bot", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def rugcheck(mint):
    try:
        d = get(RUGCHECK.format(mint))
        return {
            "score_normalised": d.get("score_normalised"),
            "lp_locked_pct": d.get("lpLockedPct"),
            "risks": [f"{r.get('level')}: {r.get('name')}" for r in d.get("risks", [])],
        }
    except Exception as e:  # rugcheck is rate-limited / flaky; research continues without it
        return {"error": str(e)}


def summarize(p):
    base, quote = (p["token_x"], p["token_y"]) if p["token_x"]["address"] not in QUOTES else (p["token_y"], p["token_x"])
    age_h = (time.time() - p["created_at"] / 1000) / 3600
    vol, tvl = p["volume"]["24h"], p["tvl"]
    return {
        "address": p["address"],
        "name": p["name"],
        "url": f"https://app.meteora.ag/dlmm/{p['address']}",
        "quote_symbol": quote["symbol"],
        "base_token": {
            "symbol": base["symbol"], "mint": base["address"], "verified": base.get("is_verified"),
            "holders": base.get("holders"), "market_cap": base.get("market_cap"),
            "freeze_authority_disabled": base.get("freeze_authority_disabled"),
        },
        "pool_age_hours": round(age_h, 1),
        "bin_step": p["pool_config"]["bin_step"],
        "base_fee_pct": p["pool_config"]["base_fee_pct"],
        "dynamic_fee_pct": p.get("dynamic_fee_pct"),
        "tvl": round(tvl),
        "volume_1h": round(p["volume"]["1h"]),
        "volume_24h": round(vol),
        "fees_24h": round(p["fees"]["24h"]),
        "fee_tvl_pct_24h": round(p["fee_tvl_ratio"]["24h"], 2),
        "fee_tvl_pct_1h": round(p["fee_tvl_ratio"]["1h"], 3),
        "volume_to_tvl": round(vol / tvl, 1) if tvl else None,
        "mc_per_holder": round(base["market_cap"] / base["holders"]) if base.get("holders") and base.get("market_cap") else None,
    }


def scan(limit=8):
    d = get(f"{METEORA}/pools", {
        "page_size": 40,
        "sort_by": "fee_tvl_ratio_24h:desc",
        "filter_by": "tvl>25000 && volume_24h>250000 && is_blacklisted=false",
    })
    pools = [summarize(p) for p in d["data"]][:limit]
    for p in pools:
        p["rugcheck"] = rugcheck(p["base_token"]["mint"])
        time.sleep(0.5)
    try:
        metrics = get(f"{METEORA}/stats/protocol_metrics")
    except Exception:
        metrics = None
    OUT.mkdir(exist_ok=True)
    out = {"generated_at": datetime.now(timezone.utc).isoformat(), "protocol_metrics": metrics, "pools": pools}
    (OUT / "pools.json").write_text(json.dumps(out, indent=2) + "\n")
    print(f"{len(pools)} pools -> out/pools.json")
    for p in pools:
        print(f"  {p['name']:<22} tvl ${p['tvl']:>9,}  vol24 ${p['volume_24h']:>11,}  fee/tvl {p['fee_tvl_pct_24h']:>6}%  "
              f"bin {p['bin_step']:>3}  age {p['pool_age_hours']}h  {p['address']}")


def chart(address, hours=72):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    p = summarize(get(f"{METEORA}/pools/{address}"))
    tf = "1h" if hours > 24 else "30m"
    candles = get(f"{METEORA}/pools/{address}/ohlcv",
                  {"timeframe": tf, "start_time": int(time.time() - hours * 3600), "end_time": int(time.time())})["data"]
    if not candles:
        sys.exit("no candles for this pool")

    span_h = round((candles[-1]["timestamp"] - candles[0]["timestamp"]) / 3600) + (1 if tf == "1h" else 0)
    bg, fg, dim, up, down, accent = "#0d1117", "#e6edf3", "#7d8590", "#3fb950", "#f85149", "#f5a623"
    fig = plt.figure(figsize=(12, 6.75), dpi=150, facecolor=bg)
    ax = fig.add_axes([0.05, 0.30, 0.62, 0.58], facecolor=bg)
    axv = fig.add_axes([0.05, 0.10, 0.62, 0.17], facecolor=bg, sharex=ax)

    w = 0.7
    for i, c in enumerate(candles):
        col = up if c["close"] >= c["open"] else down
        ax.plot([i, i], [c["low"], c["high"]], color=col, linewidth=1)
        lo, hi = sorted([c["open"], c["close"]])
        ax.add_patch(Rectangle((i - w / 2, lo), w, max(hi - lo, (c["high"] - c["low"]) * 0.01 or 1e-12), color=col))
        axv.bar(i, c["volume"], width=w, color=col, alpha=0.6)
    ax.set_xlim(-1, len(candles))
    ax.set_ylim(min(c["low"] for c in candles) * 0.97, max(c["high"] for c in candles) * 1.03)

    step = max(1, len(candles) // 6)
    ticks = list(range(0, len(candles), step))
    axv.set_xticks(ticks)
    axv.set_xticklabels([datetime.fromtimestamp(candles[i]["timestamp"], timezone.utc).strftime("%d %b %H:%M") for i in ticks])
    for a in (ax, axv):
        a.tick_params(colors=dim, labelsize=8)
        for s in a.spines.values():
            s.set_color("#30363d")
        a.grid(color="#21262d", linewidth=0.6)
    plt.setp(ax.get_xticklabels(), visible=False)
    axv.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: usd(v)))
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:.3g}"))
    ax.set_ylabel(f"price ({p['quote_symbol']})", color=dim, fontsize=8)
    axv.set_ylabel("volume", color=dim, fontsize=8)

    fig.text(0.05, 0.93, f"{p['name']}  ·  Meteora DLMM", color=fg, fontsize=17, weight="bold")
    fig.text(0.05, 0.895, f"{tf} candles · last {span_h}h · {address[:6]}…{address[-4:]}", color=dim, fontsize=9)

    rc = rugcheck(p["base_token"]["mint"])
    bt = p["base_token"]
    rows = [
        ("TVL", usd(p["tvl"])),
        ("24h volume", usd(p["volume_24h"])),
        ("24h fees", usd(p["fees_24h"])),
        ("fee / TVL 24h", f"{p['fee_tvl_pct_24h']}%"),
        ("volume / TVL", f"{p['volume_to_tvl']}x"),
        ("bin step", f"{p['bin_step']} bps"),
        ("base fee", f"{p['base_fee_pct']}%"),
        ("pool age", f"{p['pool_age_hours'] / 24:.1f}d" if p["pool_age_hours"] >= 48 else f"{p['pool_age_hours']:.0f}h"),
        ("holders", f"{bt['holders']:,}" if bt.get("holders") else "n/a"),
        ("market cap", usd(bt["market_cap"]) if bt.get("market_cap") else "n/a"),
        ("freeze auth", "revoked" if bt.get("freeze_authority_disabled") else "ACTIVE"),
        ("rugcheck risks", str(len(rc.get("risks", []))) if "error" not in rc else "n/a"),
    ]
    y = 0.86
    fig.text(0.72, y, "POOL CHECK", color=accent, fontsize=11, weight="bold")
    for k, v in rows:
        y -= 0.058
        fig.text(0.72, y, k, color=dim, fontsize=10)
        warn = v == "ACTIVE" or (k == "rugcheck risks" and v not in ("0", "n/a"))
        fig.text(0.97, y, v, color=down if warn else fg, fontsize=10, ha="right", weight="bold")
    fig.text(0.97, 0.03, "@SinClair_0000 · not financial advice", color=dim, fontsize=8, ha="right")

    OUT.mkdir(exist_ok=True)
    fig.savefig(OUT / "chart.png", facecolor=bg)
    p["rugcheck"] = rc
    (OUT / "chart_pool.json").write_text(json.dumps(p, indent=2) + "\n")
    print(f"chart -> out/chart.png ({p['name']}, {len(candles)} candles); stats -> out/chart_pool.json")


def usd(v):
    v = float(v)
    for div, suf in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if abs(v) >= div:
            return f"${v / div:.1f}{suf}"
    return f"${v:.0f}"


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "scan":
        scan()
    elif len(sys.argv) >= 3 and sys.argv[1] == "chart":
        chart(sys.argv[2])
    else:
        sys.exit(__doc__)
