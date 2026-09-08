"""Small plotting helpers shared by the notebooks (policy-event lines, the
house style for axes, the tariff histogram)."""
from __future__ import annotations

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd

from . import config


def add_policy_lines(ax) -> None:
    """Gray vertical lines at Liberation Day and the IEEPA ruling; both pick up legend entries."""
    ax.axvline(config.LIBERATION_DAY, color="gray", linestyle="--", linewidth=2.5, alpha=0.9, zorder=0, label="Liberation Day")
    ax.axvline(config.IEEPA_RULING, color="gray", linestyle="-.", linewidth=2.5, alpha=0.9, zorder=0, label="IEEPA tariffs struck down")


def style_axes(ax, labelsize: int = 16) -> None:
    ax.tick_params(axis="x", labelsize=labelsize)
    ax.tick_params(axis="y", labelsize=labelsize)
    ax.spines["right"].set_visible(False)
    ax.spines["top"].set_visible(False)
    ax.spines["left"].set_linewidth(3)
    ax.spines["bottom"].set_linewidth(3)


def month_shares(hist: pd.DataFrame, month: str) -> tuple[np.ndarray, np.ndarray]:
    """(bin_edges, fractions) for one month from data/metrics/histogram.parquet."""
    h = hist[hist["date"] == pd.Timestamp(month + "-01")].sort_values("bin")
    if h.empty:
        raise KeyError(f"no histogram rows for {month}")
    edges = np.append(h["bin_lo"].to_numpy(), h["bin_hi"].iloc[-1])
    return edges, h["share"].to_numpy()


def month_stats(country: pd.DataFrame, month: str, code: str = "ALL") -> pd.Series:
    """The three measures for one month and entity from data/metrics/country.parquet."""
    r = country[(country["date"] == pd.Timestamp(month + "-01")) & (country["CTY_CODE"] == code)]
    if len(r) != 1:
        raise KeyError(f"expected one row for {month} {code}, found {len(r)}")
    return r.iloc[0]


def tariff_histogram(ax, edges: np.ndarray, fractions: np.ndarray, stats: pd.Series, color: str = "darkblue") -> None:
    """Bars for the bin shares plus the three measure lines; no titles or annotations."""
    ax.bar(edges[:-1], fractions, width=np.diff(edges), align="edge", color=color, alpha=0.75, edgecolor="black")
    ax.axvline(100 * stats["simplemean"], color="darkblue", linestyle=":", linewidth=4, alpha=0.9, label="Duties / Imports")
    ax.axvline(100 * stats["meanweighted"], color="black", linestyle="--", linewidth=4, alpha=0.8, label="Mean Weighted Tariff")
    ax.axvline(100 * stats["sqrtariff"], color="red", linestyle="--", linewidth=4, alpha=0.8, label="TRI Tariff")
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(xmax=1))
    style_axes(ax, 14)


def savefig(fig, stem: str) -> None:
    """Write paper/figures/<stem>.png and .pdf."""
    for ext in ("png", "pdf"):
        fig.savefig(config.FIGURES_DIR / f"{stem}.{ext}", bbox_inches="tight")
