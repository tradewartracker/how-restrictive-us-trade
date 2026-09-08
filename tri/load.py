"""Read the per-entity HS10 import files once, into typed frames.

The files in ``data/imports-hs10/`` are the legacy all-string schema built by
``../trade-data`` (see DATA-PIPELINE.md): one row per (HS10, month), columns
``CTY_NAME, CON_VAL_MO, CAL_DUT_MO, I_COMMODITY, I_COMMODITY_SDESC, time,
COMM_LVL, CTY_CODE`` (``CTY_CODE`` absent in the TOTAL file). Everything that
touches those files goes through :func:`load_entity`.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from . import config

PANEL_COLUMNS = ["CTY_CODE", "CTY_NAME", "I_COMMODITY", "time", "CON_VAL_MO", "CAL_DUT_MO"]


def entity_file(code: str) -> Path:
    """Path of the ``*data-current.parquet`` file for a Census entity code (or ``TOTAL``)."""
    return config.IMPORTS_DIR / f"{code}data-current.parquet"


def load_entity(code: str, start: str = config.PANEL_START) -> pd.DataFrame:
    """One entity's rows from month ``start`` (``YYYY-MM``) onward, typed.

    Returns a frame with :data:`PANEL_COLUMNS`: ``CTY_CODE`` as given (``TOTAL``
    for the published all-country total), ``time`` as month-start Timestamps,
    values as float64. Row order is the file's order.
    """
    table = pq.read_table(
        entity_file(code),
        columns=[c for c in ["CTY_NAME", "CON_VAL_MO", "CAL_DUT_MO", "I_COMMODITY", "time"]],
    )
    # 'time' is a 'YYYY-MM' string, so lexicographic order is chronological order.
    table = table.filter(pc.greater_equal(table["time"], pa.scalar(start)))
    df = table.to_pandas()
    df["CTY_CODE"] = code
    df["CON_VAL_MO"] = df["CON_VAL_MO"].astype("float64")
    df["CAL_DUT_MO"] = df["CAL_DUT_MO"].astype("float64")
    df["time"] = pd.to_datetime(df["time"], format="%Y-%m")
    return df[PANEL_COLUMNS]


def load_panel(path: Path = config.PANEL_FILE) -> pd.DataFrame:
    """The built panel (see ``scripts/build_panel.py``), with derived ``HS2``/``HS6``."""
    df = pd.read_parquet(path)
    df["HS2"] = df["I_COMMODITY"].str[:2]
    df["HS6"] = df["I_COMMODITY"].str[:6]
    return df
