# Data Pipeline Reference

Quick reference for updating everything this repo produces when a new month of
Census trade data becomes available.

**Since 2026-08, this repo downloads nothing.** The canonical HS10 dataset
lives in `../trade-data` (imports + exports, 2013-01 → present, 63 entities,
seven-check validation gate). That repo *builds the input files into this one*
in the exact schema the code here reads.

**Since 2026-09, nothing here is computed in a notebook.** Two scripts turn
the input files into every series the paper and the tracker use, in seconds;
the notebooks read those series, check them, and draw. The design and the
verification record are in `REFACTOR-PLAN.md`.

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
   (Never `git add -A` blindly — `ALL-data-current.parquet`, monthly
   snapshots and `data/panel/` are gitignored, but stay explicit anyway.)

### Stage 2 — the measures (seconds; run after every Stage 1)

5. ```powershell
   python scripts/build_panel.py            # ~6 s; no-op if the inputs are unchanged
   python scripts/build_metrics.py          # ~12 s; prints the ALL COUNTRIES numbers for the last month
   python -m pytest tests -q                # the toy-panel and identity checks (~20 s)
   git add data/metrics; git commit -m "Metrics through 2026-07"
   ```
   `build_metrics.py` writes `data/metrics/` (committed) and a manifest with
   the weight mode and the last month. Read the printed **min weight coverage**;
   see "Sanity checks" below.

### Stage 3 — the paper (only when updating the paper)

6. ```powershell
   python scripts/build_paper_inputs.py --target 2026-07
   ```
   writes `paper/results.tex`, `results-sector.tex`, `table.tex`,
   `table-sector.tex`. The comparison month for the `twofour` macros defaults
   to the same month of the weight year (`--comparison` to override).
7. Set `target_date = "2026-07"` in **`TRI-all-country.ipynb`**,
   **`TRI-sector.ipynb`**, **`TRI-composition.ipynb`**; Run All (about 5 s
   each). Their check cells refuse to plot if the metrics manifest is not at
   the target month or was built with a different weight mode. Figures land
   in `paper/figures/`.
8. Paper gotchas:
   - `paper/how-restrictive-us-tradepolicy.tex` hardcodes the histogram-panel
     months only through the notebook (`panel_months` in the panel cell) and
     the title-page date by hand.
   - Check every number quoted in prose against the regenerated macros
     (`paper/weights-change-2026-07.md` lists which sentences carry numbers),
     then rebuild the PDF: `cd paper; latexmk -pdf -f how-restrictive-us-tradepolicy.tex; latexmk -c`.
   - The two bibtex complaints are in uncited entries; `-f` builds through them.

### Stage 4 — the live tracker (can run without Stage 3)

9. **`TRI-tracker-update.ipynb`**: set `target_date = "2026-07"`, Run All
   (~3 s). It needs `data/metrics/country.parquet` from Stage 2 plus the
   statutory CSVs from `../../github/trade-war-redux-2025/` — refresh those
   there first if you want current announced-tariff lines.
10. **Deploy** — the notebook only writes
    `../TRI-tracker/data/tri-all-country-data.parquet` locally:
    ```powershell
    cd C:\heroku\TRI-tracker
    git add data/tri-all-country-data.parquet
    git commit -m "Update tracker data through 2026-07"
    git push origin main
    ```
    The app **deploys via GitHub integration** (confirmed 2026-08-31) — pushing
    `origin main` is the deploy; there is no `heroku` remote. Live app:
    `https://tri-tracker-d17ad5511b2b.herokuapp.com/main-tri-tracker`

### Sanity checks while reviewing any update

- **Revisions look like**: month-specific, sign-flipping deltas confined to
  the revision band (January three calendar years back → present). Expected
  every vintage.
- **A scope error looks like**: a *uniform* shift across countries or months —
  almost always a missing `rp == "-"` grain filter or a bloc summed with its
  members. Stop and investigate; do not ship it.
