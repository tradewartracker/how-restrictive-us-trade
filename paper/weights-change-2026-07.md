# What moved when the weights became calendar-2024 (2026-09-08)

The paper describes the import-share weights as the annual value of imports in
2024. The notebooks that produced every vintage through July 2026 used
**January 2024 only** (a datetime column compared with the string `"2024"`
matches 2024-01-01). The refactored pipeline (`tri/`, `scripts/`) first
reproduced the January numbers exactly (`tests/test_reproduce.py`), then the
default was switched to annual weights (commit `ccf4ca9`). This note records
the difference, with everything else held fixed.

Two things change under annual weights: the *shares* are the year's product
mix rather than January's, and the *universe* of goods grows from those
imported in January 2024 to those imported at any point in 2024 (Canada: 7,851
→ 12,202 HS10 lines).

## Headline macros (percent, rounded as in the paper)

| macro | January weights | annual weights |
|---|---|---|
| TRI, July 2026 | 15 | 14 |
| mean weighted, July 2026 | 8 | 8 |
| duties / imports, July 2026 | 6 | 6 |
| TRI minus mean weighted | 7 | 6 |
| TRI minus duties / imports | 9 | 8 |
| TRI, July 2024 | 7 | 7 |
| mean weighted, July 2024 | 3 | 2 |
| TRI at the peak, October 2025 | 23 | 22 |
| TRI, February 2026 (eve of the ruling) | 18 | 17 |
| China TRI, July 2026 | 26 | 25 |
| Canada / Mexico TRI | 11 / 9 | 11 / 9 |
| Machinery TRI | 13 | 12 |

Unrounded, ALL COUNTRIES July 2026: TRI 14.82 → 14.34, mean weighted 8.30 →
7.97, duties / imports 6.31 → 6.29. The whole time series shifts down by
0.3–0.6 pp on the TRI; nothing in its shape changes.

## Countries, July 2026 TRI (percent)

Largest moves: Saudi Arabia 3.6 → 5.3, Vietnam 16.3 → 15.3, Austria 16.5 →
15.0, Taiwan 13.3 → 12.2, India 13.4 → 14.4, Netherlands 10.2 → 10.9,
Colombia 6.6 → 7.3. Canada 11.1 → 10.8, Mexico 9.1 → 8.8, China 26.1 → 25.3.
The table's ordering changes in a few adjacent places (Korea above Brazil,
India above Japan, Germany level with Japan).

## Sectors, July 2026 TRI (percent)

Machinery 12.9 → 12.0, Electrical Equipment 12.0 → 11.8, Vehicles 15.1 →
14.9, Pharmaceuticals 0.9 → 1.0; Furniture 20.9 → 19.6; the metals chapters
within 0.6 pp. The "four sectors ≈ 50 % of imports" statement is unchanged
(the shares come from the TOTAL file and were already annual).

## Prose that this touches

- The abstract's "twice as restrictive": 14 vs 6 and 8. Still holds.
- "TRI currently stands at 15 percent" reads 14 now, through the macro.
- Every figure is regenerated; the histogram panel's title numbers move
  by the amounts above.
- Nothing about the March 2026 step, the Canada/Mexico contrast, or the
  sector ranking changes qualitatively.

## Weight coverage under annual weights

`weight_coverage` = weight of goods present in the month / weight of every
good in the 2024 universe. ALL COUNTRIES: 0.95–1.00 (min 0.949 in January
2026; each January dips because of the annual HS10 code changes). Most
countries sit at 0.9–1.0 in July 2026; Russia is the outlier at 0.43–0.68
(its 2024 trade was already thin and shrank further). Sectors 0.69–1.00,
end-use categories ≥ 0.94.

## Open decision: renormalise over present goods (REFACTOR-PLAN.md §6.1)

Computed with `--renormalize present` and nothing else changed, July 2026:
ALL COUNTRIES TRI 14.34 → 14.55, mean 7.97 → 8.21; at the peak 22.42 →
22.58; February 2026 17.48 → 17.85. By country the difference is ≤ 0.6 pp
except Russia (7.4 → 8.9); by sector ≤ 1.9 pp (Aluminum 44.1 → 46.0, where
coverage is 0.9). The choice is immaterial for the paper's text and matters
only for the low-coverage entities; `present` is the cleaner definition, and
the annual January dips would stop leaking into the series.
