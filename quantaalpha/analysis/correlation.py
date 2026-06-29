"""
Correlation / diversification analysis for the factor library.

Mining tends to produce many similar factors (lots of variants of the
same idea). Combining all of them in one basket is wasteful, since
correlated factors don't add diversification.

Workflow:
    a = FactorDiversificationAnalyzer("all_factors_library.json")
    a.load()
    report = a.report(top_n=20, max_corr=0.7)
"""

import hashlib
import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


DEFAULT_FACTOR_CACHE_DIR = os.environ.get(
    "FACTOR_CACHE_DIR",
    "data/results/factor_cache",
)


# Backtest-result keys can drift between mining runs, so try a few.
IC_KEYS = (
    "IC",
    "Rank IC",
    "rank_ic",
    "1day.excess_return_without_cost.information_coefficient",
    "1day.excess_return_without_cost.rank_ic",
)


def _extract_ic(backtest_results):
    """Return (IC, Rank IC) from a backtest dict."""
    ic = 0.0
    rank_ic = 0.0
    for key in IC_KEYS:
        if key not in backtest_results:
            continue
        v = backtest_results[key]
        if v is None:
            continue
        try:
            v = float(v)
        except (TypeError, ValueError):
            continue
        if "rank" in key.lower():
            if rank_ic == 0.0:
                rank_ic = v
        else:
            if ic == 0.0:
                ic = v
    return ic, rank_ic


@dataclass
class FactorRecord:
    factor_id: str
    factor_name: str
    factor_expression: str
    ic: float = 0.0
    rank_ic: float = 0.0
    values: Optional[pd.Series] = None
    meta: dict = field(default_factory=dict)

    @property
    def score(self):
        # Prefer rank IC when present, fall back to IC, fall back to 0.
        if self.rank_ic and not np.isnan(self.rank_ic):
            return abs(float(self.rank_ic))
        if self.ic and not np.isnan(self.ic):
            return abs(float(self.ic))
        return 0.0


