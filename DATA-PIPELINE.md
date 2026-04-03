# Data Pipeline Reference

Quick reference for running and updating the data pipeline.

---

## Monthly Update Checklist

When new Census data is available for a given month (e.g., `2026-02`):

1. **Open** `make-imports-hs10-dataset-current-month.ipynb`
2. **Update** the `date` variable to the new month: `date = "2026-02"`
3. **Run all cells** — downloads the new month, appends to `*data-current.parquet`, rebuilds `ALL-data-current.parquet`
4. **Open** `TRI-all-country.ipynb` and update `target_date = "2026-02"`
5. **Run all cells** — regenerates `results.tex`, figures, `top-country-metrics.parquet`
6. Repeat for `TRI-sector.ipynb` and `TRI-composition.ipynb` if sector/end-use outputs are needed

---

## Pipeline Stages

```
Census Bureau API
       │
       ▼
[Stage 1a] make-imports-hs10-dataset.ipynb        ← Run ONCE (full history 2013–present)
       │
       ▼
data/imports-hs10/*data-current.parquet           ← One parquet file per country
       │
[Stage 1b] make-imports-hs10-dataset-current-month.ipynb   ← Run MONTHLY to append new data
       │                └── also produces ALL-data-current.parquet
       │
       ├──▶ [Stage 2a] TRI-all-country.ipynb   ──▶ top-country-metrics.parquet
       │                                             results.tex (LaTeX macros)
       │                                             histogram + time-series figures
       │
       ├──▶ [Stage 2b] TRI-sector.ipynb        ──▶ top-sector-metrics.parquet
       │                                             table-sector.tex
       │                                             panel sector figures
       │
       └──▶ [Stage 2c] TRI-composition.ipynb   ──▶ enduse-metrics.parquet
                                                     panel-enduse-tariffs.png/.pdf
```

---

## Notebooks

### Stage 1a — `make-imports-hs10-dataset.ipynb` (run once)

Downloads the full historical dataset from the Census HS API (2013–present).

- Identifies top 31 trading partners by total import value
- Explicitly adds Canada (`0003`) and Mexico (`0020`)
- For each country, fetches monthly HS10 data: `CON_VAL_MO`, `CAL_DUT_MO`, `I_COMMODITY`
- Skips files that already exist (idempotent / safe to re-run)
- Outputs: `data/imports-hs10/{CTY_CODE}data-current.parquet` for ~33 countries + `TOTALdata-current.parquet`

### Stage 1b — `make-imports-hs10-dataset-current-month.ipynb` (run monthly)

Incremental updater — downloads one new month and appends it.

**Variable to update each month:**
```python
date = "2026-02"   # ← change this
```

Steps:
1. Downloads HS10 data for the single target month
2. Saves snapshot as `{CTY_CODE}data-{YYYY-MM}.parquet`
3. Appends snapshot onto existing `*data-current.parquet` for every country
4. Rebuilds `ALL-data-current.parquet` (concatenation of all per-country current files)

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

---

## Data Files Reference

| File | Description | Produced by |
|---|---|---|
| `data/imports-hs10/{CTY_CODE}data-current.parquet` | Full monthly time series per country | Stage 1a/1b |
| `data/imports-hs10/{CTY_CODE}data-{YYYY-MM}.parquet` | Single-month snapshot per country | Stage 1b |
| `data/imports-hs10/TOTALdata-current.parquet` | Aggregate across all countries | Stage 1a/1b |
| `data/imports-hs10/ALL-data-current.parquet` | All countries concatenated | Stage 1b |
| `data/top-country-metrics.parquet` | TRI time series by country | Stage 2a |
| `data/top-sector-metrics.parquet` | TRI time series by HS2 sector | Stage 2b |
| `data/enduse-metrics.parquet` | TRI time series by end-use category | Stage 2c |
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
