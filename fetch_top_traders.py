#!/usr/bin/env python3
"""
Fetch the top Hyperliquid traders by profitability straight from Hyperliquid's
own public API (no API key, no cost), then pull each trader's live open
positions and recent fills. Writes one timestamped JSON snapshot per run.

Sources (all free, no auth):
  - Leaderboard: GET https://stats-data.hyperliquid.xyz/Mainnet/leaderboard
  - Per-trader:  POST https://api.hyperliquid.xyz/info  (clearinghouseState, userFills)

Usage:
  python3 fetch_top_traders.py

Tune via env vars:
  HL_WINDOW   day | week | month | allTime   (default: allTime)
  HL_TOP_N    how many top traders to inspect (default: 10)
  HL_OUT_DIR  output directory                (default: ./snapshots)
"""

import csv
import json
import os
import sys
import time
from datetime import datetime, timezone
from urllib import request, error

LEADERBOARD_URL = "https://stats-data.hyperliquid.xyz/Mainnet/leaderboard"
INFO_URL = "https://api.hyperliquid.xyz/info"

WINDOW = os.environ.get("HL_WINDOW", "allTime")   # day | week | month | allTime
TOP_N = int(os.environ.get("HL_TOP_N", "10"))
OUT_DIR = os.environ.get(
    "HL_OUT_DIR",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "snapshots"),
)


def _request(url, body=None, retries=3):
    headers = {"Content-Type": "application/json"} if body is not None else {}
    data = json.dumps(body).encode() if body is not None else None
    method = "POST" if body is not None else "GET"
    last_err = None
    for attempt in range(retries):
        try:
            req = request.Request(url, data=data, headers=headers, method=method)
            with request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode())
        except error.HTTPError as e:
            last_err = f"HTTP {e.code}: {e.read().decode(errors='replace')[:300]}"
        except Exception as e:  # noqa: BLE001
            last_err = str(e)
        time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"{method} {url} failed: {last_err}")


def get_top_traders():
    """Download the leaderboard and rank by PnL in the chosen window."""
    payload = _request(LEADERBOARD_URL)
    rows = payload.get("leaderboardRows", [])

    def window_pnl(row):
        for name, perf in row.get("windowPerformances", []):
            if name == WINDOW:
                try:
                    return float(perf.get("pnl", "0"))
                except (TypeError, ValueError):
                    return 0.0
        return 0.0

    rows.sort(key=window_pnl, reverse=True)
    return rows[:TOP_N]


def window_metrics(row, window):
    for name, perf in row.get("windowPerformances", []):
        if name == window:
            return {"pnl": perf.get("pnl"), "roi": perf.get("roi"), "vlm": perf.get("vlm")}
    return {"pnl": None, "roi": None, "vlm": None}


def get_live_positions(address):
    return _request(INFO_URL, {"type": "clearinghouseState", "user": address})


def get_recent_fills(address):
    return _request(INFO_URL, {"type": "userFills", "user": address})


def extract_open_positions(clearinghouse_state):
    out = []
    for ap in (clearinghouse_state or {}).get("assetPositions", []):
        p = ap.get("position", {})
        if not p:
            continue
        out.append({
            "coin": p.get("coin"),
            "szi": p.get("szi"),                  # signed size (+long / -short)
            "entryPx": p.get("entryPx"),
            "positionValue": p.get("positionValue"),
            "unrealizedPnl": p.get("unrealizedPnl"),
            "returnOnEquity": p.get("returnOnEquity"),
            "leverage": p.get("leverage"),
            "liquidationPx": p.get("liquidationPx"),
        })
    return out


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    ts = datetime.now(timezone.utc)

    leaders = get_top_traders()
    traders = []
    for rank, row in enumerate(leaders, start=1):
        addr = row.get("ethAddress")
        if not addr:
            continue
        try:
            ch = get_live_positions(addr)
            fills = get_recent_fills(addr)
        except RuntimeError as e:
            print(f"warn: {addr} live data failed: {e}", file=sys.stderr)
            ch, fills = {}, []
        traders.append({
            "rank": rank,
            "address": addr,
            "displayName": row.get("displayName"),
            "accountValue": row.get("accountValue"),
            "pnl": {w: window_metrics(row, w) for w in ("day", "week", "month", "allTime")},
            "openPositions": extract_open_positions(ch),
            "recentFills": (fills or [])[:20],
        })
        time.sleep(0.3)  # be polite to the info endpoint

    snapshot = {
        "fetchedAt": ts.isoformat(),
        "source": "hyperliquid-native",
        "rankedBy": WINDOW,
        "topN": TOP_N,
        "traders": traders,
    }

    out_path = os.path.join(OUT_DIR, f"top-traders-{ts.strftime('%Y%m%dT%H%M%SZ')}.json")
    with open(out_path, "w") as f:
        json.dump(snapshot, f, indent=2)

    write_csvs(snapshot)
    print(f"Wrote {out_path}  ({len(traders)} traders, ranked by {WINDOW} PnL)")


def write_csvs(snapshot):
    """Emit two flat, overwrite-in-place CSVs for live spreadsheet import."""
    root = os.path.dirname(OUT_DIR.rstrip("/")) or "."
    fetched = snapshot["fetchedAt"]

    # 1) one row per trader (summary)
    with open(os.path.join(root, "latest_traders.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "fetchedAt", "rank", "address", "displayName", "accountValue",
            "pnlDay", "pnlWeek", "pnlMonth", "pnlAllTime", "roiAllTime",
            "openPositions",
        ])
        for t in snapshot["traders"]:
            p = t["pnl"]
            w.writerow([
                fetched, t["rank"], t["address"], t.get("displayName") or "",
                t.get("accountValue"),
                p["day"]["pnl"], p["week"]["pnl"], p["month"]["pnl"],
                p["allTime"]["pnl"], p["allTime"]["roi"],
                len(t["openPositions"]),
            ])

    # 2) one row per open position
    with open(os.path.join(root, "latest_positions.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "fetchedAt", "rank", "address", "displayName", "coin", "side",
            "size", "entryPx", "positionValue", "unrealizedPnl",
            "returnOnEquity", "leverage", "liquidationPx",
        ])
        for t in snapshot["traders"]:
            for pos in t["openPositions"]:
                try:
                    szi = float(pos.get("szi") or 0)
                except ValueError:
                    szi = 0
                lev = pos.get("leverage") or {}
                w.writerow([
                    fetched, t["rank"], t["address"], t.get("displayName") or "",
                    pos.get("coin"), "long" if szi >= 0 else "short",
                    pos.get("szi"), pos.get("entryPx"), pos.get("positionValue"),
                    pos.get("unrealizedPnl"), pos.get("returnOnEquity"),
                    lev.get("value") if isinstance(lev, dict) else lev,
                    pos.get("liquidationPx"),
                ])


if __name__ == "__main__":
    main()
