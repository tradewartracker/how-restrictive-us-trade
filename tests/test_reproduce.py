"""The refactor gate: tri/ in January-weight mode must reproduce the notebook
pipeline's committed outputs at 2026-07 (tests/baseline-2026-07/) cell by cell.

    python -m pytest tests/test_reproduce.py -q

Needs the panel (python scripts/build_panel.py). The January mode exists only
for this test; see REFACTOR-PLAN.md §2 and §6.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from tri import config
from tri import metrics as M
from tri.load import load_panel
from tri.weights import weight_table

BASELINE = Path(__file__).parent / "baseline-2026-07"
RTOL = 1e-12
MEASURES = ["sqrtariff", "meanweighted", "simplemean"]

pytestmark = pytest.mark.skipif(not config.PANEL_FILE.exists(), reason="panel not built")


@pytest.fixture(scope="module")
def panel():
    return load_panel()


@pytest.fixture(scope="module")
def weights(panel):
    return weight_table(panel, mode="january")


def _assert_match(new: pd.DataFrame, base_file: str, keys: list[str], cols: list[str]):
    base = pd.read_parquet(BASELINE / base_file)
    base["date"] = pd.to_datetime(base["date"])
    m = base.merge(new, on=keys, how="left", suffixes=("_b", "_n"), indicator=True)
    assert (m["_merge"] == "both").all(), f"{base_file}: {(m['_merge'] != 'both').sum()} baseline rows not produced"
    for c in cols:
        np.testing.assert_allclose(m[c + "_n"].to_numpy(), m[c + "_b"].to_numpy(), rtol=RTOL, err_msg=f"{base_file}: {c}")


def test_country(panel, weights):
    new = M.country_metrics(panel, weights, config.COUNTRIES_30)
    _assert_match(new, "top-country-metrics.parquet", ["date", "CTY_NAME"], MEASURES + ["duty_total"])


def test_sector(panel, weights):
    hs2 = M.sector_shares(panel)["HS2"].head(config.N_SECTORS_SERIES).tolist()
    assert hs2 == ["84", "85", "87", "30", "90", "39", "94", "29", "73", "61"]
    new = M.sector_metrics(panel, weights, config.COUNTRIES_20, hs2)
    _assert_match(new, "top-sector-metrics.parquet", ["date", "HS2"], MEASURES)


def test_enduse(panel, weights):
    new = M.enduse_metrics(panel, weights, config.COUNTRIES_20)
    _assert_match(new, "enduse-metrics.parquet", ["date", "ENDUSE"], MEASURES)


def test_tex_fragments(panel, weights, tmp_path):
    """The four generated .tex files, line for line (line endings ignored)."""
    from tri.tex import write_all
    hs2 = M.sector_shares(panel)["HS2"].head(config.N_SECTORS_TABLE).tolist()
    metrics = tmp_path / "metrics"; metrics.mkdir()
    M.country_metrics(panel, weights, config.COUNTRIES_30).to_parquet(metrics / "country.parquet", index=False)
    M.country_metrics(panel, weights, config.COUNTRIES_20).to_parquet(metrics / "country-top20.parquet", index=False)
    M.sector_metrics(panel, weights, config.COUNTRIES_20, hs2).to_parquet(metrics / "sector.parquet", index=False)
    M.sector_shares(panel).to_parquet(metrics / "sector-shares.parquet", index=False)
    paper = tmp_path / "paper"; paper.mkdir()
    write_all("2026-07", metrics_dir=metrics, paper_dir=paper)
    for name in ["results.tex", "results-sector.tex", "table.tex", "table-sector.tex"]:
        got = (paper / name).read_text().splitlines()
        want = (BASELINE / name).read_text().splitlines()
        assert got == want, name
