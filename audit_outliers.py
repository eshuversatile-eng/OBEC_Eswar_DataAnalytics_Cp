from __future__ import annotations
from pathlib import Path
import json
import numpy as np
import pandas as pd

# ============================================================
# Project paths
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_CSV = PROJECT_ROOT / "outputs" / "task7_cleaned_join_export.csv"
SELECTION_AUDIT_CSV = PROJECT_ROOT / "outputs" / "continuous_numeric_selection_audit.csv"
OUTLIER_COMPARISON_CSV = PROJECT_ROOT / "outputs" / "outlier_comparison.csv"
OUTLIER_REPORT_TXT = PROJECT_ROOT / "outputs" / "outlier_audit_report.txt"
OUTLIER_DETAILS_JSON = PROJECT_ROOT / "outputs" / "outlier_details.json"

# ============================================================
# Explicit filtering configuration
# ============================================================

# These columns are the expected numeric measures in the Olist joined export.
# Only columns that actually exist in the CSV are evaluated.
CONTINUOUS_CANDIDATE_COLUMNS = [
    "delivery_days",
    "delay_days",
    "item_count",
    "seller_count",
    "item_value",
    "freight_value",
    "freight_pct",
    "payment_value",
    "max_installments",
    "payment_record_count",
    "review_score",
]

EXPLICIT_ID_COLUMNS = {
    "customer_unique_id",
    "customer_id",
    "order_id",
    "product_id",
    "seller_id",
    "review_id",
}

# Binary/flag columns have at most two unique non-null values.
BINARY_UNIQUE_LIMIT = 2

# Near-zero variance rule: exclude a numeric column when one value represents
# at least 99.9% of its non-null observations.
NEAR_ZERO_DOMINANCE_THRESHOLD = 0.999


# ============================================================
# Data loading and preparation
# ============================================================


def load_data(file_path: Path) -> pd.DataFrame:
    """Load the cleaned CSV, normalize column names, and convert candidates."""

    if not file_path.exists():
        raise FileNotFoundError(
            f"Cleaned CSV not found:\n{file_path}\n\n"
            "Run clean_exported_csv.py before audit_outliers.py."
        )

    dataframe = pd.read_csv(file_path)

    # Remove accidental leading/trailing spaces from headers.
    dataframe.columns = dataframe.columns.str.strip()

    print("Cleaned CSV loaded successfully.")
    print(f"File: {file_path}")
    print(f"Rows: {len(dataframe):,}")
    print(f"Columns: {len(dataframe.columns)}")

    print("\nColumns found in the CSV")
    print("-" * 70)
    for column in dataframe.columns:
        print(repr(column))

    print("\nData types before numeric conversion")
    print("-" * 70)
    print(dataframe.dtypes.to_string())

    # Numeric-looking fields may be loaded as object because of mixed text,
    # commas, blanks, or previous imputation. Convert expected measures
    # explicitly; invalid text becomes NaN and is reported in the audit.
    for column in CONTINUOUS_CANDIDATE_COLUMNS:
        if column in dataframe.columns:
            cleaned_text = (
                dataframe[column]
                .astype(str)
                .str.replace(",", "", regex=False)
                .str.strip()
                .replace({"": np.nan, "unknown": np.nan, "None": np.nan})
            )
            dataframe[column] = pd.to_numeric(cleaned_text, errors="coerce")

    print("\nData types after numeric conversion")
    print("-" * 70)
    print(dataframe.dtypes.to_string())

    return dataframe


# ============================================================
# Continuous-measure selection
# ============================================================


def looks_like_identifier(column_name: str) -> bool:
    """Return True when a column name indicates an ID or key."""

    normalized = column_name.strip().lower()
    return (
        normalized in EXPLICIT_ID_COLUMNS
        or normalized == "id"
        or normalized.endswith("_id")
        or normalized.endswith("_key")
    )


