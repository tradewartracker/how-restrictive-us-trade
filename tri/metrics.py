"""The three tariff measures, for any grouping, from the panel and a weight table.

For a set of goods G with weights w_g (import value over the weight period)
and month-t tariffs τ_g = duties / value:

    sqrtariff    = sqrt( Σ_g w_g τ_g²  /  Σ_g w_g )      the TRI (import-weighted RMS tariff)
    meanweighted =       Σ_g w_g τ_g   /  Σ_g w_g        the mean weighted tariff
    simplemean   =       Σ_g duties_g  /  Σ_g value_g    duties / imports

The denominator Σ w_g runs over the *weight universe* of the grouping -- every
good that had weight in the weight period -- while the numerators can only
include goods present in month t (an absent good contributes nothing). This is
exactly what the notebooks did through 2026-09; ``weight_coverage`` reports
Σ_{present} w / Σ_{universe} w so the gap is visible. A good present in month t
but without a weight is dropped. A good with zero value in month t has an
undefined tariff (NaN if duties are also zero, inf otherwise) and is skipped by
the sums, again as before.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config
from .weights import KEYS

MEASURES = ["sqrtariff", "meanweighted", "simplemean"]


# --- the merged frame --------------------------------------------------------
def merged(panel: pd.DataFrame, weights: pd.DataFrame, codes: list[str] | None = None) -> pd.DataFrame:
    """Panel rows that have a weight (inner merge), with ``tariff``, ``w_t2``, ``w_t``.

    ``codes`` restricts to a list of entities (e.g. the 30 paper countries).
    """
    p = panel if codes is None else panel[panel["CTY_CODE"].isin(codes)]
    m = p.merge(weights[KEYS + ["weight"]], on=KEYS, how="inner")
    # Arithmetic on numpy arrays, not pandas Series: on frames this size pandas
    # hands `*` and `**` to numexpr, and one run produced an all-zero w_t2 that
    # could not be reproduced afterwards. Plain numpy is deterministic.
    with np.errstate(divide="ignore", invalid="ignore"):
        tariff = m["CAL_DUT_MO"].to_numpy(dtype="float64") / m["CON_VAL_MO"].to_numpy(dtype="float64")
    weight = m["weight"].to_numpy(dtype="float64")
    m["tariff"] = tariff
    m["w_t2"] = weight * tariff * tariff
    m["w_t"] = weight * tariff
    return m


RENORMALIZE_MODES = ("universe", "present")


def _measures(m: pd.DataFrame, weights: pd.DataFrame, by: list[str], renormalize: str = "universe") -> pd.DataFrame:
    """Measures by month × ``by`` (``by`` may be empty for a single aggregate).

    ``m`` and ``weights`` must both carry the ``by`` columns; ``weights`` must
    already be restricted to the same entities as ``m``.

    ``renormalize="universe"`` divides by the weight of every good in the weight
    period (a good absent in month t counts as tariff-free; the notebooks'
    behaviour). ``"present"`` divides by the weight of the goods present in
    month t, so the weights sum to one every month and an absent good is
    treated like the average present good. ``weight_coverage`` is the ratio of
    the two denominators either way.
    """
    if renormalize not in RENORMALIZE_MODES:
        raise ValueError(f"renormalize must be one of {RENORMALIZE_MODES}, got {renormalize!r}")
    # Plain column-wise sums on a numeric frame. (A six-way named aggregation on
    # the merged frame returned a zero w_t2 column in one run -- see the note in
    # REFACTOR-PLAN.md §6 -- so the summation is kept as simple as possible and
    # guarded below.)
    cols = {"w_t2": "w_t2", "w_t": "w_t", "CAL_DUT_MO": "duty_total", "CON_VAL_MO": "import_total", "weight": "w_present"}
    g = m.groupby(["time"] + by, observed=True, sort=True)
    num = g[list(cols)].sum().rename(columns=cols)
    num["n_goods"] = g.size()
    num = num.reset_index()
    bad = (num["w_t2"] <= 0) & (num["w_t"] > 0)
    if bad.any():
        raise RuntimeError(f"squared-tariff sum is zero where the linear sum is positive in {int(bad.sum())} groups")
    if by:
        den = weights.groupby(by, observed=True)["weight"].sum().rename("w_universe").reset_index()
        out = num.merge(den, on=by, how="left")
    else:
        out = num.assign(w_universe=weights["weight"].sum())
    den = out["w_universe"] if renormalize == "universe" else out["w_present"]
    out["sqrtariff"] = np.sqrt(out["w_t2"] / den)
    out["meanweighted"] = out["w_t"] / den
    out["simplemean"] = out["duty_total"] / out["import_total"]
    out["weight_coverage"] = out["w_present"] / out["w_universe"]
    out = out.rename(columns={"time": "date"})
    return out[["date"] + by + MEASURES + ["duty_total", "import_total", "n_goods", "weight_coverage"]]


# --- country -----------------------------------------------------------------
def country_metrics(panel: pd.DataFrame, weights: pd.DataFrame, codes: list[str], all_label: str = "ALL COUNTRIES",
                    renormalize: str = "universe") -> pd.DataFrame:
    """Per-country measures (weights renormalised within each country) plus the
    aggregate over ``codes`` (weights normalised over all of them)."""
    m = merged(panel, weights, codes)
    w = weights[weights["CTY_CODE"].isin(codes)]
    per = _measures(m, w, ["CTY_CODE"], renormalize)
    names = w.drop_duplicates("CTY_CODE").set_index("CTY_CODE")["CTY_NAME"]
    per.insert(2, "CTY_NAME", per["CTY_CODE"].map(names))
    agg = _measures(m, w, [], renormalize)
    agg.insert(1, "CTY_CODE", "ALL")
    agg.insert(2, "CTY_NAME", all_label)
    out = pd.concat([agg, per], ignore_index=True).sort_values(["date", "CTY_CODE"], kind="stable")
    return out.reset_index(drop=True)


# --- sector (HS2) -----------------------------------------------------------
def sector_shares(panel: pd.DataFrame, year: int = config.WEIGHT_YEAR) -> pd.DataFrame:
    """HS2 chapters ranked by import value in ``year`` from Census's TOTAL file.

    ``share`` is the chapter's share of *all* imports (computed before the
    exclusions, as the sector notebook does); the excluded chapters are then
    dropped and the frame is sorted by value, descending.
    """
    t = panel[(panel["CTY_CODE"] == config.TOTAL) & (panel["time"].dt.year == year)]
    bar = t.groupby("HS2", observed=True)["CON_VAL_MO"].sum().reset_index()
    bar["share"] = bar["CON_VAL_MO"] / bar["CON_VAL_MO"].sum()
    bar = bar[~bar["HS2"].isin(config.SECTOR_EXCLUDE_HS2)]
    return bar.sort_values("CON_VAL_MO", ascending=False).reset_index(drop=True)


def sector_metrics(panel: pd.DataFrame, weights: pd.DataFrame, codes: list[str], hs2: list[str],
                   renormalize: str = "universe") -> pd.DataFrame:
    """Measures by month × HS2 over the countries in ``codes``, weights
    normalised within each chapter."""
    m = merged(panel, weights, codes)
    m = m[m["HS2"].isin(hs2)]
    w = weights[weights["CTY_CODE"].isin(codes) & weights["HS2"].isin(hs2)]
    return _measures(m, w, ["HS2"], renormalize)


# --- end use ----------------------------------------------------------------
def enduse_map() -> pd.Series:
    e = pd.read_parquet(config.ENDUSE_FILE)
    return pd.Series(e["BEC5EndUse"].to_numpy(), index=e["HS6"].astype(str).to_numpy(), name="ENDUSE")


def enduse_metrics(panel: pd.DataFrame, weights: pd.DataFrame, codes: list[str], categories: list[str] = config.ENDUSE_CATEGORIES,
                   renormalize: str = "universe") -> pd.DataFrame:
    """Measures by month × BEC end-use category over ``codes``, weights
    normalised within each category. Goods whose HS6 has no mapping are excluded."""
    emap = enduse_map()
    m = merged(panel, weights, codes)
    m["ENDUSE"] = m["HS6"].map(emap)
    m = m[m["ENDUSE"].isin(categories)]
    w = weights[weights["CTY_CODE"].isin(codes)].copy()
    w["ENDUSE"] = w["HS6"].map(emap)
    w = w[w["ENDUSE"].isin(categories)]
    return _measures(m, w, ["ENDUSE"], renormalize)


# --- histogram --------------------------------------------------------------
def histogram_shares(panel: pd.DataFrame, weights: pd.DataFrame, codes: list[str], edges: np.ndarray = config.HIST_BIN_EDGES) -> pd.DataFrame:
    """Share of month-t import value in each tariff bin (percent edges), over the
    goods with weight. Goods whose tariff falls outside the bins (above the top
    edge, or undefined) stay in the denominator, as in the notebook figure."""
    m = merged(panel, weights, codes)
    m["bin"] = np.digitize(100 * m["tariff"].to_numpy(), edges) - 1
    tot = m.groupby("time", observed=True)["CON_VAL_MO"].sum().rename("total")
    inb = m[(m["bin"] >= 0) & (m["bin"] < len(edges) - 1)]
    s = inb.groupby(["time", "bin"], observed=True)["CON_VAL_MO"].sum().rename("value").reset_index()
    grid = pd.MultiIndex.from_product([tot.index, range(len(edges) - 1)], names=["time", "bin"]).to_frame(index=False)
    s = grid.merge(s, on=["time", "bin"], how="left").fillna({"value": 0.0}).merge(tot, on="time")
    s["share"] = s["value"] / s["total"]
    s["bin_lo"] = edges[s["bin"]]
    s["bin_hi"] = edges[s["bin"] + 1]
    return s.rename(columns={"time": "date"})[["date", "bin", "bin_lo", "bin_hi", "share", "value", "total"]]
