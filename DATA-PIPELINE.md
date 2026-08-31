# Data Pipeline Reference

Quick reference for updating everything this repo produces when a new month of
Census trade data becomes available.

**Since 2026-08, this repo downloads nothing.** The canonical HS10 dataset
lives in `../trade-data` (imports + exports, 2013-01 → present, 63 entities,
seven-check validation gate). That repo *builds the input files into this one*
in the exact schema the notebooks here have always read, so the analysis
notebooks are unchanged — only Stage 1 moved.

---

## Monthly Update Checklist

Census publishes a month roughly **five weeks after it ends**, with the FT900
release (~8:30 AM ET). Using `2026-07` as the example month:

### Stage 1 — refresh the data (in `../trade-data`)

1. **Probe that the month is actually on the API** — the FT900 press release
   and the detail API don't always land together. In `../trade-data`, use
   `tradedata.census.build_url` + `fetch` for one entity-month (writes
   nothing). An empty answer means *wait*, not debug.
2. ```powershell
   cd C:\heroku\trade-data
   python scripts/build_history.py --end 2026-07
   ```
   `--end` is mandatory in practice — omitting it burns ~126 calls on an
   unpublished month. Idempotent and resumable; **the exit code alone is the
   verdict** (non-zero = a download, combine, or validation check failed).
   Budget ~10 min download + ~40 min combine/validate per flow.
3. **Run `../trade-data/notebooks/04-build-tri-country-product.ipynb`** — it
   rebuilds the 33 files in `data/imports-hs10/` here (30 countries + EU +
   USMCA + TOTAL), verifying each one against the previous vintage *before*
   writing. The gate only passes appended new months plus changes inside the
   revision band; anything else raises and writes nothing for that entity.
4. **Commit this repo** — the refreshed parquets are the data update:
   ```powershell
   cd C:\heroku\how-restrictive-us-trade
   git add data/imports-hs10; git commit -m "July 2026 data"; git push
   ```
   (Never `git add -A` blindly — `ALL-data-current.parquet` and monthly
   snapshots are gitignored, but stay explicit anyway.)

### Stage 2 — paper outputs (only when updating the paper)

5. **`TRI-all-country.ipynb`**: set `target_date = "2026-07"`, Run All →
   `results.tex`, `table.tex`, histogram + panel figures,
   `data/top-country-metrics.parquet`.
6. **`TRI-sector.ipynb`** and **`TRI-composition.ipynb`** (same
   `target_date`) if sector / end-use outputs are wanted.
7. Paper gotchas (`C:\github\how-restrictive-us-trade-paper`):
   - Two savefigs are **commented out** (the Canada panel in TRI-all-country,
     the whole end-use figure in TRI-composition) — re-enable them or they
     silently keep their old vintage.
   - The `.tex` **hardcodes histogram filenames by date** (e.g.
     `2025-12-histogram.pdf`) while the notebooks write `{target_date}`-named
     files — point the `\includegraphics` lines at the months you want.
   - Check every number quoted in prose against the regenerated macros, then
     rebuild the PDF.

### Stage 3 — the live tracker (can run without Stage 2)

8. **`TRI-tracker-update.ipynb`**: set `target_date = "2026-07"`, Run All. It
   needs only the Stage 1 files plus the statutory CSVs from
   `../../github/trade-war-redux-2025/` — refresh those there first if you
   want current announced-tariff lines.
9. **Deploy** — the notebook only writes
   `../TRI-tracker/data/tri-all-country-data.parquet` locally:
   ```powershell
   cd C:\heroku\TRI-tracker
   git add data/tri-all-country-data.parquet
   git commit -m "Update tracker data through 2026-07"
   git push heroku main    # see note below
   ```
   ⚠ There is currently **no `heroku` remote configured locally** — confirm on
   the Heroku dashboard whether the app deploys from GitHub (then
   `git push origin main` suffices, like the other tracker apps) or re-add the
   remote. Live app:
   `https://tri-tracker-d17ad5511b2b.herokuapp.com/main-tri-tracker`

### Sanity checks while reviewing any update

- **Revisions look like**: month-specific, sign-flipping deltas confined to
  the revision band (January three calendar years back → present). Expected
  every vintage.
- **A scope error looks like**: a *uniform* shift across countries or months —
  almost always a missing `rp == "-"` grain filter or a bloc summed with its
  members. Stop and investigate; do not ship it.
