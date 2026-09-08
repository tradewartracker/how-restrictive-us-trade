"""Stage 2b: every series the paper and the tracker use, from the panel.

    python scripts/build_metrics.py [--weights annual|january]

Writes to data/metrics/:

  country.parquet        month x country (the 30) + ALL COUNTRIES, from 2024-01
  country-top20.parquet  month x country (the 20) + ALL COUNTRIES over the 20   (the paper's table)
  sector.parquet         month x HS2 (top 20 chapters by 2024 value), over the 20, from 2025-01
  sector-shares.parquet  HS2 chapters ranked by 2024 import value, with share of all imports
  enduse.parquet         month x BEC end use (CONS/CAP/INT), over the 20, from 2025-01
  histogram.parquet      month x tariff bin: share of import value (the 30)
  decomposition.parquet  month x country: TRI², mean², variance, variance share, TRI/mean
  metrics-manifest.json  weight mode, panel manifest, row counts

Runs in seconds. The panel must exist (python scripts/build_panel.py).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

from tri import config  # noqa: E402
from tri import metrics as M  # noqa: E402
from tri.load import load_panel  # noqa: E402
from tri.weights import weight_table  # noqa: E402


def decomposition(country: pd.DataFrame) -> pd.DataFrame:
    """TRI² = mean² + V, in percentage points squared, plus the two ratios."""
    d = country[["date", "CTY_CODE", "CTY_NAME", "sqrtariff", "meanweighted"]].copy()
    d["tri2"] = (100 * d["sqrtariff"]) ** 2
    d["mean2"] = (100 * d["meanweighted"]) ** 2
    d["variance"] = d["tri2"] - d["mean2"]
    d["variance_share"] = d["variance"] / d["tri2"]
    d["tri_over_mean"] = d["sqrtariff"] / d["meanweighted"]
    return d


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--weights", choices=["annual", "january"], default=config.WEIGHT_MODE_DEFAULT,
                    help="weight period (january only reproduces the pre-refactor notebooks)")
    ap.add_argument("--renormalize", choices=list(M.RENORMALIZE_MODES), default=config.RENORMALIZE_DEFAULT,
                    help="denominator: every good in the weight period (universe) or the goods present in the month (present)")
    ap.add_argument("--out", type=Path, default=config.METRICS_DIR, help="output directory (default data/metrics)")
    args = ap.parse_args()

    t0 = time.time()
    panel = load_panel()
    w = weight_table(panel, mode=args.weights)
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    rn = args.renormalize

    def since(df, key):
        return df[df["date"] >= pd.Timestamp(config.SERIES_START[key])].reset_index(drop=True)

    country = since(M.country_metrics(panel, w, config.COUNTRIES_30, renormalize=rn), "country")
    top20 = since(M.country_metrics(panel, w, config.COUNTRIES_20, renormalize=rn), "country")
    shares = M.sector_shares(panel)
    hs2 = shares["HS2"].head(config.N_SECTORS_TABLE).tolist()
    sector = since(M.sector_metrics(panel, w, config.COUNTRIES_20, hs2, renormalize=rn), "sector")
    enduse = since(M.enduse_metrics(panel, w, config.COUNTRIES_20, renormalize=rn), "enduse")
    hist = since(M.histogram_shares(panel, w, config.COUNTRIES_30), "country")
    decomp = decomposition(country)

    files = {
        "country.parquet": country, "country-top20.parquet": top20, "sector.parquet": sector,
        "sector-shares.parquet": shares, "enduse.parquet": enduse, "histogram.parquet": hist,
        "decomposition.parquet": decomp,
    }
    for name, df in files.items():
        df.to_parquet(out / name, index=False)

    manifest = {
        "weights": args.weights, "weight_year": config.WEIGHT_YEAR, "renormalize": rn,
        "panel": json.loads(config.PANEL_MANIFEST.read_text()) if config.PANEL_MANIFEST.exists() else None,
        "last_month": f"{country['date'].max():%Y-%m}",
        "rows": {k: len(v) for k, v in files.items()},
        "min_weight_coverage": {
            "country": float(country["weight_coverage"].min()),
            "sector": float(sector["weight_coverage"].min()),
            "enduse": float(enduse["weight_coverage"].min()),
        },
    }
    (out / "metrics-manifest.json").write_text(json.dumps(manifest, indent=1))

    last = country[(country["CTY_CODE"] == "ALL") & (country["date"] == country["date"].max())].iloc[0]
    print(f"weights={args.weights} renormalize={rn}  months through {manifest['last_month']}  "
          f"ALL COUNTRIES {last['date']:%Y-%m}: TRI {100*last['sqrtariff']:.1f}  mean {100*last['meanweighted']:.1f}  "
          f"duties/imports {100*last['simplemean']:.1f}  coverage {last['weight_coverage']:.3f}")
    print("min weight coverage:", {k: round(v, 3) for k, v in manifest["min_weight_coverage"].items()})
    print(f"wrote {len(files)} files to {out} in {time.time() - t0:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
