"""Stage 2a: build data/panel/tariff-panel.parquet from data/imports-hs10/.

One row per (entity, HS10, month) from config.PANEL_START onward, for the 30
paper countries plus Census's TOTAL, with typed columns. Reads each source file
exactly once, in parallel. Skips the build when the source files are unchanged
(size + mtime manifest) unless --force is given.

    python scripts/build_panel.py [--force] [--workers N]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

from tri import config  # noqa: E402
from tri.load import entity_file, load_entity  # noqa: E402


def source_manifest() -> dict:
    out = {}
    for code in config.PANEL_ENTITIES:
        st = entity_file(code).stat()
        out[code] = {"size": st.st_size, "mtime": int(st.st_mtime)}
    return {"start": config.PANEL_START, "sources": out}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--force", action="store_true", help="rebuild even if the sources are unchanged")
    ap.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 1))
    args = ap.parse_args()

    manifest = source_manifest()
    if not args.force and config.PANEL_MANIFEST.exists() and config.PANEL_FILE.exists():
        if json.loads(config.PANEL_MANIFEST.read_text()) == manifest:
            print(f"panel is current ({config.PANEL_FILE}); nothing to do")
            return 0

    t0 = time.time()
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        frames = list(pool.map(load_entity, config.PANEL_ENTITIES))
    panel = pd.concat(frames, ignore_index=True)
    for c in ("CTY_CODE", "CTY_NAME"):
        panel[c] = panel[c].astype("category")

    config.PANEL_DIR.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(config.PANEL_FILE, index=False, compression="zstd")
    config.PANEL_MANIFEST.write_text(json.dumps(manifest, indent=1))

    months = panel["time"].nunique()
    print(f"wrote {config.PANEL_FILE}: {len(panel):,} rows, {panel['CTY_CODE'].nunique()} entities, "
          f"{months} months ({panel['time'].min():%Y-%m} .. {panel['time'].max():%Y-%m}), "
          f"{config.PANEL_FILE.stat().st_size / 1e6:.0f} MB, {time.time() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