- **Weight coverage** (`weight_coverage` in every metrics file; the minimum
  is printed by `build_metrics.py`): the share of the 2024 weight base that is
  actually present in the month. ALL COUNTRIES runs 0.95–1.00, dipping each
  January with the HS10 code changes; Russia is the outlier (0.4–0.7). A
  sudden drop elsewhere means a country file lost months upstream.
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
       ▼
[Stage 2] scripts/build_panel.py   ──▶ data/panel/tariff-panel.parquet   (gitignored, ~6 s)
          scripts/build_metrics.py ──▶ data/metrics/*.parquet             (committed, ~12 s)
       │        country, country-top20, sector, sector-shares, enduse, histogram, decomposition
       │
       ├──▶ [Stage 3] scripts/build_paper_inputs.py ──▶ paper/results*.tex, table*.tex
       │              TRI-all-country.ipynb          ──▶ histograms, country panel
       │              TRI-sector.ipynb               ──▶ sector panels
       │              TRI-composition.ipynb          ──▶ end-use panel (not in the paper)
       │
       └──▶ [Stage 4] TRI-tracker-update.ipynb ──▶ ../TRI-tracker/data/tri-all-country-data.parquet
                    (+ external statutory CSVs        (feeds the Heroku Bokeh app)
                     from ../../github/
                     trade-war-redux-2025/)
```

---

## The `tri/` package

One definition of everything the measures depend on:

| module | what it holds |
|---|---|
| `tri/config.py` | paths, the 30- and 20-country lists, weight year and mode, sector exclusions, histogram bins, policy-event dates |
| `tri/load.py` | `load_entity` (one source file, typed), `load_panel` |
| `tri/weights.py` | `weight_table`: import value per (country, HS10) over the weight period — `annual` (default) or `january` (reproduces the pre-2026-09 notebooks; tests only) |
| `tri/metrics.py` | `country_metrics`, `sector_metrics`, `enduse_metrics`, `histogram_shares`, `sector_shares`; the formulas are in the module docstring |
| `tri/tex.py` | the macro and table writers |
| `tri/plot.py` | policy-event lines, histogram drawing, house style |
| `tri/hs2_names.py` | HS2 chapter names for the sector table |

The measures, for goods *g* in a grouping with weights *w* and month-*t*
tariffs τ = duties / value:

| Measure | Formula | Column |
|---|---|---|
| TRI | $\sqrt{\sum w_g \tau_g^2 / \sum w_g}$ | `sqrtariff` |
| Mean weighted | $\sum w_g \tau_g / \sum w_g$ | `meanweighted` |
| Duties / imports | $\sum \text{duties}_g / \sum \text{value}_g$ | `simplemean` |

Weights are import values over calendar 2024 (`config.WEIGHT_YEAR`) and are
normalised within whatever is being measured — a country, a sector, an end-use
category, or all 30 countries. The denominator runs over every good that had
weight in 2024 (`config.RENORMALIZE_DEFAULT = "universe"`; a good absent in
month *t* counts as tariff-free); `--renormalize present` divides by the
present goods instead. `weight_coverage` is the ratio of the two.

**Tests:** `tests/test_reproduce.py` is the refactor gate — in `january`
weight mode the scripts must reproduce `tests/baseline-2026-07/` (the notebook
pipeline's last outputs, tag `pre-refactor-2026-07`) to 1e-12, and the four
`.tex` fragments line for line. `tests/test_metrics.py` checks the formulas on
a toy panel and the identity TRI²(all) = Σ share × TRI²(country) on real data.

---

## Notebooks

All four notebooks **read `data/metrics/` and nothing else**. Each has a
config cell with `target_date` and `expected_weights`, and a check cell that
asserts the metrics manifest matches, every month is present, and no measure
is NaN. If a check fails, rerun Stage 2.

| notebook | reads | draws / writes |
|---|---|---|
| `TRI-all-country.ipynb` | `country.parquet`, `histogram.parquet` | `{month}-histogram`, `panel-histograms`, `mexico-`/`china-tariffs`, `panel-tariffs`; Canada/Mexico plot-data CSVs |
| `TRI-sector.ipynb` | `sector.parquet`, `sector-shares.parquet` | `hs61-tariffs`, `panel-top-sector-tariffs` |
| `TRI-composition.ipynb` | `enduse.parquet` | end-use panel (savefig commented out; not in the paper) |
| `TRI-tracker-update.ipynb` | `country.parquet` + statutory CSVs from `../../github/trade-war-redux-2025/` | `../TRI-tracker/data/tri-all-country-data.parquet` |

**Retired** (kept for history; superseded):

- `make-imports-hs10-dataset.ipynb` and
  `make-imports-hs10-dataset-current-month.ipynb` — the old Census pulls
  (2026-08-31). Do not run them; they would overwrite verified files with an
  unverified pull.
- The computation cells of the four notebooks above (2026-09-08): see the tag
  `pre-refactor-2026-07` for the last version that computed in-notebook.
- `data/imports-hs10/{CTY_CODE}data-{YYYY-MM}.parquet` monthly snapshots and
  `data/imports-hs10/ALL-data-current.parquet` (untracked, gitignored, deletable).

---

## Data Files Reference

| File | Description | Produced by |
|---|---|---|
| `data/imports-hs10/{CTY_CODE}data-current.parquet` | Full monthly time series per country | Stage 1 (`../trade-data` notebook 04) |
| `data/imports-hs10/TOTALdata-current.parquet` | Census's published all-country total | Stage 1 (`../trade-data` notebook 04) |
| `data/panel/tariff-panel.parquet` | one row per (entity, HS10, month) from 2024-01, typed; gitignored | `scripts/build_panel.py` |
| `data/metrics/country.parquet` | month × country (30) + ALL COUNTRIES, from 2024-01 | `scripts/build_metrics.py` |
| `data/metrics/country-top20.parquet` | month × country (20) + their aggregate — the paper's table | `scripts/build_metrics.py` |
| `data/metrics/sector.parquet` | month × HS2 (top 20 chapters), over the 20 partners, from 2025-01 | `scripts/build_metrics.py` |
| `data/metrics/sector-shares.parquet` | HS2 chapters ranked by 2024 value, with share of all imports | `scripts/build_metrics.py` |
| `data/metrics/enduse.parquet` | month × BEC end use (CONS/CAP/INT), over the 20 partners | `scripts/build_metrics.py` |
| `data/metrics/histogram.parquet` | month × tariff bin → share of import value (the 30) | `scripts/build_metrics.py` |
| `data/metrics/decomposition.parquet` | month × country: TRI², mean², variance, variance share, TRI/mean | `scripts/build_metrics.py` |
| `data/metrics/metrics-manifest.json` | weight mode, renormalisation, last month, row counts, min coverage | `scripts/build_metrics.py` |
| `paper/results.tex`, `results-sector.tex`, `table.tex`, `table-sector.tex` | the paper's generated pieces | `scripts/build_paper_inputs.py` |
| `../TRI-tracker/data/tri-all-country-data.parquet` | Daily tariff series feeding the Heroku app | Stage 4 |
| `../../github/trade-war-redux-2025/country-by-time.csv` | Per-country statutory tariffs (external repo) | Stage 4 input |
| `../../github/trade-war-redux-2025/daily-tariff-latest-data.csv` | Daily ALL-COUNTRIES statutory tariff (external repo) | Stage 4 input |
| `data/hs6-enduse.parquet` | BEA end-use classification (HS6 → CONS/CAP/INT) | static |
| `data/country-list.csv` | The 30 country codes for the main analysis | static (pinned; mirrored as `FROZEN_COUNTRY_CODES` in `../trade-data/config.py`) |
| `data/country-list-20.csv` | Top 20 trading partners (table, sectors, end use) | static |
| `tests/baseline-2026-07/` | the notebook pipeline's last outputs; reproduction target | frozen 2026-09-08 |

---

## Parquet Schema (`*data-current.parquet`)

All columns are **strings** (the loader casts values with `.astype(float)`),
in this order:

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
