from __future__ import annotations

from pathlib import Path
import numpy as np
# pyright: reportMissingImports=false
import pandas as pd  # type: ignore[reportMissingModuleSource]

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "raw" / "olist_order_analysis_export.csv"
CLEAN = ROOT / "data" / "processed" / "olist_order_analysis_cleaned.csv"
MISSING_REPORT = ROOT / "outputs" / "missing_values_before.csv"
OUTLIER_REPORT = ROOT / "outputs" / "outlier_audit.csv"
SUMMARY = ROOT / "outputs" / "cleaning_summary.txt"

ID_COLUMNS = {"order_id", "customer_unique_id"}
FLAG_COLUMNS = {"has_review_comment"}
DATE_COLUMNS = {
    "order_purchase_timestamp", "order_approved_at",
    "order_delivered_customer_date", "order_estimated_delivery_date",
}


def zscore(series: pd.Series) -> np.ndarray:
    mean = series.mean()
    std = series.std(ddof=0)
    if std == 0 or np.isnan(std):
        return np.zeros(len(series), dtype=float)
    return (series - mean) / std


def choose_continuous_columns(df: pd.DataFrame) -> tuple[list[str], dict[str, str]]:
    selected: list[str] = []
    excluded: dict[str, str] = {}
    for col in df.select_dtypes(include=np.number).columns:
        series = df[col].dropna()
        if col in ID_COLUMNS:
            excluded[col] = "identifier/key"
        elif col in FLAG_COLUMNS or series.nunique() <= 2:
            excluded[col] = "binary/flag"
        elif series.nunique() <= 5:
            excluded[col] = "low-cardinality discrete measure"
        elif series.var(ddof=0) < 1e-12:
            excluded[col] = "zero or near-zero variance"
        else:
            selected.append(col)
    return selected, excluded


def main() -> None:
    for path in [CLEAN.parent, MISSING_REPORT.parent]:
        path.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(INPUT)
    rows_initial = len(df)

    for col in DATE_COLUMNS.intersection(df.columns):
        df[col] = pd.to_datetime(df[col], errors="coerce")

    missing = pd.DataFrame({
        "column": df.columns,
        "missing_count": [int(df[c].isna().sum()) for c in df.columns],
        "missing_percentage": [round(float(df[c].isna().mean() * 100), 4) for c in df.columns],
    })
    missing.to_csv(MISSING_REPORT, index=False)

    duplicate_count = int(df.duplicated().sum())
    df = df.drop_duplicates().copy()
    rows_after_duplicates = len(df)

    # Numeric imputation uses median because order-value and delivery variables are skewed
    # and contain genuine high-value extremes. The median is robust to those outliers.
    numeric_cols = df.select_dtypes(include=np.number).columns
    for col in numeric_cols:
        median = df[col].median()
        df[col] = df[col].fillna(median if pd.notna(median) else 0)

    # Datetimes are filled using the column median timestamp; categorical/text uses mode,
    # with "unknown" as a safe fallback.
    for col in DATE_COLUMNS.intersection(df.columns):
        if df[col].isna().any():
            valid = df[col].dropna().sort_values()
            fill = valid.iloc[len(valid) // 2] if not valid.empty else pd.Timestamp("1970-01-01")
            df[col] = df[col].fillna(fill)

    text_cols = df.select_dtypes(include=["object", "string"]).columns
    for col in text_cols:
        mode = df[col].mode(dropna=True)
        fill = mode.iloc[0] if not mode.empty else "unknown"
        df[col] = df[col].fillna(fill)

    selected, excluded = choose_continuous_columns(df)
    records = []
    for col in selected:
        s = pd.to_numeric(df[col], errors="coerce")
        q1, q3 = s.quantile([0.25, 0.75])
        iqr = q3 - q1
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        iqr_count = int(((s < lower) | (s > upper)).sum())
        std = s.std(ddof=0)
        if std == 0 or np.isnan(std):
            z_count = 0
        else:
            z = np.abs(zscore(s))
            z_count = int(np.sum(z > 3))
        records.append({
            "column": col,
            "q1": q1,
            "q3": q3,
            "iqr": iqr,
            "lower_fence": lower,
            "upper_fence": upper,
            "iqr_outlier_count": iqr_count,
            "zscore_outlier_count": z_count,
            "methods_agree": iqr_count == z_count,
            "difference_explanation": (
                "Counts match." if iqr_count == z_count else
                "Counts differ because IQR is rank-based and robust to skew, while Z-score uses mean and standard deviation and assumes a more symmetric distribution."
            ),
        })

    pd.DataFrame(records).to_csv(OUTLIER_REPORT, index=False)
    df.to_csv(CLEAN, index=False, date_format="%Y-%m-%d %H:%M:%S")

    remaining_missing = int(df.isna().sum().sum())
    lines = [
        f"Rows before duplicate removal: {rows_initial:,}",
        f"Duplicate rows detected: {duplicate_count:,}",
        f"Rows after duplicate removal: {rows_after_duplicates:,}",
        f"Total missing cells after imputation: {remaining_missing}",
        "Numeric imputation: median (robust to skew and outliers).",
        "Categorical/text imputation: mode; fallback literal 'unknown'.",
        "Date imputation: median observed timestamp in each date column.",
        "Continuous numeric selection rule: numeric columns excluding identifiers/keys, binary or flag columns, low-cardinality discrete measures (<=5 unique values), and zero/near-zero variance columns.",
        f"Continuous columns audited: {', '.join(selected)}",
        "Excluded numeric columns: " + "; ".join(f"{k} ({v})" for k, v in excluded.items()),
    ]
    SUMMARY.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    if remaining_missing != 0:
        raise AssertionError("Cleaning incomplete: missing values remain")


if __name__ == "__main__":
    main()
