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

## View as a spreadsheet

Each run overwrites two flat CSVs at the repo root (always the latest data):

- `latest_traders.csv` — one row per top trader (rank, PnL windows, account value, # open positions)
- `latest_positions.csv` — one row per open position (coin, side, size, entry, value, uPnL, leverage, liq price)

**Three ways to use them:**

1. **GitHub table view** — just open the CSV in the repo; GitHub renders it as a
   sortable, searchable table.
2. **Instant table browser** — [flatgithub.com/kushagra93/hl-top-traders](https://flatgithub.com/kushagra93/hl-top-traders) (filter/sort the JSON or CSV, no setup).
3. **Live Google Sheet** — in any cell, pull the raw CSV so the sheet auto-refreshes:
   ```
   =IMPORTDATA("https://raw.githubusercontent.com/kushagra93/hl-top-traders/main/latest_positions.csv")
   ```
   ```
   =IMPORTDATA("https://raw.githubusercontent.com/kushagra93/hl-top-traders/main/latest_traders.csv")
   ```
   Google re-fetches roughly hourly; File → Share → "Anyone with the link" makes it a public spreadsheet.

## Notes

- GitHub disables scheduled workflows after **60 days of no repo activity** —
  the hourly commits keep it alive, but if you ever pause it, re-enable from the
  Actions tab.
- Other data sources with richer metrics (paid): HyperTracker / CoinMarketMan,
  Nansen, Apify Hyperliquid scrapers.