- The tracker's announced-tariff line may extend months past the TRI lines
  (statutory data is forward-looking; Census-derived columns are nulled past
  the last observed month). Designed behavior, not a bug. The display window
  in `../TRI-tracker/main-tri-tracker.py` (`final_month`/`final_year`) needs a
  manual bump when the data approaches it.

---

## Pipeline Stages

```
Census Bureau API
       │
       ▼
[Stage 1] ../trade-data repo                      ← canonical HS10 base (imports + exports,
       │   scripts/build_history.py                  2013–present, validated 7-check gate)
       │   notebooks/04-build-tri-country-product.ipynb
       ▼
data/imports-hs10/*data-current.parquet           ← 33 files: one per country + EU, USMCA, TOTAL
       │
       ├──▶ [Stage 2a] TRI-all-country.ipynb   ──▶ top-country-metrics.parquet
       │                                             results.tex (LaTeX macros)
       │                                             histogram + time-series figures
       │
       ├──▶ [Stage 2b] TRI-sector.ipynb        ──▶ top-sector-metrics.parquet
       │                                             table-sector.tex
       │                                             panel sector figures
       │
       ├──▶ [Stage 2c] TRI-composition.ipynb   ──▶ enduse-metrics.parquet
       │                                             panel-enduse-tariffs.png/.pdf
       │
       └──▶ [Stage 3]  TRI-tracker-update.ipynb ──▶ ../TRI-tracker/data/tri-all-country-data.parquet
                    (+ external statutory CSVs        (feeds the Heroku Bokeh app)
                     from ../../github/
                     trade-war-redux-2025/)
```

---

## Notebooks

### Stage 1 — the `../trade-data` repo (replaces the retired download notebooks)

The canonical base is validated by a seven-check gate (duplicates, vintage,
completeness, coverage, entity kind, grain reconciliation, frozen countries).
See `../trade-data/README.md` for the two rules for reading it without
double-counting, and its `STATUS.md` for the verification record.

Its `notebooks/04-build-tri-country-product.ipynb` writes the 33 files into
`data/imports-hs10/` here in the exact legacy schema — all-string columns,
`time` as `YYYY-MM`, TOTAL without `CTY_CODE` — and refuses to write any file
whose diff against the previous vintage is not a clean refresh. The entity
list: the 30 countries in `country-list.csv`, plus the EU (`0003`) and USMCA
(`0020`) **blocs** (these contain their own member countries — never sum them
with individual countries; Canada is `1220`, Mexico is `2010`), plus
`TOTALdata-current.parquet`.

**Retired** (files kept for history; superseded 2026-08-31):

- `make-imports-hs10-dataset.ipynb` and
  `make-imports-hs10-dataset-current-month.ipynb` — the old Census pulls,
  including the blind-append bug (re-running a month appended it twice).
  Do not run them; they would overwrite verified files with an unverified pull.
- `data/imports-hs10/{CTY_CODE}data-{YYYY-MM}.parquet` monthly snapshots
  (untracked, gitignored; safe to delete)
- `data/imports-hs10/ALL-data-current.parquet` — read by nothing;
  `trade-miner` now reads trade-data's own ALL files directly (untracked,
  gitignored; safe to delete)

### Stage 2a — `TRI-all-country.ipynb`

Computes the three tariff measures by country over time.

**Variable to update each month:**
```python
target_date = "2026-07"   # ← change this
```

Tariff measures computed (weights = 2024 import shares at the HS10×country level):

| Measure | Formula | Variable |
|---|---|---|
| TRI | $\sqrt{\sum_i w_i \tau_i^2}$ | `sqrtariff` |
| Weighted mean | $\sum_i w_i \tau_i$ | `meanweighted` |
| Simple mean | $\sum \text{Duties} / \sum \text{Imports}$ | `simplemean` |

Outputs: `results.tex` (LaTeX macros for paper), `data/top-country-metrics.parquet`, PNG/PDF figures

### Stage 2b — `TRI-sector.ipynb`

Breaks down TRI by HS2 two-digit sector (Machinery=84, Electrical=85, Vehicles=87, Pharma=30, etc.).

- Uses top 10–20 HS2 sectors by 2024 import value
- Excludes HS2 codes 27 (petroleum), 71 (gems), 98, 99 (special classifications)
- Outputs: `data/top-sector-metrics.parquet`, `table-sector.tex`, panel figures

### Stage 2c — `TRI-composition.ipynb`

Decomposes TRI by BEA end-use category using `data/hs6-enduse.parquet`.

| Category | Code |
|---|---|
| Consumer goods | `CONS` |
| Capital goods | `CAP` |
| Intermediate goods | `INT` |

