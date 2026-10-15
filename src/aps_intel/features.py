"""Fold-safe feature engineering: every statistic is learned inside fit()."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin

DROP = ("cd_000",)  # constant in training (audit)


def histogram_groups(columns) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    for column in columns:
        groups.setdefault(column.split("_")[0], []).append(column)
    return {k: sorted(v) for k, v in groups.items() if len(v) > 1}


class APSFeatures(BaseEstimator, TransformerMixin):
    """Drop constants; optional missing-value indicators and histogram aggregates.

    Missing values are kept as NaN (tree models handle them natively); linear
    models add an imputer afterwards. Indicators are created only for columns
    that had missing values in the training fold.
    """

    def __init__(self, indicators: bool = False, histograms: bool = False):
        self.indicators = indicators
        self.histograms = histograms

    def fit(self, X: pd.DataFrame, y=None):
        X = X.drop(columns=[c for c in DROP if c in X.columns])
        self.columns_ = list(X.columns)
        self.missing_columns_ = [c for c in self.columns_ if X[c].isna().any()]
        self.groups_ = histogram_groups(self.columns_)
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        out = X[self.columns_].copy()
        parts = [out]
        if self.indicators:
            parts.append(out[self.missing_columns_].isna().astype(float).add_suffix("_isna"))
        if self.histograms:
            agg = {}
            for name, cols in self.groups_.items():
                total = out[cols].sum(axis=1, min_count=1)
                agg[f"{name}_hist_total"] = total
                share = out[cols].div(total.replace(0, np.nan), axis=0)
                agg[f"{name}_hist_top_share"] = share.max(axis=1)
                centers = np.arange(len(cols), dtype=float)
                agg[f"{name}_hist_mean_bin"] = (share * centers).sum(axis=1, min_count=1)
            parts.append(pd.DataFrame(agg, index=out.index))
        result = pd.concat(parts, axis=1)
        result["n_missing"] = out.isna().sum(axis=1).astype(float)
        return result
