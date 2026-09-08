"""Paths, entity lists, and the fixed choices behind the TRI measures.

Everything the scripts and notebooks share lives here so that a choice (the
weight year, the sector exclusions, the policy-event dates) is made once.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .hs2_names import HS2_NAMES  # noqa: F401  (re-exported)

# --- paths -----------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
IMPORTS_DIR = DATA_DIR / "imports-hs10"          # built by ../trade-data notebook 04
PANEL_DIR = DATA_DIR / "panel"                    # gitignored, regenerable
PANEL_FILE = PANEL_DIR / "tariff-panel.parquet"
PANEL_MANIFEST = PANEL_DIR / "manifest.json"
METRICS_DIR = DATA_DIR / "metrics"                # committed, small
PAPER_DIR = REPO_ROOT / "paper"
FIGURES_DIR = PAPER_DIR / "figures"
ENDUSE_FILE = DATA_DIR / "hs6-enduse.parquet"     # HS6 -> BEC5 end use (CONS / CAP / INT / OTHER)

# --- entities ----------------------------------------------------------------
def _codes(name: str) -> list[str]:
    return pd.read_csv(DATA_DIR / name, header=None, names=["CTY_CODE"], dtype=str)["CTY_CODE"].tolist()


COUNTRIES_30 = _codes("country-list.csv")       # the paper's country universe
COUNTRIES_20 = _codes("country-list-20.csv")    # top-20 partners: tables, sectors, end use
TOTAL = "TOTAL"                                 # Census's published all-country total
PANEL_ENTITIES = COUNTRIES_30 + [TOTAL]

# --- the panel --------------------------------------------------------------
PANEL_START = "2024-01"     # nothing before the weight year is ever used

# --- the measures -----------------------------------------------------------
WEIGHT_YEAR = 2024
# "annual": calendar-year import value (what the paper says).
# "january": January only -- reproduces the notebooks as of 2026-09 (see REFACTOR-PLAN.md §2).
WEIGHT_MODE_DEFAULT = "annual"

SERIES_START = {"country": "2024-01", "sector": "2025-01", "enduse": "2025-01"}

SECTOR_EXCLUDE_HS2 = ["99", "98", "27", "71"]   # special classifications, petroleum, precious metals
N_SECTORS_SERIES = 10                           # HS2 chapters in the time series
N_SECTORS_TABLE = 20                            # HS2 chapters in the paper's table
ENDUSE_CATEGORIES = ["CONS", "CAP", "INT"]

HIST_BIN_EDGES = np.linspace(-0.01, 50, 11)     # tariff histogram, percent

# --- policy events (vertical lines on the time-series plots) -----------------
LIBERATION_DAY = pd.Timestamp("2025-04-02")
IEEPA_RULING = pd.Timestamp("2026-02-20")        # Supreme Court strikes down the IEEPA tariffs -- confirm the exact date