Outputs: `data/enduse-metrics.parquet`, `panel-enduse-tariffs.png/.pdf`

### Stage 3 — `TRI-tracker-update.ipynb` (Heroku tracker)

Standalone updater for the **live Heroku tracker site** — run this when you
only need to refresh the interactive app, without regenerating any paper
results (Stage 2a–2c). Reads the `*data-current.parquet` files (so Stage 1
must already include the target month) and recomputes the three country
tariff measures as a daily time series.

**Variable to update each month:**
```python
target_date = "2026-07"   # ← change this
```

**External dependency — pulled in from a *different* repo:** the notebook also
reads statutory tariff data from `../../github/trade-war-redux-2025/`:

| File | Used for |
|---|---|
| `country-by-time.csv` | Per-country announced/statutory effective tariff |
| `daily-tariff-latest-data.csv` | Daily import-weighted "ALL COUNTRIES" statutory tariff |

Refresh those CSVs in the `trade-war-redux-2025` repo first if you want
current statutory numbers.

**Output:** writes directly into the separate tracker repo at
`../TRI-tracker/data/tri-all-country-data.parquet` (also rewrites
`data/top-country-metrics.parquet` here). Deploying is a separate manual step —
see the checklist above, including the note about the missing `heroku` remote.

---

## Data Files Reference

| File | Description | Produced by |
|---|---|---|
| `data/imports-hs10/{CTY_CODE}data-current.parquet` | Full monthly time series per country | Stage 1 (`../trade-data` notebook 04) |
| `data/imports-hs10/TOTALdata-current.parquet` | Census's published all-country total | Stage 1 (`../trade-data` notebook 04) |
| `data/imports-hs10/{CTY_CODE}data-{YYYY-MM}.parquet` | *(retired)* single-month snapshots | old pipeline — gitignored, deletable |
| `data/imports-hs10/ALL-data-current.parquet` | *(retired)* concatenation, read by nothing | old pipeline — gitignored, deletable |
| `data/top-country-metrics.parquet` | TRI time series by country | Stage 2a (also rewritten by Stage 3) |
| `data/top-sector-metrics.parquet` | TRI time series by HS2 sector | Stage 2b |
| `data/enduse-metrics.parquet` | TRI time series by end-use category | Stage 2c |
| `../TRI-tracker/data/tri-all-country-data.parquet` | Daily tariff series feeding the Heroku app | Stage 3 |
| `../../github/trade-war-redux-2025/country-by-time.csv` | Per-country statutory tariffs (external repo) | Stage 3 input |
| `../../github/trade-war-redux-2025/daily-tariff-latest-data.csv` | Daily ALL-COUNTRIES statutory tariff (external repo) | Stage 3 input |
| `data/hs6-enduse.parquet` | BEA end-use classification (HS6 → CONS/CAP/INT) | static |
| `data/country-list.csv` | The 30 country codes for the main analysis | static (pinned; mirrored as `FROZEN_COUNTRY_CODES` in `../trade-data/config.py`) |
| `data/country-list-20.csv` | Top 20 trading partners (sector/composition) | static |

---

## Parquet Schema (`*data-current.parquet`)

All columns are **strings** (the notebooks cast values with `.astype(float)`
and slice codes with `.str[...]`), in this order:

| Column | Description |
|---|---|
| `CTY_NAME` | Country name |
| `CON_VAL_MO` | Monthly import value, consumption basis (USD) |
| `CAL_DUT_MO` | Calculated duties collected (USD) |
| `I_COMMODITY` | HS10 commodity code (10 chars, leading zeros preserved) |
| `I_COMMODITY_SDESC` | Commodity short description |
| `time` | Month, `YYYY-MM` |
| `COMM_LVL` | Always `HS10` |
| `CTY_CODE` | Census country code — **absent in `TOTALdata-current.parquet`** |

Tariff rate for a commodity: `τ = CAL_DUT_MO / CON_VAL_MO`

The files carry one row per (HS10, month) — grain and bloc/member overlaps are
already resolved upstream by trade-data, so summing within one file is safe.
Only never mix the bloc files (`0003`, `0020`) or TOTAL with the country files.

---

## Census Bureau API

This repo no longer calls the Census API. All downloading lives in
`../trade-data` (`tradedata/census.py`; key resolved from `CENSUS_API_KEY` or
its untracked `.census-api-key` file). For reference, the base is built from
`https://api.census.gov/data/timeseries/intltrade/imports/hs`.
