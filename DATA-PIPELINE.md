# Data Pipeline Reference

Quick reference for running and updating the data pipeline.

---

## Monthly Update Checklist

> **Since 2026-08 the input data comes from the canonical `../trade-data` repo.**
> The old Stage 1a/1b Census-download notebooks in this repo are retired — the
> per-country parquets are now **built into this repo** by trade-data's
> `notebooks/04-build-tri-country-product.ipynb`, which verifies each file
> against the previous vintage before writing (see trade-data's README/STATUS).

When new Census data is available for a given month (e.g., `2026-07`):

1. **In `../trade-data`**: `python scripts/build_history.py --end 2026-07`
   (idempotent; the exit code is the verdict)
2. **In `../trade-data`**: run `notebooks/04-build-tri-country-product.ipynb` —
   rebuilds the 33 files in `data/imports-hs10/` here (30 countries + EU +
   USMCA + TOTAL), gated so only appended months and revision-band changes pass
3. **Commit this repo** — the refreshed parquets are the data update
4. **Open** `TRI-all-country.ipynb` and update `target_date = "2026-07"`
5. **Run all cells** — regenerates `results.tex`, figures, `top-country-metrics.parquet`
6. Repeat for `TRI-sector.ipynb` and `TRI-composition.ipynb` if sector/end-use outputs are needed

### To update ONLY the Heroku tracker site

If you just need to refresh the live tracker (not the paper outputs), you can skip Stage 2a–2c and run **only** the tracker notebook — see [Stage 3](#stage-3--tri-tracker-updateipynb-heroku-tracker) below.

1. Make sure Stage 1b has been run for the target month (so `*data-current.parquet` contains it)
2. **Open** `TRI-tracker-update.ipynb`, set `target_date = "2026-02"`, **Run all cells**
3. **Deploy**: in the separate `../TRI-tracker` repo, commit the regenerated parquet and `git push heroku main`

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
data/imports-hs10/*data-current.parquet           ← One parquet file per country (33 files)
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

### Stage 1 — the `../trade-data` repo (replaces the retired 1a/1b notebooks)

The canonical HS10 base: imports **and** exports, 2013-01 → present, 63
entities, downloaded once and validated by a seven-check gate (duplicates,
vintage, completeness, coverage, entity kind, grain reconciliation, frozen
countries). See `../trade-data/README.md` for the two reading rules and
`STATUS.md` there for the verification record.

Monthly: `python scripts/build_history.py --end YYYY-MM` there, then its
`notebooks/04-build-tri-country-product.ipynb`, which writes the 33 files into
`data/imports-hs10/` here in the exact legacy schema — all-string columns,
`time` as `YYYY-MM`, TOTAL without `CTY_CODE` — verified against the previous
vintage before every write. The entity files: the 30 countries in
`country-list.csv`, plus the EU (`0003`) and USMCA (`0020`) **blocs** (these
contain their own member countries — never sum them with individual countries;
Canada is `1220`, Mexico is `2010`), plus `TOTALdata-current.parquet`.

**Retired with the old notebooks** (kept in git history):

- `make-imports-hs10-dataset.ipynb` and
  `make-imports-hs10-dataset-current-month.ipynb` — the separate Census pulls,
  including the blind-append bug (re-running a month appended it twice)
- `data/imports-hs10/{CTY_CODE}data-{YYYY-MM}.parquet` monthly snapshots
  (untracked, gitignored; safe to delete)
- `data/imports-hs10/ALL-data-current.parquet` — no notebook here reads it, and
  `trade-miner` now reads trade-data's own ALL files directly (untracked,
  gitignored; safe to delete)

### Stage 2a — `TRI-all-country.ipynb`

Computes the three tariff measures by country over time.

**Variable to update each month:**
```python
target_date = "2026-02"   # ← change this
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

Standalone updater for the **live Heroku tracker site** — run this when you only need to
refresh the interactive app, without regenerating any paper results (Stage 2a–2c).

Reads the `*data-current.parquet` files (so Stage 1b must already include the target month)
and recomputes the three country tariff measures as a daily time series.

**Variable to update each month:**
```python
target_date = "2026-02"   # ← change this
```

**External dependency — pulled in from a *different* repo:** the notebook also reads statutory
tariff data from `../../github/trade-war-redux-2025/` (outside this repo):

| File | Used for |
|---|---|
| `country-by-time.csv` | Per-country announced/statutory effective tariff |
| `daily-tariff-latest-data.csv` | Daily import-weighted "ALL COUNTRIES" statutory tariff |

Refresh those CSVs in the `trade-war-redux-2025` repo first if you want current statutory numbers.

**Output:** writes directly into the separate tracker repo at
`../TRI-tracker/data/tri-all-country-data.parquet` (also rewrites `data/top-country-metrics.parquet`).

**Deploy to Heroku:** the notebook only writes the parquet locally — it does **not** deploy.
The `../TRI-tracker` repo is its own git repo with its own Heroku remote. To push live:
```bash
cd ../TRI-tracker
git add data/tri-all-country-data.parquet
git commit -m "Update tracker data through 2026-02"
git push heroku main
```
Live app: `https://tri-tracker-d17ad5511b2b.herokuapp.com/main-tri-tracker`

---

## Data Files Reference

| File | Description | Produced by |
|---|---|---|
| `data/imports-hs10/{CTY_CODE}data-current.parquet` | Full monthly time series per country | Stage 1 (`../trade-data` notebook 04) |
| `data/imports-hs10/TOTALdata-current.parquet` | Census's published all-country total | Stage 1 (`../trade-data` notebook 04) |
| `data/imports-hs10/{CTY_CODE}data-{YYYY-MM}.parquet` | *(retired)* single-month snapshots | old Stage 1b — gitignored, deletable |
| `data/imports-hs10/ALL-data-current.parquet` | *(retired)* concatenation, read by nothing | old Stage 1b — gitignored, deletable |
| `data/top-country-metrics.parquet` | TRI time series by country | Stage 2a |
| `data/top-sector-metrics.parquet` | TRI time series by HS2 sector | Stage 2b |
| `data/enduse-metrics.parquet` | TRI time series by end-use category | Stage 2c |
| `../TRI-tracker/data/tri-all-country-data.parquet` | Daily tariff series feeding the Heroku app | Stage 3 |
| `../../github/trade-war-redux-2025/country-by-time.csv` | Per-country statutory tariffs (external repo) | Stage 3 input |
| `../../github/trade-war-redux-2025/daily-tariff-latest-data.csv` | Daily ALL-COUNTRIES statutory tariff (external repo) | Stage 3 input |
| `data/hs6-enduse.parquet` | BEA end-use classification (HS6 → CONS/CAP/INT) | static |
| `data/country-list.csv` | ~33 country codes for main analysis | static |
| `data/country-list-20.csv` | Top 20 trading partners (sector/composition) | static |

---

## Parquet Schema (`*data-current.parquet`)

| Column | Description |
|---|---|
| `CTY_NAME` | Country name |
| `I_COMMODITY` | HS10 commodity code |
| `I_COMMODITY_SDESC` | Commodity short description |
| `CON_VAL_MO` | Monthly import value (USD) |
| `CAL_DUT_MO` | Calculated duties collected (USD) |
| `time` | Month (YYYY-MM) |

Tariff rate for a commodity: `τ = CAL_DUT_MO / CON_VAL_MO`

---

## Census Bureau API

- **Base URL:** `https://api.census.gov/data/timeseries/intltrade/imports/hs`
- **Key fields:** `CTY_CODE`, `CTY_NAME`, `CON_VAL_MO`, `CAL_DUT_MO`, `I_COMMODITY`, `I_COMMODITY_SDESC`
- The notebooks use a public API key — for heavy usage get your own at https://api.census.gov/data/key_signup.html
