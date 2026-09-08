# Refactor plan: scripts that compute, notebooks that plot

**Status:** plan agreed 2026-09-08; not started.
**Goal:** the paper's numbers come from a fast, tested, single-definition
pipeline; the notebooks only read, check, and draw. A monthly update becomes a
few commands and the figure-tweak loop is seconds, not an hour.

---

## 1. Why

Measured on the canonical data (2026-07 vintage, this machine):

| notebook | run time | what it spends the time on |
|---|---|---|
| TRI-all-country | 18 min | reloads all 30 country files for every month (and 4 more times for the histogram panel) |
| TRI-composition | 37 min | same, for 20 countries × 19 months × 3 end-use groups |
| TRI-sector | 82–109 min | same, for 20 countries × 19 months × 10 HS2 groups |

Every load re-reads a 1.5M-row all-string parquet, casts two columns to float,
parses dates, and recomputes weights. The arithmetic itself is trivial. The same
four functions are copy-pasted into four notebooks (including the tracker) and
have already drifted in small ways.

## 2. Two things the current code does that the paper does not say

Found while reading the code for this plan. Both must be **reproduced first**
(so the refactor is verifiable) and then **fixed deliberately** (so the change
in the numbers is attributable to the fix, not to the refactor).

1. **Weights are January-2024, not calendar-2024.** `make_good_country_year`
   filters `dfcntry['time'] == "2024"`; `time` is a datetime, so pandas compares
   with `Timestamp("2024-01-01")` and keeps only January. Consequences:
   - the import-share weights are January's product mix;
   - the *universe of goods* is what was imported in January 2024 (Canada:
     7,851 HS10 lines vs 12,202 over the year); goods absent in January get no
     weight in any month's TRI, mean, or duties/imports;
   - the paper (Section 3, "the annual value of imports for a good ... in the
     year 2024") describes something else.
   The fix is `time.dt.year == 2024`. Expect every number to move a little.
2. **The country table's "All Countries" row is the top-20 aggregate**, the
   prose macro is the 30-country aggregate (`table.tex` 15.1 vs
   `results.tex` 15 for 2026-07). Decide which the table should show.

Other behaviours to carry over knowingly (see the quirk register in §6):
left-merge of weights onto the target month (goods missing in the target month
contribute nothing to the sums but keep their weight in the denominator; goods
new since the weight period are dropped); rows with `CON_VAL_MO == 0` yield
NaN tariffs and are silently skipped; per-country measures renormalise weights
within the country; sector measures normalise within sector across the
top-20 countries only.

## 3. Target layout

```
tri/                          ← one importable package (like ../trade-data/tradedata)
  __init__.py
  config.py                   ← paths, country lists, HS2 exclusions, policy dates, weight year
  load.py                     ← read one country file once: cast, parse time, add HS2/HS6, tariff
  weights.py                  ← weight table for a weight period (annual; "january" mode for reproduction)
  metrics.py                  ← the three measures for any grouping (country, HS2, end-use, all)
  histogram.py                ← bin shares per month
  tex.py                      ← macro and table writers (one place, one naming scheme)
scripts/
  build_panel.py              ← Stage 2a: 31 files → data/panel/tariff-panel.parquet (once per vintage)
  build_metrics.py            ← Stage 2b: panel → data/metrics/*.parquet (seconds)
  build_paper_inputs.py       ← Stage 2c: metrics → paper/results*.tex, table*.tex (no plots)
tests/
  test_reproduce.py           ← the gate (§5)
  test_metrics.py             ← unit checks on small synthetic panels
notebooks (existing names kept):
  TRI-all-country.ipynb       ← read data/metrics, assert, plot; ~1 min
  TRI-sector.ipynb
  TRI-composition.ipynb
  TRI-tracker-update.ipynb    ← reads data/metrics/country.parquet instead of recomputing
```

### The panel (data/panel/tariff-panel.parquet)

One row per (country, HS10, month), 2024-01 → present, ~9M rows, parquet with
proper dtypes:

| column | type | note |
|---|---|---|
| `CTY_CODE`, `CTY_NAME` | category | 31 entities (30 countries + TOTAL kept separately) |
| `I_COMMODITY` | string | 10 chars; `HS2`, `HS6` derived |
| `time` | period[M] or datetime | month |
| `CON_VAL_MO`, `CAL_DUT_MO` | float64 | |
| `tariff` | float64 | duties / value; NaN where value is 0 |

Built by reading each file once with `pyarrow`, selecting columns, filtering
`time >= 2024-01`, casting. Parallel across files with a process pool (I/O and
casting dominate; ~31 files, expect 1–2 min total). Rebuilt only when
`data/imports-hs10` changes; the script records the input files' mtimes and
sizes in a small manifest and is a no-op when nothing changed.

### The weights

`weights.py` produces `(CTY_CODE, I_COMMODITY, weight)` for a weight period.
Two modes: `annual=2024` (the fix) and `january=2024` (exact reproduction of
today's behaviour). Weights are stored unnormalised (import value); every
metric normalises over its own grouping, which is what the notebooks do today
via renormalisation.

### The metrics (data/metrics/)

All computed from the panel with one merge and grouped sums — no loops over
months, no reloads:

| file | grouping | consumers |
|---|---|---|
| `country.parquet` | month × country, plus `ALL COUNTRIES` over the 30 | all-country notebook, tracker, `table.tex` |
| `country-top20.parquet` | same over the top-20 list (for the table row if kept) | all-country notebook |
| `sector.parquet` | month × HS2 (top 10 by 2024 value, excl. 27/71/98/99), over top-20 countries | sector notebook |
| `enduse.parquet` | month × BEC end-use (CONS/CAP/INT), over top-20 countries | composition notebook |
| `histogram.parquet` | month × tariff bin → share of import value | histogram figures/panel |
| `decomposition.parquet` | month × country: TRI², mean², V, V share, TRI/mean | optional table (the IEEPA discussion) |

Columns everywhere: `date, <group>, sqrtariff, meanweighted, simplemean,
duty_total, import_total, n_goods, weight_coverage` — the last is the share of
weight actually present in that month, which makes the left-merge behaviour
visible instead of silent.

### The notebooks

Each becomes: read the metrics parquets → a checks cell (expected months,
no NaN in the plotted series, coverage above a floor, the all-country TRI
equals the histogram-panel TRI for the same month) → plots → done. Macros and
tables are written by `build_paper_inputs.py`, not by plotting cells, so
`results.tex` cannot end up half-written by a partial notebook run.

## 4. Steps

1. **Freeze the baseline.** Tag the current commit. Copy today's
   `top-country-metrics.parquet`, `top-sector-metrics.parquet`,
   `enduse-metrics.parquet`, `results*.tex`, `table*.tex` into
   `tests/baseline-2026-07/`. These are the reproduction targets.
2. **Package skeleton + loader + panel build.** `tri/load.py`,
   `scripts/build_panel.py`, manifest, process pool. Check: row counts per
   country-month equal the source files after the 2024-01 filter.
3. **Weights + metrics in "january" mode.** Reproduce `country.parquet`.
   Gate: `test_reproduce.py` passes at 1e-12 on every cell of the baseline
   country file (we already know the notebook is deterministic: two runs
   matched to the digit).
4. **Sector and end-use.** Reproduce the other two baseline parquets the same
   way. The sector list and the top-20 share column come from the same panel
   (TOTAL file for the 2024 shares, as today).
5. **Histogram shares + tex writers.** `build_paper_inputs.py` regenerates
   `results.tex`, `results-sector.tex`, `table.tex`, `table-sector.tex`
   byte-identical to the baseline (modulo the table caption fix already made).
6. **Notebooks rewritten** to read metrics only. Figures compared by eye to
   the committed PNGs; the plotting code is moved, not rewritten.
7. **Tracker** reads `data/metrics/country.parquet`; the daily
   interpolation and statutory merge stay in the tracker notebook.
8. **Switch on the fixes** (§2) as separate commits: annual weights, then the
   table's all-countries row. Regenerate, record what moved in a short note
   next to this file, update the paper's data section if needed.
9. **Docs.** Rewrite DATA-PIPELINE Stage 2 around the scripts; retire the old
   function cells; add the two commands to the trade-data runbook.

## 5. The gate

`python -m pytest tests/test_reproduce.py` compares, cell by cell, the
scripts' output in `january` mode against `tests/baseline-2026-07/`.
Tolerance 1e-12 relative. Nothing in steps 2–7 may be merged while it fails.
Step 8 is the only place the numbers are allowed to change, and the diff is
the deliverable of that step.

## 6. Quirk register (reproduce, then decide)

Decisions taken 2026-09-08 are marked **decided**.

| # | behaviour today | reproduce? | then |
|---|---|---|---|
| Q1 | weight period is January 2024 | yes (`january` mode) | **decided: switch to annual 2024** (§2.1) |
| Q2 | goods universe = goods with weight; new goods dropped, vanished goods keep weight in the denominator (i.e. are treated as tariff-free) | yes | report `weight_coverage` first; recommendation is to renormalise over goods present in the month (see §6.1) — decide once coverage is measured on annual weights |
| Q3 | `CON_VAL_MO == 0` → NaN tariff, silently skipped | yes | keep; count them in `n_goods` diagnostics |
| Q4 | country table all-countries row = top-20 aggregate | yes (`country-top20.parquet`) | **decided: leave the table as is; the prose will say which aggregate it is** |
| Q5 | country and sector measures renormalise weights within the country / within the sector (sector over the top-20 countries) | yes | **decided: keep — this is the intended definition** (§6.1) |
| Q6 | sector universe excludes HS2 27, 71, 98, 99; ranked by 2024 value from the TOTAL file (true annual) | yes | keep |
| Q7 | histogram bins `linspace(-0.01, 50, 11)`; mass above 50 not drawn | yes | keep; add the >50 share as a number in the panel title if wanted |
| Q8 | `results-sector.tex` appended by a loop (fixed 2026-09-04) | n/a | writers own the whole file |

### 6.1 The two renormalisations, kept apart

**Within a grouping (Q5) — keep.** A country TRI answers "what uniform tariff
on imports *from Canada* has the same deadweight loss as the actual tariffs on
Canada", so the weights are Canada's own import shares; likewise within a
sector. This is what the paper says and what the code does. It also gives a
free consistency test: with common weights the aggregate obeys
`TRI_all² = Σ_c s_c · TRI_c²` exactly, where `s_c` is country c's share of the
weight base — `test_metrics.py` should assert it.

**Over goods present in the month (Q2) — recommended, decide after measuring.**
Today a good that has 2024 weight but no imports in the target month drops out
of the numerator and stays in the denominator, so it is scored as a zero
tariff. That pulls the TRI and the mean down in proportion to the missing
weight, and it interacts with the annual HS10 code revisions: codes retired
after 2024 are permanently "zero tariff", codes introduced after 2024 are
permanently excluded (left merge). Renormalising over present goods scores a
missing good as "like the average present good" instead, which is the neutral
assumption and keeps every month on the same footing regardless of coverage.
Duties / imports is unaffected either way (it only ever uses present goods).
With January weights the missing mass was large (a third of Canada's annual
HS10 lines had no weight at all); with annual weights it should be small, and
`weight_coverage` by month will say how small. If coverage is above ~97 %
everywhere the choice barely matters and renormalising is simply cleaner; if
it is not, the HS10 code-change concordance becomes the real fix and is a
separate task.

## 7. Expected run times after

| step | now | after |
|---|---|---|
| panel build (once per vintage) | — | ~1–2 min |
| all metrics | ~2.5 h across three notebooks | seconds |
| paper inputs (tex) | inside notebooks | < 1 s |
| three plotting notebooks | ~2.5 h | ~1 min |
| histogram-panel restyle | 20 min | seconds |

## 8. Out of scope

The IEEPA decomposition table and any prose changes; the tracker's daily
interpolation logic; moving the panel build into `../trade-data` (possible
later as a product, but the TRI-specific choices — weight year, universe,
exclusions — belong here).
