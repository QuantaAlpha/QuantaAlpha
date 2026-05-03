"""Unit tests for quantaalpha.analysis.correlation.

Synthetic data only, no Qlib / no LLM.
"""

import hashlib
import json

import numpy as np
import pandas as pd
import pytest

from quantaalpha.analysis.correlation import (
    FactorDiversificationAnalyzer,
    _matrix_to_records,
    _mean_xs_rank_corr,
    _to_panel,
)


def _make_factor_series(panel, dates, instruments):
    df = pd.DataFrame(panel, index=dates, columns=instruments)
    df.index.name = "datetime"
    df.columns.name = "instrument"
    return df.stack().rename("factor")


def _build_library(tmp_path, factors_meta, panels):
    cache_dir = tmp_path / "factor_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    lib = {
        "metadata": {"created_at": "2026-01-01", "total_factors": len(factors_meta)},
        "factors": {},
    }

    if panels:
        n_dates, n_inst = panels[next(iter(panels))].shape
    else:
        n_dates, n_inst = 60, 30
    dates = pd.date_range("2024-01-01", periods=n_dates, freq="B")
    instruments = [f"SH{600000 + i}" for i in range(n_inst)]

    for fid, meta in factors_meta.items():
        expr = meta["factor_expression"]
        if fid in panels:
            series = _make_factor_series(panels[fid], dates, instruments)
            md5 = hashlib.md5(expr.encode()).hexdigest()
            series.to_pickle(cache_dir / f"{md5}.pkl")
        lib["factors"][fid] = {
            "factor_id": fid,
            "factor_name": meta["factor_name"],
            "factor_expression": expr,
            "factor_description": "",
            "factor_formulation": "",
            "cache_location": {},
            "metadata": {"round_number": 0, "trajectory_id": "", "evolution_phase": "original"},
            "backtest_results": {"IC": meta.get("ic", 0.0), "Rank IC": meta.get("rank_ic", 0.0)},
            "feedback": {},
        }

    lib_path = tmp_path / "library.json"
    lib_path.write_text(json.dumps(lib, default=str))
    return lib_path, cache_dir


@pytest.fixture
def synthetic_library(tmp_path):
    # A and B are near-duplicates, C is independent.
    rng = np.random.default_rng(42)
    n_dates, n_inst = 80, 40
    base = rng.standard_normal((n_dates, n_inst))
    panels = {
        "fid_a": base,
        "fid_b": base + 0.001 * rng.standard_normal((n_dates, n_inst)),
        "fid_c": rng.standard_normal((n_dates, n_inst)),
    }
    factors_meta = {
        "fid_a": {"factor_name": "alpha_a", "factor_expression": "$close",
                   "ic": 0.10, "rank_ic": 0.12},
        "fid_b": {"factor_name": "alpha_b", "factor_expression": "$close + 0.001",
                   "ic": 0.09, "rank_ic": 0.11},
        "fid_c": {"factor_name": "alpha_c", "factor_expression": "$volume",
                   "ic": 0.08, "rank_ic": 0.10},
    }
    lib_path, cache_dir = _build_library(tmp_path, factors_meta, panels)
    return {"library": lib_path, "cache_dir": cache_dir}


def test_to_panel_shape():
    dates = pd.date_range("2024-01-01", periods=10, freq="B")
    inst = ["A", "B", "C"]
    series = _make_factor_series(np.arange(30).reshape(10, 3), dates, inst)
    panel = _to_panel(series)
    assert panel.shape == (10, 3)
    assert list(panel.columns) == inst


def test_mean_xs_rank_corr_perfect():
    dates = pd.date_range("2024-01-01", periods=60, freq="B")
    inst = [f"S{i}" for i in range(20)]
    a = pd.DataFrame(np.random.default_rng(0).standard_normal((60, 20)),
                     index=dates, columns=inst)
    b = a * 2 + 5  # monotonic transform => perfect rank corr
    assert _mean_xs_rank_corr(a, b, min_overlap=10) == pytest.approx(1.0, abs=1e-9)


def test_mean_xs_rank_corr_anticorrelated():
    dates = pd.date_range("2024-01-01", periods=60, freq="B")
    inst = [f"S{i}" for i in range(20)]
    a = pd.DataFrame(np.random.default_rng(1).standard_normal((60, 20)),
                     index=dates, columns=inst)
    b = -a
    assert _mean_xs_rank_corr(a, b, min_overlap=10) == pytest.approx(-1.0, abs=1e-9)