def classify_numeric_columns(
    dataframe: pd.DataFrame,
) -> tuple[list[str], pd.DataFrame]:
    """Select all meaningful numeric measures using an auditable rule."""

    selected_columns: list[str] = []
    audit_rows: list[dict[str, object]] = []

    # Prefer the explicit Olist candidate list. If none of those columns are
    # present, fall back to every numeric column so the script remains useful
    # when the exported schema differs slightly.
    available_candidates = [
        column
        for column in CONTINUOUS_CANDIDATE_COLUMNS
        if column in dataframe.columns
    ]

    if not available_candidates:
        print(
            "\nWarning: none of the expected Olist candidate columns were "
            "found. Falling back to all numeric columns."
        )
        available_candidates = dataframe.select_dtypes(
            include=[np.number]
        ).columns.tolist()

    print("\nCandidate numeric columns")
    print("-" * 70)
    print(available_candidates)

    for column in available_candidates:
        series = pd.to_numeric(dataframe[column], errors="coerce")
        non_null_series = series.dropna()

        valid_numeric_rows = int(non_null_series.shape[0])
        conversion_failures = int(series.isna().sum())
        unique_count = int(non_null_series.nunique(dropna=True))

        if non_null_series.empty:
            variance = np.nan
            dominant_ratio = np.nan
        else:
            variance = float(non_null_series.var(ddof=0))
            dominant_ratio = float(
                non_null_series.value_counts(normalize=True).iloc[0]
            )

        exclusion_reason = ""

        if looks_like_identifier(column):
            exclusion_reason = "ID/key column"
        elif non_null_series.empty:
            exclusion_reason = "no valid numeric values after conversion"
        elif unique_count <= BINARY_UNIQUE_LIMIT:
            exclusion_reason = "binary/flag or two-level numeric column"
        elif pd.isna(variance) or np.isclose(variance, 0.0):
            exclusion_reason = "zero variance"
        elif dominant_ratio >= NEAR_ZERO_DOMINANCE_THRESHOLD:
            exclusion_reason = (
                "near-zero variance: one value represents "
                f"{dominant_ratio:.2%} of non-null rows"
            )
        else:
            selected_columns.append(column)

        audit_rows.append(
            {
                "column_name": column,
                "dtype_after_conversion": str(dataframe[column].dtype),
                "valid_numeric_rows": valid_numeric_rows,
                "conversion_or_missing_count": conversion_failures,
                "unique_non_null_values": unique_count,
                "variance_population": variance,
                "dominant_value_ratio": dominant_ratio,
                "selected_as_continuous_measure": exclusion_reason == "",
                "exclusion_reason": exclusion_reason,
            }
        )

    return selected_columns, pd.DataFrame(audit_rows)


# ============================================================
# Outlier calculations
# ============================================================


def calculate_iqr_outliers(series: pd.Series) -> dict[str, float | int]:
    """Compute IQR fences and count values outside the fences."""

    numeric_series = pd.to_numeric(series, errors="coerce").dropna()

    q1 = float(numeric_series.quantile(0.25))
    q3 = float(numeric_series.quantile(0.75))
    iqr = q3 - q1
    lower_fence = q1 - 1.5 * iqr
    upper_fence = q3 + 1.5 * iqr

    outlier_mask = (
        (numeric_series < lower_fence)
        | (numeric_series > upper_fence)
    )

    return {
        "q1": q1,
        "q3": q3,
        "iqr": iqr,
        "lower_fence": lower_fence,
        "upper_fence": upper_fence,
        "iqr_outlier_count": int(outlier_mask.sum()),
        "iqr_outlier_percentage": float(outlier_mask.mean() * 100),
    }


def calculate_zscore_outliers(series: pd.Series) -> dict[str, float | int]:
    """Compute Z-scores and count observations where absolute Z > 3."""

    numeric_series = pd.to_numeric(series, errors="coerce").dropna()
    mean_value = float(numeric_series.mean())
    standard_deviation = float(numeric_series.std(ddof=0))

    if np.isclose(standard_deviation, 0.0):
        z_scores = pd.Series(0.0, index=numeric_series.index)
    else:
        z_scores = (numeric_series - mean_value) / standard_deviation

    outlier_mask = z_scores.abs() > 3

    return {
        "mean": mean_value,
        "standard_deviation": standard_deviation,
        "zscore_outlier_count": int(outlier_mask.sum()),
        "zscore_outlier_percentage": float(outlier_mask.mean() * 100),
    }


def compare_methods(iqr_count: int, zscore_count: int) -> tuple[str, str]:
    """Describe whether the two methods produced identical counts."""

    if iqr_count == zscore_count:
        return (
            "Agree",
            "Both methods flagged the same number of observations.",
        )

    return (
        "Disagree",
        "IQR uses robust quartiles and is sensitive to skewed tails, while "
        "Z-scores depend on the mean and standard deviation and assume a "
        "more symmetric distribution.",
    )


def audit_outliers(
    dataframe: pd.DataFrame,
    selected_columns: list[str],
) -> pd.DataFrame:
    """Apply both methods to every selected continuous numeric measure."""

    result_rows: list[dict[str, object]] = []

    for column in selected_columns:
        series = dataframe[column]
        iqr_result = calculate_iqr_outliers(series)
        zscore_result = calculate_zscore_outliers(series)

        agreement, explanation = compare_methods(
            int(iqr_result["iqr_outlier_count"]),
            int(zscore_result["zscore_outlier_count"]),
        )

        result_rows.append(
            {
                "column_name": column,
                "non_null_rows": int(series.notna().sum()),
                **iqr_result,
                **zscore_result,
                "zscore_threshold": 3,
                "methods_agree": agreement,
                "comparison_explanation": explanation,
            }
        )

    return pd.DataFrame(result_rows)


