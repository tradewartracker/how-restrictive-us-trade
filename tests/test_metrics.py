"""Properties the measures must satisfy, checked on a small synthetic panel and,
when the panel is built, on the real data."""
import numpy as np
import pandas as pd
import pytest

from tri import config
from tri import metrics as M
from tri.weights import weight_table


def _toy_panel():
    """Two countries, three goods, two months; one good vanishes in month 2."""
    rows = []
    months = pd.to_datetime(["2024-01-01", "2024-02-01"])
    goods = {"A": [("g1", 100.0, 10.0), ("g2", 300.0, 0.0)], "B": [("g1", 200.0, 50.0), ("g3", 100.0, 20.0)]}
    for cty, gs in goods.items():
        for t in months:
            for g, v, d in gs:
                if t == months[1] and g == "g3":
                    continue  # vanishes
                rows.append({"CTY_CODE": cty, "CTY_NAME": cty, "I_COMMODITY": g + "00000000", "time": t,
                             "CON_VAL_MO": v, "CAL_DUT_MO": d})
    p = pd.DataFrame(rows)
    p["HS2"] = p["I_COMMODITY"].str[:2]
    p["HS6"] = p["I_COMMODITY"].str[:6]
    return p


def test_measures_by_hand():
    p = _toy_panel()
    w = weight_table(p, year=2024, mode="january")
    out = M.country_metrics(p, w, ["A", "B"]).set_index(["date", "CTY_NAME"])
    jan = pd.Timestamp("2024-01-01")
    # Country A, January: goods g1 (τ=.1, w=100) and g2 (τ=0, w=300)
    a = out.loc[(jan, "A")]
    assert np.isclose(a["meanweighted"], 100 * 0.1 / 400)
    assert np.isclose(a["sqrtariff"], np.sqrt(100 * 0.01 / 400))
    assert np.isclose(a["simplemean"], 10 / 400)
    # Aggregate identity: TRI_all² = Σ_c s_c TRI_c² with s_c = country share of the weight base
    allc = out.loc[(jan, "ALL COUNTRIES")]
    per = out.loc[jan].drop("ALL COUNTRIES")
    shares = w.groupby("CTY_CODE")["weight"].sum() / w["weight"].sum()
    assert np.isclose(allc["sqrtariff"] ** 2, (shares.loc[per.index] * per["sqrtariff"] ** 2).sum())
    # Vanished good: February coverage for B drops, denominator unchanged
    feb = pd.Timestamp("2024-02-01")
    assert out.loc[(feb, "B"), "weight_coverage"] == pytest.approx(200 / 300)
    assert out.loc[(feb, "B"), "meanweighted"] == pytest.approx(200 * 0.25 / 300)


@pytest.mark.skipif(not config.PANEL_FILE.exists(), reason="panel not built")
def test_aggregate_identity_real_data():
    from tri.load import load_panel
    panel = load_panel()
    w = weight_table(panel, mode="annual")
    out = M.country_metrics(panel, w, config.COUNTRIES_30)
    shares = w[w["CTY_CODE"].isin(config.COUNTRIES_30)].groupby("CTY_CODE", observed=True)["weight"].sum()
    shares = shares / shares.sum()
    assert (out["sqrtariff"] > 0).all() and (out["sqrtariff"] >= out["meanweighted"]).all(), "TRI must be positive and >= the mean"
    for date, grp in out.groupby("date"):
        allc = grp[grp["CTY_CODE"] == "ALL"]["sqrtariff"].iloc[0]
        per = grp[grp["CTY_CODE"] != "ALL"].set_index("CTY_CODE")["sqrtariff"]
        lhs, rhs = allc ** 2, (shares.loc[per.index] * per ** 2).sum()
        assert lhs > 0 and np.isclose(lhs, rhs, rtol=1e-10), (date, lhs, rhs)
