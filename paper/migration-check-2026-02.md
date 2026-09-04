# Paper-side migration check: retired pipeline vs canonical trade-data, at 2026-02

**Date:** 2026-09-04. **Verdict: clean refresh — the paper can move to the
canonical data without qualification.**

## What was compared

The three paper notebooks (`TRI-all-country`, `TRI-sector`, `TRI-composition`)
were run twice at the same target month, `target_date = "2026-02"`:

| run | data under `data/imports-hs10/` | vintage | where |
|---|---|---|---|
| baseline | retired Census-pull notebooks | 2026-02 release (run 2026-04-02) | commit `85dbbb0` |
| canonical | `../trade-data` notebook 04 build | 2026-07 release (built 2026-08-31) | this commit |

Same notebooks, same month, same 2024 weights. The two runs differ in the
data source *and* in the Census vintage — the 2026-07 release carries the
annual revision of calendar 2025 that the April baseline predates — so the
expected signature is the one from the data migration: revision-band months
move a little with flipping signs, everything else is identical.

## Results

**Paper macros — identical.** All 19 `results.tex` values and all 12
`results-sector.tex` values are unchanged. Every number quoted in the paper's
prose for February 2026 and February 2024 survives the switch as-is.

**Tables — three and six cells move by 0.1 pp.**
`table.tex`: China TRI 33.0→32.9, Brazil mean-weighted 14.7→14.6, UK TRI
8.7→8.6. `table-sector.tex`: HS 73 mean-weighted 37.2→37.3, HS 72 TRI
38.8→38.7, HS 40 TRI 22.8→22.9, HS 84 TRI 17.6→17.5, HS 29 share 1.7→1.8,
HS 30 share 6.7→6.6. Rounding-edge effects of the revisions below.

**Metric time series — all movement inside calendar 2025, sign-flipping.**
Max absolute change in percentage points, by file:

| file | TRI | mean weighted | duties/imports | months that move > 0.05 pp |
|---|---|---|---|---|
| `top-sector-metrics.parquet` | 1.34 | 2.90 | 2.86 | 2025-01 … 2025-12 only |
| `enduse-metrics.parquet` | 0.62 | 1.08 | 1.17 | 2025-03 … 2025-12 only |
| `canada_tariff_plot_data_2026-02.csv` | 1.88 | 1.40 | 1.44 | 2025-03 … 2025-10 only |
| `mexico_tariff_plot_data_2026-02.csv` | 0.80 | 0.76 | 0.70 | 2025-03 … 2025-10 only |

The largest movers are Vehicles (HS 87) in 2025-04..06 (+0.9 to +2.9 pp) and
2025-07..11 (−0.7 to −2.1 pp), and consumer goods in the same months — the
sectors and months where the Section 232 auto tariffs landed and where Census
revised 2025 most. January–December 2024 and January–February 2026 do not
move (< 0.05 pp everywhere). A source-scope error would show as a uniform
shift across months or entities; there is none.

**`top-country-metrics.parquet` — canonical vs canonical, exact.** HEAD holds
the TRI-tracker's run of the same code on the same canonical files through
2026-07; the 2026-02 run reproduces every overlapping month to the digit
(max |Δ| = 0.000 pp). The notebook pipeline is deterministic on this data.
The HEAD file was kept (it is the superset).

## Things the run surfaced (fix in Phase 2, before the 2026-07 regeneration)

- `TRI-sector.ipynb` **appends** to `results-sector.tex` rather than
  rewriting it: the run produced the 12 macros twice. Duplicate
  `\newcommand`s would fail the LaTeX build. Restored to the baseline copy
  here (the values were identical). The `open(texfile, 'w')` in cell 13 is
  commented out, leaving only the `'a'` in cell 18.
- `TRI-sector.ipynb` cell 16 saves a knitted-apparel (HS 61) time-series plot
  over `figures/canada-tariffs.png/.pdf`. The paper does not include that
  figure, so nothing is wrong in the PDF, but the file in `figures/` is not
  what its name says.
- `table.tex` is captioned "Tariff Metrics by Sector"; it is the country
  table.
- Run times on this machine, kernel cwd = repo root: all-country 14 min,
  composition 28 min, sector 109 min (the three run concurrently; sector
  loops 20 countries × 14 months × HS2 groups).
