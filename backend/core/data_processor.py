from typing import Any

import numpy as np
import pandas as pd
from scipy import stats


class DataProcessor:
    @staticmethod
    def statistical_summary(df: pd.DataFrame) -> dict:
        result: dict[str, Any] = {
            "shape": {"rows": len(df), "columns": len(df.columns)},
            "columns": {},
            "missing_values": {},
            "duplicates": int(df.duplicated().sum()),
        }

        for col in df.columns:
            series = df[col]
            missing = int(series.isna().sum())
            result["missing_values"][col] = missing

            if pd.api.types.is_numeric_dtype(series):
                clean = series.dropna()
                result["columns"][col] = {
                    "type": "numeric",
                    "mean": round(float(clean.mean()), 4) if len(clean) else None,
                    "median": round(float(clean.median()), 4) if len(clean) else None,
                    "std": round(float(clean.std()), 4) if len(clean) else None,
                    "min": round(float(clean.min()), 4) if len(clean) else None,
                    "max": round(float(clean.max()), 4) if len(clean) else None,
                    "q25": round(float(clean.quantile(0.25)), 4) if len(clean) else None,
                    "q75": round(float(clean.quantile(0.75)), 4) if len(clean) else None,
                    "skewness": round(float(clean.skew()), 4) if len(clean) > 1 else None,
                    "missing": missing,
                }
            elif pd.api.types.is_datetime64_any_dtype(series):
                clean = series.dropna()
                result["columns"][col] = {
                    "type": "datetime",
                    "min": str(clean.min()) if len(clean) else None,
                    "max": str(clean.max()) if len(clean) else None,
                    "range_days": int((clean.max() - clean.min()).days) if len(clean) > 1 else 0,
                    "missing": missing,
                }
            else:
                result["columns"][col] = {
                    "type": "categorical",
                    "unique_values": int(series.nunique()),
                    "top_values": series.value_counts().head(5).to_dict(),
                    "missing": missing,
                }

        return result

    @staticmethod
    def detect_anomalies(df: pd.DataFrame, method: str = "iqr") -> dict:
        anomalies: dict[str, Any] = {}
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

        for col in numeric_cols:
            series = df[col].dropna()
            if len(series) < 4:
                continue

            if method == "iqr":
                q1, q3 = series.quantile(0.25), series.quantile(0.75)
                iqr = q3 - q1
                lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
                mask = (df[col] < lower) | (df[col] > upper)
            else:
                z_scores = np.abs(stats.zscore(series))
                outlier_indices = series.index[z_scores > 3]
                mask = df.index.isin(outlier_indices)
                lower = float(series.mean() - 3 * series.std())
                upper = float(series.mean() + 3 * series.std())

            outliers = df[mask][col]
            if len(outliers) > 0:
                anomalies[col] = {
                    "count": int(len(outliers)),
                    "percentage": round(100 * len(outliers) / len(df), 2),
                    "values": outliers.head(10).tolist(),
                    "lower_bound": round(float(lower), 4),
                    "upper_bound": round(float(upper), 4),
                    "indices": outliers.index.tolist()[:10],
                }

        return {"method": method, "anomalies": anomalies, "columns_checked": numeric_cols}

    @staticmethod
    def correlation_matrix(df: pd.DataFrame) -> dict:
        numeric_df = df.select_dtypes(include=[np.number])
        if len(numeric_df.columns) < 2:
            return {"error": "Need at least 2 numeric columns for correlation"}

        corr = numeric_df.corr()
        return {
            "columns": corr.columns.tolist(),
            "matrix": corr.values.tolist(),
            "strong_correlations": DataProcessor._find_strong_correlations(corr),
        }

    @staticmethod
    def _find_strong_correlations(corr: pd.DataFrame, threshold: float = 0.7) -> list[dict]:
        pairs = []
        cols = corr.columns.tolist()
        for i in range(len(cols)):
            for j in range(i + 1, len(cols)):
                val = corr.iloc[i, j]
                if abs(val) >= threshold:
                    pairs.append({
                        "col1": cols[i],
                        "col2": cols[j],
                        "correlation": round(float(val), 4),
                        "strength": "strong" if abs(val) >= 0.9 else "moderate",
                    })
        return sorted(pairs, key=lambda x: abs(x["correlation"]), reverse=True)

    @staticmethod
    def data_quality_report(df: pd.DataFrame) -> dict:
        total = len(df)
        return {
            "total_rows": total,
            "total_columns": len(df.columns),
            "complete_rows": int((~df.isna().any(axis=1)).sum()),
            "duplicate_rows": int(df.duplicated().sum()),
            "missing_by_column": {
                col: {
                    "count": int(df[col].isna().sum()),
                    "pct": round(100 * df[col].isna().mean(), 2),
                }
                for col in df.columns
            },
            "column_types": df.dtypes.astype(str).to_dict(),
            "memory_usage_kb": round(df.memory_usage(deep=True).sum() / 1024, 2),
        }

    @staticmethod
    def time_series_analysis(df: pd.DataFrame, date_col: str, value_col: str) -> dict:
        from statsmodels.tsa.seasonal import seasonal_decompose

        df = df[[date_col, value_col]].copy()
        df[date_col] = pd.to_datetime(df[date_col])
        df = df.sort_values(date_col).set_index(date_col)
        series = df[value_col].dropna()

        result: dict[str, Any] = {
            "date_column": date_col,
            "value_column": value_col,
            "start": str(series.index.min()),
            "end": str(series.index.max()),
            "periods": len(series),
        }

        if len(series) >= 8:
            try:
                period = min(12, len(series) // 2)
                decomp = seasonal_decompose(series, model="additive", period=period)
                result["trend"] = {
                    "dates": [str(d) for d in decomp.trend.dropna().index],
                    "values": decomp.trend.dropna().tolist(),
                }
                result["seasonal"] = {
                    "dates": [str(d) for d in decomp.seasonal.dropna().index],
                    "values": decomp.seasonal.dropna().tolist(),
                }
                result["residual"] = {
                    "dates": [str(d) for d in decomp.resid.dropna().index],
                    "values": decomp.resid.dropna().tolist(),
                }
            except Exception as e:
                result["decomposition_error"] = str(e)

        return result

    @staticmethod
    def run_prediction(
        df: pd.DataFrame,
        target_col: str,
        feature_cols: list[str],
        task: str = "regression",
    ) -> dict:
        from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
        from sklearn.metrics import (
            accuracy_score,
            mean_absolute_error,
            mean_squared_error,
            r2_score,
        )
        from sklearn.model_selection import train_test_split
        from sklearn.preprocessing import LabelEncoder

        df_clean = df[feature_cols + [target_col]].dropna()
        X = df_clean[feature_cols].copy()
        y = df_clean[target_col].copy()

        # Encode categoricals
        encoders: dict[str, LabelEncoder] = {}
        for col in X.select_dtypes(include="object").columns:
            le = LabelEncoder()
            X[col] = le.fit_transform(X[col].astype(str))
            encoders[col] = le

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        if task == "classification":
            le_target = LabelEncoder()
            y_train_enc = le_target.fit_transform(y_train)
            y_test_enc = le_target.transform(y_test)
            model = GradientBoostingClassifier(n_estimators=100, random_state=42)
            model.fit(X_train, y_train_enc)
            preds = model.predict(X_test)
            metrics = {"accuracy": round(float(accuracy_score(y_test_enc, preds)), 4)}
        else:
            model = GradientBoostingRegressor(n_estimators=100, random_state=42)
            model.fit(X_train, y_train)
            preds = model.predict(X_test)
            metrics = {
                "r2": round(float(r2_score(y_test, preds)), 4),
                "mae": round(float(mean_absolute_error(y_test, preds)), 4),
                "rmse": round(float(mean_squared_error(y_test, preds) ** 0.5), 4),
            }

        importances = dict(zip(feature_cols, model.feature_importances_.tolist()))
        importances = dict(sorted(importances.items(), key=lambda x: x[1], reverse=True))

        return {
            "task": task,
            "target": target_col,
            "features": feature_cols,
            "train_samples": len(X_train),
            "test_samples": len(X_test),
            "metrics": metrics,
            "feature_importances": importances,
        }
