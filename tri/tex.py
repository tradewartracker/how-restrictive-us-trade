"""Writers for the paper's generated LaTeX pieces, from data/metrics/.

results.tex          macros: current month, comparison month, peak, pre-ruling, three countries
results-sector.tex   macros: four sectors at the current month
table.tex            top-20 countries + their aggregate at the current month
table-sector.tex     top-20 HS2 chapters at the current month, with 2024 import shares

The macro names and table layouts are unchanged from the notebooks so the
paper's .tex needs no edits. Values are rounded exactly as before (macros to
whole percent, tables to 0.1).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from . import config

METRIC_COLS = ["sqrtariff", "meanweighted", "simplemean"]


def _month_name(month: str) -> str:
    return pd.to_datetime(month, format="%Y-%m").strftime("%B %Y")


def _row(df: pd.DataFrame, month: str, **key) -> pd.Series:
    sel = df["date"] == pd.Timestamp(month + "-01")
    for k, v in key.items():
        sel &= df[k] == v
    hit = df[sel]
    if len(hit) != 1:
        raise KeyError(f"expected one row for {month} {key}, found {len(hit)}")
    return hit.iloc[0]


def _macro(name: str, value) -> str:
    v = f"{value*100:.0f}" if isinstance(value, float) else str(value)
    return f"\\newcommand{{\\{name}}}{{{v}}}\n"


# --- results.tex ----------------------------------------------------------------
def results_macros(country: pd.DataFrame, target: str, comparison: str,
                   peak: str = "2025-10", preruling: str = "2026-02") -> str:
    """The 27 macros of results.tex, in the order the notebook wrote them."""
    cur = _row(country, target, CTY_CODE="ALL")
    old = _row(country, comparison, CTY_CODE="ALL")
    lines = [
        _macro("rmsValuetwofive", cur["sqrtariff"]),
        _macro("meanWeightedValuetwofive", cur["meanweighted"]),
        _macro("simpleMeanValuetwofive", cur["simplemean"]),
        _macro("currentdate", _month_name(target)),
        _macro("diffmeanWeightedValuetwofive", cur["sqrtariff"] - cur["meanweighted"]),
        _macro("diffsimpleMeanValuetwofive", cur["sqrtariff"] - cur["simplemean"]),
        _macro("rmsValuetwofour", old["sqrtariff"]),
        _macro("meanWeightedValuetwofour", old["meanweighted"]),
        _macro("simpleMeanValuetwofour", old["simplemean"]),
        _macro("olddate", _month_name(comparison)),
    ]
    for month, tag in [(peak, "peak"), (preruling, "preruling")]:
        r = _row(country, month, CTY_CODE="ALL")
        lines += [
            _macro(f"{tag}date", _month_name(month)),
            _macro(f"rmsValue{tag}", r["sqrtariff"]),
            _macro(f"meanWeightedValue{tag}", r["meanweighted"]),
            _macro(f"simpleMeanValue{tag}", r["simplemean"]),
        ]
    for cty, code in [("canada", "1220"), ("mexico", "2010"), ("china", "5700")]:
        r = _row(country, target, CTY_CODE=code)
        lines += [
            _macro(f"{cty}rmsValuetwofive", r["sqrtariff"]),
            _macro(f"{cty}meanWeightedValuetwofive", r["meanweighted"]),
            _macro(f"{cty}simpleMeanValuetwofive", r["simplemean"]),
        ]
    return "".join(lines)


# --- results-sector.tex ---------------------------------------------------------
SECTOR_MACROS = [("84", "Machinery"), ("85", "ElectricalEquipment"), ("87", "Vehicles"), ("30", "Pharmaceuticals")]


def sector_macros(sector: pd.DataFrame, target: str) -> str:
    lines = []
    for hs2, tag in SECTOR_MACROS:
        r = _row(sector, target, HS2=hs2)
        lines += [
            _macro(f"rmsValuetwofive{tag}", r["sqrtariff"]),
            _macro(f"meanWeightedValuetwofive{tag}", r["meanweighted"]),
            _macro(f"simpleMeanValuetwofive{tag}", r["simplemean"]),
        ]
    return "".join(lines)


# --- tables -----------------------------------------------------------------------
def _to_latex(df: pd.DataFrame, caption: str, label: str) -> str:
    s = df.to_latex(index=False, escape=False, float_format="%.1f", caption=caption, label=label)
    return s.replace(r"\begin{table}", r"\begin{table}" + "\n\\centering")


def country_table(top20: pd.DataFrame, target: str) -> str:
    """Top-20 partners plus their aggregate ('All Countries' = the 20-country
    aggregate, as in the paper), sorted by TRI."""
    foo = top20[top20["date"] == pd.Timestamp(target + "-01")][["CTY_NAME"] + METRIC_COLS].iloc[0:21]
    foo = foo.sort_values(by="sqrtariff", ascending=False).reset_index(drop=True)
    foo[METRIC_COLS] = 100 * foo[METRIC_COLS]
    foo["CTY_NAME"] = foo["CTY_NAME"].str.title()
    foo = foo.rename(columns={"CTY_NAME": "Country", "sqrtariff": "TRI Tariff",
                              "meanweighted": "Mean Weighted Tariff", "simplemean": "Duties / Imports"})
    return _to_latex(foo, f"Tariff Metrics by Country: {_month_name(target)}", "tab:tariff_metrics")


def sector_table(sector: pd.DataFrame, shares: pd.DataFrame, target: str) -> str:
    """Top-20 HS2 chapters at the target month with their 2024 share of all imports."""
    hs2 = shares["HS2"].head(config.N_SECTORS_TABLE).tolist()
    cur = sector[(sector["date"] == pd.Timestamp(target + "-01")) & sector["HS2"].isin(hs2)]
    foo = cur.merge(shares[["HS2", "share"]], on="HS2")
    foo["HS2_name"] = foo["HS2"].map(config.HS2_NAMES)
    foo = foo[["HS2", "HS2_name"] + METRIC_COLS + ["share"]].sort_values(by="sqrtariff", ascending=False).iloc[0:21]
    foo[METRIC_COLS + ["share"]] = 100 * foo[METRIC_COLS + ["share"]]
    foo = foo.rename(columns={"HS2_name": "HS2 Name", "sqrtariff": "TRI Tariff", "meanweighted": "Mean Weighted Tariff",
                              "simplemean": "Duties / Imports", "share": "Share of U.S. Imports"})
    return _to_latex(foo, f"Tariff Metrics by Sector: {_month_name(target)}", "tab:tariff_sector")


# --- driver ------------------------------------------------------------------------
def write_all(target: str, metrics_dir: Path = config.METRICS_DIR, paper_dir: Path = config.PAPER_DIR,
              comparison: str | None = None) -> dict[str, str]:
    """Write the four files; returns {filename: text}."""
    comparison = comparison or f"{config.WEIGHT_YEAR}-{target.split('-')[1]}"
    country = pd.read_parquet(metrics_dir / "country.parquet")
    top20 = pd.read_parquet(metrics_dir / "country-top20.parquet")
    sector = pd.read_parquet(metrics_dir / "sector.parquet")
    shares = pd.read_parquet(metrics_dir / "sector-shares.parquet")
    texts = {
        "results.tex": results_macros(country, target, comparison),
        "results-sector.tex": sector_macros(sector, target),
        "table.tex": country_table(top20, target),
        "table-sector.tex": sector_table(sector, shares, target),
    }
    for name, text in texts.items():
        # platform newline translation on purpose: the notebooks wrote these in text
        # mode, so on Windows the committed files are CRLF
        with open(paper_dir / name, "w", encoding="utf-8") as f:
            f.write(text)
    return texts