class FactorDiversificationAnalyzer:
    def __init__(self, library_path, cache_dir=None):
        self.library_path = Path(library_path)
        self.cache_dir = Path(cache_dir or DEFAULT_FACTOR_CACHE_DIR)
        self.records: List[FactorRecord] = []
        self._corr_matrix: Optional[pd.DataFrame] = None

    def load(self, max_factors=None):
        """Read library JSON and pull cached factor values when present.

        Returns the count of factors that have usable values; the rest
        are still kept (useful for ranking) but excluded from corr.
        """
        if not self.library_path.exists():
            raise FileNotFoundError(f"Factor library not found: {self.library_path}")

        with open(self.library_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        factors = data.get("factors", {}) or {}
        loaded_with_values = 0

        for fid, info in factors.items():
            expr = info.get("factor_expression", "") or ""
            ic, rank_ic = _extract_ic(info.get("backtest_results", {}) or {})

            md = info.get("metadata", {}) or {}
            rec = FactorRecord(
                factor_id=fid,
                factor_name=info.get("factor_name", fid) or fid,
                factor_expression=expr,
                ic=ic,
                rank_ic=rank_ic,
                meta={
                    "round": md.get("round_number"),
                    "trajectory_id": md.get("trajectory_id"),
                    "evolution_phase": md.get("evolution_phase"),
                },
            )
            rec.values = self._load_values(expr, info.get("cache_location") or {})
            if rec.values is not None:
                loaded_with_values += 1

            self.records.append(rec)
            if max_factors is not None and len(self.records) >= max_factors:
                break

        logger.info(
            "Loaded %d factors from %s (%d with cached values)",
            len(self.records), self.library_path.name, loaded_with_values,
        )
        return loaded_with_values

    def _load_values(self, expr, cache_location):
        # Try MD5 pickle first (fast, written by FactorLibraryManager).
        if expr:
            md5_key = hashlib.md5(expr.encode()).hexdigest()
            pkl = self.cache_dir / f"{md5_key}.pkl"
            if pkl.exists():
                try:
                    return _coerce_series(pd.read_pickle(pkl))
                except Exception as e:
                    logger.debug("Failed reading %s: %s", pkl, e)

        # Fall back to result.h5 if the library entry points at one.
        h5_path = cache_location.get("result_h5_path") if cache_location else None
        if h5_path and Path(h5_path).exists():
            try:
                return _coerce_series(pd.read_hdf(h5_path))
            except Exception as e:
                logger.debug("Failed reading %s: %s", h5_path, e)
        return None

    def correlation_matrix(self, min_overlap=30):
        """Pairwise mean cross-sectional Spearman corr.

        Pairs without enough overlap come back as NaN; callers should
        treat NaN as unknown rather than zero.
        """
        if self._corr_matrix is not None:
            return self._corr_matrix

        usable = [r for r in self.records if r.values is not None]
        if len(usable) < 2:
            self._corr_matrix = pd.DataFrame(
                np.eye(len(usable)),
                index=[r.factor_id for r in usable],
                columns=[r.factor_id for r in usable],
                dtype=float,
            )
            return self._corr_matrix

        panels = {}
        for r in usable:
            try:
                panels[r.factor_id] = _to_panel(r.values)
            except Exception as e:
                logger.debug("Skip %s: %s", r.factor_name, e)

        ids = [r.factor_id for r in usable if r.factor_id in panels]
        m = pd.DataFrame(np.eye(len(ids)), index=ids, columns=ids, dtype=float)
        for i, a in enumerate(ids):
            pa = panels[a]
            for j in range(i + 1, len(ids)):
                b = ids[j]
                c = _mean_xs_rank_corr(pa, panels[b], min_overlap=min_overlap)
                m.iat[i, j] = c
                m.iat[j, i] = c

        self._corr_matrix = m
        return m

    def redundant_pairs(self, threshold=0.9):
        m = self.correlation_matrix()
        out = []
        ids = list(m.index)
        for i, a in enumerate(ids):
            for j in range(i + 1, len(ids)):
                b = ids[j]
                c = m.iat[i, j]
                if pd.isna(c):
                    continue
                if abs(c) >= threshold:
                    out.append({
                        "factor_a": a,
                        "factor_b": b,
                        "factor_a_name": self._name(a),
                        "factor_b_name": self._name(b),
                        "correlation": round(float(c), 6),
                    })
        out.sort(key=lambda d: abs(d["correlation"]), reverse=True)
        return out

    def cluster(self, n_clusters=None, distance_threshold=0.3):
        """Group factors by 1 - |corr| with agglomerative clustering."""
        from sklearn.cluster import AgglomerativeClustering

        m = self.correlation_matrix()
        if len(m) < 2:
            return {fid: 0 for fid in m.index}

        d = 1.0 - m.abs().fillna(1.0)
        np.fill_diagonal(d.values, 0.0)

        kwargs = {"metric": "precomputed", "linkage": "average"}
        if n_clusters is not None:
            kwargs["n_clusters"] = n_clusters
        else:
            kwargs["n_clusters"] = None
            kwargs["distance_threshold"] = distance_threshold

        labels = AgglomerativeClustering(**kwargs).fit_predict(d.values)
        return dict(zip(m.index, (int(x) for x in labels)))

    def diversified_subset(self, top_n=20, max_corr=0.7, lambda_penalty=0.5):
        """Greedy pick: highest-scoring factors that aren't too correlated
        with anything already in the set.
        """
        if not self.records:
            return []

        candidates = sorted(self.records, key=lambda r: r.score, reverse=True)

        # If everything has zero IC, just hand back the top-N by name.
        if not candidates or candidates[0].score == 0.0:
            logger.warning("No factors with non-zero IC; returning top-N as-is")
            return [self._summarize(r, 0.0) for r in candidates[:top_n]]

        m = self.correlation_matrix()
        in_matrix = set(m.index)

        selected: List[FactorRecord] = []
        for cand in candidates:
            if len(selected) >= top_n:
                break

            if not selected:
                selected.append(cand)
                continue

            # Factor without cached values can only fill the tail.
            if cand.factor_id not in in_matrix:
                if len(selected) >= int(0.75 * top_n):
                    selected.append(cand)
                continue

            corrs = []
            for s in selected:
                if s.factor_id not in in_matrix:
                    continue
                c = m.at[cand.factor_id, s.factor_id]
                if not pd.isna(c):
                    corrs.append(abs(float(c)))

            max_c = max(corrs) if corrs else 0.0
            if max_c >= max_corr:
                continue

            # lambda_penalty kept for future scoring tweaks; gate above is what filters.
            _ = cand.score - lambda_penalty * max_c
            selected.append(cand)

        out = []
        for r in selected:
            mc = self._max_corr_against(r, selected, m)
            out.append(self._summarize(r, mc))
        return out

    def report(self, top_n=20, max_corr=0.7, redundancy_threshold=0.9):
        matrix = self.correlation_matrix()
        clusters = self.cluster() if len(matrix) >= 2 else {}
        redundant = self.redundant_pairs(threshold=redundancy_threshold)
        subset = self.diversified_subset(top_n=top_n, max_corr=max_corr)

        n_with_values = sum(1 for r in self.records if r.values is not None)
        return {
            "library": str(self.library_path),
            "summary": {
                "total_factors": len(self.records),
                "factors_with_values": n_with_values,
                "redundant_pairs": len(redundant),
                "n_clusters": (max(clusters.values()) + 1) if clusters else 0,
                "diversified_subset_size": len(subset),
            },
            "redundant_pairs": redundant,
            "clusters": clusters,
            "diversified_subset": subset,
            "correlation_matrix": _matrix_to_records(matrix),
        }

    def write_subset_library(self, output_path, subset):
        """Write a factor-library JSON with only the picked factors.

        The output is in the same format the mining loop produces, so
        run_backtest.py can take it via --factor-json directly.
        """
        with open(self.library_path, "r", encoding="utf-8") as f:
            original = json.load(f)

        keep = {item["factor_id"] for item in subset}
        out = {
            "metadata": {
                **(original.get("metadata") or {}),
                "derived_from": str(self.library_path),
                "derivation": "diversified_subset",
                "total_factors": len(keep),
            },
            "factors": {
                fid: info
                for fid, info in (original.get("factors") or {}).items()
                if fid in keep
            },
        }
        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2, default=str)
        logger.info("Wrote diversified subset (%d factors) to %s", len(keep), out_path)
        return out_path

    def _name(self, factor_id):
        for r in self.records:
            if r.factor_id == factor_id:
                return r.factor_name
        return factor_id

    @staticmethod
    def _max_corr_against(rec, others, matrix):
        if rec.factor_id not in matrix.index:
            return 0.0
        vals = []
        for s in others:
            if s.factor_id == rec.factor_id or s.factor_id not in matrix.index:
                continue
            c = matrix.at[rec.factor_id, s.factor_id]
            if not pd.isna(c):
                vals.append(abs(float(c)))
        return float(max(vals)) if vals else 0.0

    @staticmethod
    def _summarize(rec, max_corr_with_selected):
        return {
            "factor_id": rec.factor_id,
            "factor_name": rec.factor_name,
            "factor_expression": rec.factor_expression,
            "ic": round(float(rec.ic), 6) if rec.ic else 0.0,
            "rank_ic": round(float(rec.rank_ic), 6) if rec.rank_ic else 0.0,
            "score": round(rec.score, 6),
            "max_corr_with_selected": round(float(max_corr_with_selected), 6),
            "metadata": rec.meta,
        }


