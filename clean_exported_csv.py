from pathlib import Path
import pandas as pd


# ---------------------------------------------------------
# Project paths
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_CSV = (
    PROJECT_ROOT
    / "outputs"
    / "task4_inner_join_export.csv"
)

CLEANED_CSV = (
    PROJECT_ROOT
    / "outputs"
    / "task7_cleaned_join_export.csv"
)

REPORT_FILE = (
    PROJECT_ROOT
    / "outputs"
    / "cleaning_validation_report.txt"
)


def load_data(file_path: Path) -> pd.DataFrame:
    """Load the exported Task 4 INNER JOIN CSV."""

    if not file_path.exists():
        raise FileNotFoundError(
            f"Input CSV was not found:\n{file_path}\n\n"
            "Run export_join_csv.py before running this script."
        )

    dataframe = pd.read_csv(file_path)

    print("CSV loaded successfully.")
    print(f"Input file: {file_path}")
    print(f"Rows loaded: {len(dataframe):,}")
    print(f"Columns loaded: {len(dataframe.columns)}")

    return dataframe


def missing_value_report(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Return missing-value count and percentage for every column."""

    report = pd.DataFrame(
        {
            "column_name": dataframe.columns,
            "missing_count": dataframe.isnull().sum().values,
            "missing_percentage": (
                dataframe.isnull().mean().values * 100
            ).round(2),
        }
    )

    return report


def clean_data(dataframe: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Impute missing values and remove duplicate rows."""

    cleaned = dataframe.copy()

    rows_before_duplicates = len(cleaned)
    duplicate_count = cleaned.duplicated().sum()

    print("\nDuplicate-row check before cleaning")
    print("-----------------------------------")
    print(f"Rows before drop_duplicates(): {rows_before_duplicates:,}")
    print(f"Duplicate rows detected: {duplicate_count:,}")

    cleaned = cleaned.drop_duplicates().reset_index(drop=True)

    rows_after_duplicates = len(cleaned)

    print(f"Rows after drop_duplicates(): {rows_after_duplicates:,}")
    print(
        "Rows removed: "
        f"{rows_before_duplicates - rows_after_duplicates:,}"
    )

    numeric_columns = cleaned.select_dtypes(
        include="number"
    ).columns.tolist()

    categorical_columns = cleaned.select_dtypes(
        exclude="number"
    ).columns.tolist()

    print("\nNumeric columns imputed with median")
    print("-----------------------------------")

    for column in numeric_columns:
        missing_count = cleaned[column].isnull().sum()

        if missing_count > 0:
            median_value = cleaned[column].median()

            if pd.isna(median_value):
                median_value = 0

            cleaned[column] = cleaned[column].fillna(median_value)

            print(
                f"{column}: filled {missing_count:,} missing values "
                f"with median = {median_value}"
            )
        else:
            print(f"{column}: no missing values")

    print("\nCategorical/text columns imputed")
    print("--------------------------------")

    for column in categorical_columns:
        missing_count = cleaned[column].isnull().sum()

        if missing_count > 0:
            non_null_mode = cleaned[column].mode(dropna=True)

            if not non_null_mode.empty:
                fill_value = non_null_mode.iloc[0]
                strategy = "mode"
            else:
                fill_value = "unknown"
                strategy = "'unknown'"

            cleaned[column] = cleaned[column].fillna(fill_value)

            print(
                f"{column}: filled {missing_count:,} missing values "
                f"using {strategy} = {fill_value}"
            )
        else:
            print(f"{column}: no missing values")

    remaining_missing = cleaned.isnull().sum()

    validation = {
        "rows_before_duplicates": rows_before_duplicates,
        "duplicate_rows_detected": int(duplicate_count),
        "rows_after_duplicates": rows_after_duplicates,
        "rows_removed": rows_before_duplicates - rows_after_duplicates,
        "numeric_columns": numeric_columns,
        "categorical_columns": categorical_columns,
        "remaining_missing_total": int(remaining_missing.sum()),
    }

    return cleaned, validation


def save_report(
    original_missing_report: pd.DataFrame,
    cleaned_dataframe: pd.DataFrame,
    validation: dict,
) -> None:
    """Save cleaning results to a text report."""

    final_missing_report = missing_value_report(cleaned_dataframe)

    lines = [
        "OLIST EXPORTED CSV CLEANING VALIDATION REPORT",
        "=" * 60,
        "",
        f"Input CSV: {INPUT_CSV}",
        f"Cleaned CSV: {CLEANED_CSV}",
        "",
        "MISSING VALUES BEFORE CLEANING",
        "-" * 60,
        original_missing_report.to_string(index=False),
        "",
        "DUPLICATE-ROW VALIDATION",
        "-" * 60,
        (
            "Rows before drop_duplicates(): "
            f"{validation['rows_before_duplicates']:,}"
        ),
        (
            "Duplicate rows detected: "
            f"{validation['duplicate_rows_detected']:,}"
        ),
        (
            "Rows after drop_duplicates(): "
            f"{validation['rows_after_duplicates']:,}"
        ),
        (
            "Rows removed: "
            f"{validation['rows_removed']:,}"
        ),
        "",
        "IMPUTATION STRATEGY",
        "-" * 60,
        (
            "Numeric columns were imputed using the median because "
            "the median is less sensitive to extreme values and "
            "outliers than the mean."
        ),
        (
            "Categorical and text columns were imputed using the "
            "column mode. If no valid mode existed, the literal "
            "string 'unknown' was used."
        ),
        "",
        "MISSING VALUES AFTER CLEANING",
        "-" * 60,
        final_missing_report.to_string(index=False),
        "",
        (
            "Total missing values remaining: "
            f"{validation['remaining_missing_total']}"
        ),
    ]

    REPORT_FILE.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def main() -> None:
    dataframe = load_data(INPUT_CSV)

    initial_missing_report = missing_value_report(dataframe)

    print("\nMissing values before cleaning")
    print("------------------------------")
    print(initial_missing_report.to_string(index=False))

    cleaned_dataframe, validation = clean_data(dataframe)

    final_missing_report = missing_value_report(cleaned_dataframe)

    print("\nMissing values after cleaning")
    print("-----------------------------")
    print(final_missing_report.to_string(index=False))

    print("\nisnull().sum() after cleaning")
    print("-----------------------------")
    print(cleaned_dataframe.isnull().sum())

    remaining_missing = cleaned_dataframe.isnull().sum().sum()

    if remaining_missing != 0:
        raise ValueError(
            f"Cleaning failed. {remaining_missing} missing values remain."
        )

    CLEANED_CSV.parent.mkdir(parents=True, exist_ok=True)

    cleaned_dataframe.to_csv(
        CLEANED_CSV,
        index=False,
        encoding="utf-8",
    )

    save_report(
        initial_missing_report,
        cleaned_dataframe,
        validation,
    )

    print("\nCleaning completed successfully.")
    print(f"Cleaned rows: {len(cleaned_dataframe):,}")
    print(f"Cleaned columns: {len(cleaned_dataframe.columns)}")
    print(f"Cleaned CSV saved to: {CLEANED_CSV}")
    print(f"Validation report saved to: {REPORT_FILE}")
    print("Final missing-value total: 0")


if __name__ == "__main__":
    main()
