"""Import-value weights for the TRI measures.

A weight is the import value of a (country, HS10) good over the weight period.
Weights are kept *unnormalised*; every measure normalises over its own grouping
(country, sector, end use, or everything), which is what "renormalising the
weights within the country" means in the paper.
"""
from __future__ import annotations

import pandas as pd

from . import config

KEYS = ["CTY_CODE", "I_COMMODITY"]


def weight_table(panel: pd.DataFrame, year: int = config.WEIGHT_YEAR, mode: str = config.WEIGHT_MODE_DEFAULT) -> pd.DataFrame:
    """One row per (country, HS10) with its import value over the weight period.

    ``mode="annual"`` sums calendar-year ``year``. ``mode="january"`` uses
    January of ``year`` only, which is what the notebooks did through 2026-09
    (``time == "2024"`` on a datetime column matches 2024-01-01); it exists so
    the refactor can be verified against them and should not be used for new
    results.
    """
    if mode == "annual":
        sel = panel["time"].dt.year == year
    elif mode == "january":
        sel = panel["time"] == pd.Timestamp(year=year, month=1, day=1)
    else:
        raise ValueError(f"unknown weight mode {mode!r}")
    w = (
        panel.loc[sel, KEYS + ["CTY_NAME", "CON_VAL_MO"]]
        .groupby(KEYS, as_index=False, sort=False, observed=True)
        .agg(CTY_NAME=("CTY_NAME", "first"), weight=("CON_VAL_MO", "sum"))
    )
    w["HS2"] = w["I_COMMODITY"].str[:2]
    w["HS6"] = w["I_COMMODITY"].str[:6]
    return w
