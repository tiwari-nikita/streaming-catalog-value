"""
Every figure published in MEMO.md and README.md, asserted against the generated outputs.
Run: python -m pytest tests/ -v   or   python tests/test_claims.py
"""
import hashlib
import pathlib
import sys

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT, RAW, PROC = ROOT / "output", ROOT / "data" / "raw", ROOT / "data" / "processed"

HASHES = {
    "netflix_engagement_2023H1.xlsx": "c6fd33eb4c243e6e18d81a248ad71a28e8ccc3d0dd2b1fbc9f8538c649d28637",
    "netflix_engagement_2023H2.xlsx": "ea536b6e1f3771ba662e57a72ab847efd0200b3e4adb93a2f7d3e2b133f5b655",
    "netflix_engagement_2024H1.xlsx": "2803512229889f91b51c214b9494b7a55799767d63e3f5cf2c142b1917a18d62",
    "netflix_engagement_2024H2.xlsx": "3030e3630fb0ff90d8d84b9cda3c22c83f4e9e356d4f1742bda729bfa2fc738c",
    "netflix_engagement_2025H1.xlsx": "7208fc0207818f961652748d19500221b1d3edce8999b83e0f954f27fb31e8dd",
    "netflix_engagement_2025H2.xlsx": "a06b0f510264336ad31f29a0ed4aaa51247374dcaa8aee780bbecf50227635cb",
    "netflix_engagement_2026H1.xlsx": "bcfda87e87d09d923472a1e1b30d5c7c799457aacba41310a9d223e834fe2f5f",
}


def near(a, b, tol, label):
    assert abs(a - b) <= tol, "{}: expected {} +/- {}, got {}".format(label, b, tol, a)


def test_raw_data_unmodified():
    """Seven Netflix reports match the SHA-256 recorded at download."""
    for name, h in HASHES.items():
        assert hashlib.sha256((RAW / name).read_bytes()).hexdigest() == h, name + " changed"


def test_panel_size():
    """CLAIM: 97,736 title-period rows covering 28,694 titles across six halves."""
    p = pd.read_parquet(PROC / "panel.parquet")
    assert len(p) == 97736, len(p)
    assert p[["title", "type"]].drop_duplicates().shape[0] == 28694
    assert p["period"].nunique() == 6


def test_totals_match_netflix():
    """External check: Netflix reported 'more than 97 billion hours' for H1 2026."""
    t = pd.read_csv(OUT / "total_hours_by_period.csv").set_index("period")["hours_billions"]
    assert 97.0 <= t["2026H1"] <= 98.0, t["2026H1"]


def test_licensed_share():
    """CLAIM: licensed titles supply 47-51% of all viewing in every half."""
    m = pd.read_csv(OUT / "viewing_mix_by_segment.csv", index_col=0)
    assert m["Licensed"].between(46.5, 51.5).all(), m["Licensed"].tolist()


def test_concentration():
    """CLAIM: under 5% of titles deliver half of viewing; top 1% = 24-26% of hours."""
    c = pd.read_csv(OUT / "concentration.csv")
    assert ((c["titles_for_half_of_hours"] / c["titles"]) < 0.05).all()
    assert c["top1pct_share"].between(23.5, 26.5).all()


def test_launch_decay():
    """CLAIM: a new original's daily viewing falls over 90% after its launch half."""
    d = pd.read_csv(OUT / "launch_decay.csv").set_index("type")
    assert d.loc["All", "median_retained_next_half"] < 0.10
    assert int(d.loc["All", "titles"]) == 1368


def test_retention_by_segment():
    """CLAIM: catalog originals keep 82%, licensed 80%, new originals 29% of hours."""
    r = pd.read_csv(OUT / "retention_by_segment.csv").set_index("segment")["avg_hours_kept_pct"]
    near(r["Catalog original"], 81.7, 0.5, "catalog")
    near(r["Licensed"], 79.9, 0.5, "licensed")
    near(r["New original"], 29.4, 0.5, "new")


def test_twelve_month_value():
    """CLAIM: next 12 months worth ~1.4x a licensed title's latest half (0.8 + 0.8^2)."""
    r = pd.read_csv(OUT / "retention_by_segment.csv").set_index("segment")["avg_hours_kept_pct"]
    k = r["Licensed"] / 100
    near(k + k ** 2, 1.44, 0.02, "12-month multiple")


def test_licensed_dropout():
    """CLAIM: licensed titles fall off the list 3.6x as often as catalog originals (22% vs 6%)."""
    r = pd.read_csv(OUT / "retention_by_segment.csv").set_index("segment")["avg_dropped_pct"]
    near(r["Licensed"] / r["Catalog original"], 3.6, 0.1, "dropout ratio")


def test_forecast_beats_baselines():
    """CLAIM: model 24.7% median error vs 26.2% (segment naive) and 27.2% (flat); R2 0.818."""
    m = pd.read_csv(OUT / "forecast_metrics.csv").set_index("model")
    gb = m.loc["Gradient boosting (median loss)"]
    near(gb["median_abs_pct_error"], 24.7, 0.2, "model error")
    near(gb["r2_log"], 0.818, 0.005, "model r2")
    assert gb["median_abs_pct_error"] < m.loc["Naive: segment-specific retention", "median_abs_pct_error"] \
        < m.loc["Naive: flat retention", "median_abs_pct_error"]


def test_forecast_big_licensed():
    """CLAIM: on licensed titles with 1M+ hours, median error falls from 43% to 37%."""
    b = pd.read_csv(OUT / "forecast_metrics_licensed_1m.csv").iloc[0]
    near(b["model_mdape"], 37.0, 0.3, "model")
    near(b["segment_naive_mdape"], 43.1, 0.3, "naive")


def _main():
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_")]
    bad = 0
    for n, f in tests:
        try:
            f()
            print("  PASS  {:<32} {}".format(n, (f.__doc__ or "").strip().splitlines()[0]))
        except AssertionError as e:
            bad += 1
            print("  FAIL  {:<32} {}".format(n, e))
    print("\n{} passed, {} failed".format(len(tests) - bad, bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(_main())