def _coerce_series(obj):
    """Cache files might be a Series, single-column DataFrame, or wide panel."""
    if isinstance(obj, pd.Series):
        return obj
    if isinstance(obj, pd.DataFrame):
        if obj.shape[1] == 1:
            return obj.iloc[:, 0]
        # wide -> stacked multi-index
        try:
            return obj.stack(future_stack=True)
        except TypeError:
            return obj.stack()
    return None


def _to_panel(values):
    """(datetime, instrument) Series -> date x instrument DataFrame."""
    if not isinstance(values.index, pd.MultiIndex):
        raise ValueError("Expected a (datetime, instrument) MultiIndex")
    return values.unstack(level=-1).sort_index()


def _mean_xs_rank_corr(a, b, min_overlap=30):
    """Mean per-date Spearman corr across overlapping dates/instruments."""
    common_dates = a.index.intersection(b.index)
    if len(common_dates) == 0:
        return float("nan")
    common_cols = a.columns.intersection(b.columns)
    if len(common_cols) < 3:
        return float("nan")

    a = a.loc[common_dates, common_cols]
    b = b.loc[common_dates, common_cols]

    # Spearman = Pearson on per-row ranks
    ar = a.rank(axis=1, method="average")
    br = b.rank(axis=1, method="average")

    arc = ar.sub(ar.mean(axis=1), axis=0)
    brc = br.sub(br.mean(axis=1), axis=0)
    num = (arc * brc).sum(axis=1)
    den = np.sqrt((arc ** 2).sum(axis=1) * (brc ** 2).sum(axis=1))

    with np.errstate(invalid="ignore", divide="ignore"):
        per_date = num / den.replace(0, np.nan)

    valid = per_date.dropna()
    if len(valid) < min_overlap:
        return float("nan")
    return float(valid.mean())


def _matrix_to_records(matrix):
    if matrix.empty:
        return {"ids": [], "values": []}
    ids = list(matrix.index)
    values = [
        [None if pd.isna(x) else round(float(x), 6) for x in row]
        for row in matrix.values
    ]
    return {"ids": ids, "values": values}