def test_matrix_to_records_handles_nan():
    df = pd.DataFrame([[1.0, np.nan], [np.nan, 1.0]], index=["a", "b"], columns=["a", "b"])
    out = _matrix_to_records(df)
    assert out["ids"] == ["a", "b"]
    assert out["values"][0][1] is None
    assert out["values"][1][0] is None


def test_analyzer_loads_records_and_values(synthetic_library):
    a = FactorDiversificationAnalyzer(synthetic_library["library"],
                                      cache_dir=synthetic_library["cache_dir"])
    n = a.load()
    assert len(a.records) == 3
    assert n == 3


def test_correlation_matrix_identifies_duplicate(synthetic_library):
    a = FactorDiversificationAnalyzer(synthetic_library["library"],
                                      cache_dir=synthetic_library["cache_dir"])
    a.load()
    m = a.correlation_matrix()
    assert m.shape == (3, 3)
    assert m.loc["fid_a", "fid_a"] == pytest.approx(1.0)
    assert m.loc["fid_a", "fid_b"] > 0.95
    assert abs(m.loc["fid_a", "fid_c"]) < 0.4


def test_redundant_pairs(synthetic_library):
    a = FactorDiversificationAnalyzer(synthetic_library["library"],
                                      cache_dir=synthetic_library["cache_dir"])
    a.load()
    pairs = a.redundant_pairs(threshold=0.9)
    assert len(pairs) == 1
    assert {pairs[0]["factor_a"], pairs[0]["factor_b"]} == {"fid_a", "fid_b"}
    assert pairs[0]["correlation"] > 0.9


def test_diversified_subset_drops_duplicate(synthetic_library):
    a = FactorDiversificationAnalyzer(synthetic_library["library"],
                                      cache_dir=synthetic_library["cache_dir"])
    a.load()
    subset = a.diversified_subset(top_n=3, max_corr=0.7)
    ids = {item["factor_id"] for item in subset}
    assert "fid_a" in ids
    assert "fid_b" not in ids  # too correlated with A
    assert "fid_c" in ids
    assert len(subset) == 2


def test_diversified_subset_respects_top_n(synthetic_library):
    a = FactorDiversificationAnalyzer(synthetic_library["library"],
                                      cache_dir=synthetic_library["cache_dir"])
    a.load()
    subset = a.diversified_subset(top_n=1, max_corr=0.7)
    assert len(subset) == 1
    assert subset[0]["factor_id"] == "fid_a"


def test_clusters_group_correlated_factors(synthetic_library):
    a = FactorDiversificationAnalyzer(synthetic_library["library"],
                                      cache_dir=synthetic_library["cache_dir"])
    a.load()
    clusters = a.cluster(distance_threshold=0.3)
    assert clusters["fid_a"] == clusters["fid_b"]
    assert clusters["fid_a"] != clusters["fid_c"]


def test_report_shape(synthetic_library):
    a = FactorDiversificationAnalyzer(synthetic_library["library"],
                                      cache_dir=synthetic_library["cache_dir"])
    a.load()
    report = a.report(top_n=3, max_corr=0.7, redundancy_threshold=0.9)
    assert report["summary"]["total_factors"] == 3
    assert report["summary"]["factors_with_values"] == 3
    assert report["summary"]["redundant_pairs"] == 1
    assert "correlation_matrix" in report
    assert "diversified_subset" in report


def test_write_subset_library_round_trip(synthetic_library, tmp_path):
    a = FactorDiversificationAnalyzer(synthetic_library["library"],
                                      cache_dir=synthetic_library["cache_dir"])
    a.load()
    subset = a.diversified_subset(top_n=3, max_corr=0.7)
    out_path = tmp_path / "diversified.json"
    a.write_subset_library(out_path, subset)

    written = json.loads(out_path.read_text())
    assert written["metadata"]["derivation"] == "diversified_subset"
    assert set(written["factors"].keys()) == {item["factor_id"] for item in subset}


def test_load_handles_missing_cache(tmp_path):
    factors_meta = {
        "fid_x": {"factor_name": "alpha_x", "factor_expression": "$close",
                   "ic": 0.05, "rank_ic": 0.06},
    }
    lib_path, cache_dir = _build_library(tmp_path, factors_meta, panels={})
    a = FactorDiversificationAnalyzer(lib_path, cache_dir=cache_dir)
    n = a.load()
    assert n == 0
    assert len(a.records) == 1
    matrix = a.correlation_matrix()
    assert matrix.empty or matrix.shape == (0, 0)


def test_load_raises_on_missing_library(tmp_path):
    a = FactorDiversificationAnalyzer(tmp_path / "nope.json")
    with pytest.raises(FileNotFoundError):
        a.load()
