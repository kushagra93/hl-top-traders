# hl-top-traders

Hourly snapshots of the **top Hyperliquid traders by profitability** and their
**live open positions + recent fills**, fetched straight from Hyperliquid's
public API. No API key, no cost.

## How it works

[`fetch_top_traders.py`](fetch_top_traders.py):

1. Downloads the leaderboard from `https://stats-data.hyperliquid.xyz/Mainnet/leaderboard`
   and ranks traders by PnL in the chosen window.
2. For each of the top N, calls `https://api.hyperliquid.xyz/info` for
   `clearinghouseState` (live open positions) and `userFills` (recent trades).
3. Writes a timestamped JSON snapshot to `snapshots/`.

A GitHub Actions workflow ([`.github/workflows/snapshot.yml`](.github/workflows/snapshot.yml))
runs it hourly and commits each new snapshot back to the repo.

## Run locally

```bash
HL_WINDOW=allTime HL_TOP_N=10 python3 fetch_top_traders.py
```

| Env var      | Default    | Values                          |
|--------------|------------|---------------------------------|
| `HL_WINDOW`  | `allTime`  | `day` `week` `month` `allTime`  |
| `HL_TOP_N`   | `10`       | any integer                     |
| `HL_OUT_DIR` | `./snapshots` | output directory             |

## Run on demand in GitHub

Actions tab → **Snapshot top Hyperliquid traders** → **Run workflow** (lets you
override window / top-N).

## Notes

- GitHub disables scheduled workflows after **60 days of no repo activity** —
  the hourly commits keep it alive, but if you ever pause it, re-enable from the
  Actions tab.
- Other data sources with richer metrics (paid): HyperTracker / CoinMarketMan,
  Nansen, Apify Hyperliquid scrapers.
