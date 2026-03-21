import json
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor

from app.reporting import build_pdf_report
from app.llm import generate_llm_summary


@dataclass
class AnalysisResult:
    overview: Dict
    summary: str
    modeling: Dict
    warnings: List[str]


def _read_csv(csv_path: str) -> pd.DataFrame:
    try:
        return pd.read_csv(csv_path, encoding="utf-8")
    except UnicodeDecodeError:
        return pd.read_csv(csv_path, encoding="latin-1")


def _basic_cleaning(df: pd.DataFrame) -> pd.DataFrame:
    cleaned = df.copy()
    cleaned.columns = [str(c).strip() for c in cleaned.columns]
    cleaned = cleaned.replace(r"^\s*$", np.nan, regex=True)
    cleaned = cleaned.drop_duplicates()
    return cleaned


def _split_columns(df: pd.DataFrame) -> Tuple[List[str], List[str]]:
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = [c for c in df.columns if c not in numeric_cols]
    return numeric_cols, categorical_cols


def _safe_value_counts(series: pd.Series, limit: int = 5) -> List[Dict]:
    counts = series.value_counts(dropna=False).head(limit)
    return [{"value": str(idx), "count": int(val)} for idx, val in counts.items()]


def _describe_numeric(df: pd.DataFrame, numeric_cols: List[str]) -> Dict:
    if not numeric_cols:
        return {}
    desc = df[numeric_cols].describe().T
    desc["missing"] = df[numeric_cols].isna().sum()
    return json.loads(desc.reset_index().to_json(orient="records"))


def _column_summary(df: pd.DataFrame) -> List[Dict]:
    summaries = []
    for col in df.columns:
        series = df[col]
        summaries.append(
            {
                "name": col,
                "dtype": str(series.dtype),
                "missing": int(series.isna().sum()),
                "unique": int(series.nunique(dropna=True)),
                "example": "" if series.dropna().empty else str(series.dropna().iloc[0]),
            }
        )
    return summaries


def _plot_histograms(df: pd.DataFrame, numeric_cols: List[str], out_dir: str) -> List[str]:
    paths = []
    for col in numeric_cols[:5]:
        if df[col].dropna().empty:
            continue
        fig, ax = plt.subplots(figsize=(6, 4))
        sns.histplot(df[col].dropna(), kde=True, ax=ax, color="#355C7D")
        ax.set_title(f"Distribution of {col}")
        ax.set_xlabel(col)
        ax.set_ylabel("Count")
        path = os.path.join(out_dir, f"hist_{col}.png")
        fig.tight_layout()
        fig.savefig(path, dpi=150)
        plt.close(fig)
        paths.append(path)
    return paths


def _plot_correlation(df: pd.DataFrame, numeric_cols: List[str], out_dir: str) -> Optional[str]:
    if len(numeric_cols) < 2:
        return None
    fig, ax = plt.subplots(figsize=(6, 5))
    corr = df[numeric_cols].corr().fillna(0.0)
    sns.heatmap(corr, ax=ax, cmap="vlag", center=0, square=True)
    ax.set_title("Correlation Heatmap")
    path = os.path.join(out_dir, "correlation.png")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def _plot_target_relationships(
    df: pd.DataFrame,
    target: str,
    numeric_cols: List[str],
    categorical_cols: List[str],
    out_dir: str,
) -> List[str]:
    if target not in df.columns:
        return []
    paths = []
    if target in numeric_cols:
        for col in [c for c in numeric_cols if c != target][:3]:
            if df[col].dropna().empty or df[target].dropna().empty:
                continue
            fig, ax = plt.subplots(figsize=(6, 4))
            sns.scatterplot(x=df[col], y=df[target], ax=ax, color="#6C5B7B")
            ax.set_title(f"{col} vs {target}")
            path = os.path.join(out_dir, f"scatter_{col}_vs_{target}.png")
            fig.tight_layout()
            fig.savefig(path, dpi=150)
            plt.close(fig)
            paths.append(path)
    else:
        for col in numeric_cols[:3]:
            if df[col].dropna().empty:
                continue
            fig, ax = plt.subplots(figsize=(6, 4))
            sns.boxplot(x=df[target], y=df[col], ax=ax, palette="coolwarm")
            ax.set_title(f"{col} by {target}")
            path = os.path.join(out_dir, f"box_{col}_by_{target}.png")
            fig.tight_layout()
            fig.savefig(path, dpi=150)
            plt.close(fig)
            paths.append(path)
    if target in categorical_cols:
        fig, ax = plt.subplots(figsize=(6, 4))
        df[target].value_counts().head(10).plot(kind="bar", ax=ax, color="#F67280")
        ax.set_title(f"{target} value counts")
        ax.set_ylabel("Count")
        path = os.path.join(out_dir, f"bar_{target}.png")
        fig.tight_layout()
        fig.savefig(path, dpi=150)
        plt.close(fig)
        paths.append(path)
    return paths


def _auto_task_type(df: pd.DataFrame, target: str) -> Optional[str]:
    if target not in df.columns:
        return None
    unique = df[target].dropna().nunique()
    if pd.api.types.is_numeric_dtype(df[target]) and unique > 10:
        return "regression"
    if unique <= 20:
        return "classification"
    return "regression"


