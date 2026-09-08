"""Stage 2c: write the paper's generated LaTeX pieces from data/metrics/.

    python scripts/build_paper_inputs.py --target 2026-07 [--comparison 2024-07]

Writes paper/results.tex, results-sector.tex, table.tex, table-sector.tex.
Figures are made by the plotting notebooks; nothing here plots.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tri import config  # noqa: E402
from tri.tex import write_all  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--target", required=True, help="most recent month, YYYY-MM")
    ap.add_argument("--comparison", default=None, help="pre-trade-war month for the twofour macros (default: same month of the weight year)")
    args = ap.parse_args()
    texts = write_all(args.target, comparison=args.comparison)
    for name, text in texts.items():
        print(f"{name}: {text.count(chr(10))} lines -> {config.PAPER_DIR / name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