# ============================================================
# Reporting
# ============================================================


def print_selection_audit(selection_audit: pd.DataFrame) -> None:
    print("\nContinuous numeric measure selection audit")
    print("=" * 100)
    print(selection_audit.to_string(index=False))


def print_outlier_results(results: pd.DataFrame) -> None:
    print("\nIQR and Z-score outlier results")
    print("=" * 100)

    for _, row in results.iterrows():
        print(f"\nColumn: {row['column_name']}")
        print("-" * 80)
        print(f"Q1: {row['q1']:.6f}")
        print(f"Q3: {row['q3']:.6f}")
        print(f"IQR: {row['iqr']:.6f}")
        print(f"Lower fence: {row['lower_fence']:.6f}")
        print(f"Upper fence: {row['upper_fence']:.6f}")
        print(
            f"IQR outliers: {int(row['iqr_outlier_count']):,} "
            f"({row['iqr_outlier_percentage']:.2f}%)"
        )
        print(f"Mean: {row['mean']:.6f}")
        print(f"Population standard deviation: {row['standard_deviation']:.6f}")
        print(
            f"Z-score outliers (|Z| > 3): "
            f"{int(row['zscore_outlier_count']):,} "
            f"({row['zscore_outlier_percentage']:.2f}%)"
        )
        print(f"Comparison: {row['methods_agree']}")
        print(row["comparison_explanation"])


def save_text_report(
    selection_audit: pd.DataFrame,
    results: pd.DataFrame,
) -> None:
    lines = [
        "OLIST CONTINUOUS NUMERIC OUTLIER AUDIT",
        "=" * 100,
        "",
        "FILTERING RULE",
        "-" * 100,
        (
            "A numeric column is retained when it is not an ID/key, has more "
            "than two unique non-null values, has non-zero variance, and is "
            "not near-zero variance. Near-zero variance means one value "
            "accounts for at least 99.9% of non-null rows."
        ),
        "",
        "SELECTION AUDIT",
        "-" * 100,
        selection_audit.to_string(index=False),
        "",
        "IQR AND Z-SCORE RESULTS",
        "-" * 100,
        results.to_string(index=False),
        "",
    ]

    OUTLIER_REPORT_TXT.write_text("\n".join(lines), encoding="utf-8")


# ============================================================
# Main program
# ============================================================


def main() -> None:
    dataframe = load_data(INPUT_CSV)
    selected_columns, selection_audit = classify_numeric_columns(dataframe)

    print_selection_audit(selection_audit)

    if not selected_columns:
        OUTPUT_DIR = PROJECT_ROOT / "outputs"
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        selection_audit.to_csv(
            SELECTION_AUDIT_CSV,
            index=False,
            encoding="utf-8",
        )

        raise ValueError(
            "No continuous numeric measures survived the filter. "
            "Review the printed column names and the saved selection audit at "
            f"{SELECTION_AUDIT_CSV}. Expected candidates were: "
            f"{CONTINUOUS_CANDIDATE_COLUMNS}"
        )

    print("\nSelected continuous numeric measures")
    print("-" * 70)
    for column in selected_columns:
        print(f"- {column}")

    results = audit_outliers(dataframe, selected_columns)
    print_outlier_results(results)

    OUTLIER_COMPARISON_CSV.parent.mkdir(parents=True, exist_ok=True)

    selection_audit.to_csv(
        SELECTION_AUDIT_CSV,
        index=False,
        encoding="utf-8",
    )
    results.to_csv(
        OUTLIER_COMPARISON_CSV,
        index=False,
        encoding="utf-8",
    )

    details = {
        "input_csv": str(INPUT_CSV),
        "filtering_rule": {
            "explicit_candidates": CONTINUOUS_CANDIDATE_COLUMNS,
            "binary_unique_limit": BINARY_UNIQUE_LIMIT,
            "near_zero_dominance_threshold": NEAR_ZERO_DOMINANCE_THRESHOLD,
        },
        "selected_columns": selected_columns,
        "results": results.to_dict(orient="records"),
    }

    OUTLIER_DETAILS_JSON.write_text(
        json.dumps(details, indent=2),
        encoding="utf-8",
    )
    save_text_report(selection_audit, results)

    print("\nOutlier audit completed successfully.")
    print(f"Selection audit: {SELECTION_AUDIT_CSV}")
    print(f"Comparison CSV: {OUTLIER_COMPARISON_CSV}")
    print(f"Text report: {OUTLIER_REPORT_TXT}")
    print(f"JSON details: {OUTLIER_DETAILS_JSON}")


if __name__ == "__main__":
    main()