def _model_with_target(
    df: pd.DataFrame,
    target: str,
    task_type: str,
) -> Dict:
    if target not in df.columns:
        return {"status": "skipped", "reason": "Target column not found."}

    data = df.dropna(subset=[target])
    if data.shape[0] < 20:
        return {"status": "skipped", "reason": "Not enough rows for modeling."}

    numeric_cols, categorical_cols = _split_columns(data.drop(columns=[target]))
    X = data.drop(columns=[target])
    y = data[target]

    if task_type == "classification" and y.nunique() < 2:
        return {"status": "skipped", "reason": "Target has only one class."}

    numeric_transformer = Pipeline(
        steps=[("imputer", SimpleImputer(strategy="median"))]
    )
    categorical_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, numeric_cols),
            ("cat", categorical_transformer, categorical_cols),
        ],
        remainder="drop",
    )

    if task_type == "classification":
        model = RandomForestClassifier(n_estimators=200, random_state=42)
    else:
        model = RandomForestRegressor(n_estimators=200, random_state=42)

    clf = Pipeline(steps=[("preprocessor", preprocessor), ("model", model)])

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    clf.fit(X_train, y_train)
    preds = clf.predict(X_test)

    if task_type == "classification":
        metrics = {
            "accuracy": float(accuracy_score(y_test, preds)),
            "f1": float(
                f1_score(y_test, preds, average="weighted", zero_division=0)
            ),
        }
    else:
        metrics = {
            "r2": float(r2_score(y_test, preds)),
            "mae": float(mean_absolute_error(y_test, preds)),
        }

    return {
        "status": "completed",
        "task_type": task_type,
        "metrics": metrics,
        "train_rows": int(X_train.shape[0]),
        "test_rows": int(X_test.shape[0]),
    }


def _cluster_numeric(df: pd.DataFrame, numeric_cols: List[str]) -> Dict:
    if len(numeric_cols) < 2:
        return {"status": "skipped", "reason": "Not enough numeric columns."}
    numeric_df = df[numeric_cols].dropna()
    if numeric_df.shape[0] < 20:
        return {"status": "skipped", "reason": "Not enough rows for clustering."}
    k = min(4, max(2, numeric_df.shape[0] // 50))
    model = KMeans(n_clusters=k, n_init=10, random_state=42)
    labels = model.fit_predict(numeric_df)
    cluster_sizes = pd.Series(labels).value_counts().sort_index().to_dict()
    return {
        "status": "completed",
        "clusters": {f"cluster_{k}": int(v) for k, v in cluster_sizes.items()},
    }


def run_analysis(
    csv_path: str,
    output_dir: str,
    api_key: str,
    target: Optional[str] = None,
    task_type: Optional[str] = None,
) -> Dict:
    warnings: List[str] = []
    df_raw = _read_csv(csv_path)
    df = _basic_cleaning(df_raw)

    if df.shape[0] == 0:
        raise ValueError("CSV contains no rows after cleaning.")

    numeric_cols, categorical_cols = _split_columns(df)

    overview = {
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "duplicate_rows_removed": int(df_raw.shape[0] - df.shape[0]),
        "missing_total": int(df.isna().sum().sum()),
        "numeric_columns": len(numeric_cols),
        "categorical_columns": len(categorical_cols),
    }

    column_summary = _column_summary(df)
    numeric_stats = _describe_numeric(df, numeric_cols)
    categorical_preview = {
        col: _safe_value_counts(df[col])
        for col in categorical_cols[:5]
    }

    fig_dir = os.path.join(output_dir, "figures")
    os.makedirs(fig_dir, exist_ok=True)

    figs = []
    figs += _plot_histograms(df, numeric_cols, fig_dir)
    corr_path = _plot_correlation(df, numeric_cols, fig_dir)
    if corr_path:
        figs.append(corr_path)
    if target:
        figs += _plot_target_relationships(
            df, target, numeric_cols, categorical_cols, fig_dir
        )

    modeling: Dict = {"status": "skipped"}
    if target:
        resolved_task = task_type or _auto_task_type(df, target)
        if not resolved_task:
            modeling = {
                "status": "skipped",
                "reason": "Target column not found.",
            }
        else:
            modeling = _model_with_target(df, target, resolved_task)
    else:
        modeling = _cluster_numeric(df, numeric_cols)

    llm_context = {
        "overview": overview,
        "numeric_stats": numeric_stats[:5],
        "categorical_preview": categorical_preview,
        "modeling": modeling,
    }

    summary = ""
    if api_key and api_key.strip():
        summary = generate_llm_summary(api_key, llm_context)
    else:
        warnings.append("LLM summary skipped: missing API key.")
    if not summary:
        warnings.append("LLM summary unavailable. Using heuristic summary.")
        summary = (
            f"Dataset has {overview['rows']} rows and {overview['columns']} columns. "
            f"Missing values: {overview['missing_total']}. "
            f"Modeling status: {modeling.get('status', 'skipped')}."
        )

    report_path = os.path.join(output_dir, "report.pdf")
    build_pdf_report(
        report_path=report_path,
        overview=overview,
        column_summary=column_summary,
        numeric_stats=numeric_stats,
        categorical_preview=categorical_preview,
        modeling=modeling,
        figures=figs,
        summary=summary,
    )

    return AnalysisResult(
        overview=overview,
        summary=summary,
        modeling=modeling,
        warnings=warnings,
    ).__dict__
