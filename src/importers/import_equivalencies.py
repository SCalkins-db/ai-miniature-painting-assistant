from pathlib import Path
import pandas as pd

from src.utils.normalization import build_key


PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_ROOT / "data"
SOURCE_IMPORT_FILE = DATA_DIR / "speedpaint_equivalency_database_seed.csv"
MASTER_EQUIVALENCY_FILE = DATA_DIR / "paint_equivalency_database.csv"

REPORTS_DIR = DATA_DIR / "reports"
BACKUP_FILE = REPORTS_DIR / "paint_equivalency_database_backup.csv"


REQUIRED_COLUMNS = [
    "Source_Company",
    "Source_Product_Line",
    "Source_Paint_Name",
    "Source_Paint_ID",
    "Equivalent_Company",
    "Equivalent_Product_Line",
    "Equivalent_Paint_Name",
    "Equivalent_Paint_ID",
    "Match_Type",
    "Similarity_Percent",
    "Confidence",
    "Source",
    "Notes",
]


DEDUPLICATION_KEY = [
    "Source_Company",
    "Source_Product_Line",
    "Source_Paint_Name",
    "Equivalent_Company",
    "Equivalent_Product_Line",
    "Equivalent_Paint_Name",
]


def clean_text(value):
    if pd.isna(value):
        return ""

    return str(value).strip()


def ensure_required_columns(df, file_name):
    missing_columns = [
        column for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"{file_name} is missing required columns: {missing_columns}"
        )


def normalize_dataframe(df):
    df = df.copy()

    for column in REQUIRED_COLUMNS:
        if column not in df.columns:
            df[column] = ""

    df = df[REQUIRED_COLUMNS]

    for column in REQUIRED_COLUMNS:
        df[column] = df[column].apply(clean_text)

    return df


def build_deduplication_key(df):
    return df.apply(
        lambda row: build_key(
            *[
                row.get(column, "")
                for column in DEDUPLICATION_KEY
            ]
        ),
        axis=1,
    )


def main():
    print("IMPORT EQUIVALENCIES")
    print("--------------------")

    if not SOURCE_IMPORT_FILE.exists():
        raise FileNotFoundError(f"Import file not found: {SOURCE_IMPORT_FILE}")

    if not MASTER_EQUIVALENCY_FILE.exists():
        raise FileNotFoundError(f"Master equivalency file not found: {MASTER_EQUIVALENCY_FILE}")

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    import_df = pd.read_csv(SOURCE_IMPORT_FILE)
    master_df = pd.read_csv(MASTER_EQUIVALENCY_FILE)

    ensure_required_columns(import_df, SOURCE_IMPORT_FILE.name)
    ensure_required_columns(master_df, MASTER_EQUIVALENCY_FILE.name)

    import_df = normalize_dataframe(import_df)
    master_df = normalize_dataframe(master_df)

    master_df.to_csv(BACKUP_FILE, index=False)

    master_keys = set(build_deduplication_key(master_df))
    import_df["_dedupe_key"] = build_deduplication_key(import_df)

    new_rows_df = import_df[
        ~import_df["_dedupe_key"].isin(master_keys)
    ].copy()

    duplicate_rows_df = import_df[
        import_df["_dedupe_key"].isin(master_keys)
    ].copy()

    new_rows_df = new_rows_df.drop(columns=["_dedupe_key"])
    duplicate_rows_df = duplicate_rows_df.drop(columns=["_dedupe_key"])

    updated_df = pd.concat(
        [master_df, new_rows_df],
        ignore_index=True
    )

    updated_df["Similarity_Percent_Sort"] = pd.to_numeric(
        updated_df["Similarity_Percent"].astype(str).str.replace("%", "", regex=False),
        errors="coerce"
    ).fillna(0)

    updated_df = updated_df.sort_values(
        by=[
            "Source_Company",
            "Source_Product_Line",
            "Source_Paint_Name",
            "Similarity_Percent_Sort",
        ],
        ascending=[True, True, True, False],
    )

    updated_df = updated_df.drop(columns=["Similarity_Percent_Sort"])

    updated_df.to_csv(MASTER_EQUIVALENCY_FILE, index=False)

    duplicate_report = REPORTS_DIR / "duplicate_equivalency_import_rows.csv"
    new_rows_report = REPORTS_DIR / "new_equivalency_import_rows.csv"

    duplicate_rows_df.to_csv(duplicate_report, index=False)
    new_rows_df.to_csv(new_rows_report, index=False)

    print(f"Import file: {SOURCE_IMPORT_FILE}")
    print(f"Master file: {MASTER_EQUIVALENCY_FILE}")
    print()
    print(f"Rows in import file: {len(import_df)}")
    print(f"Existing master rows: {len(master_df)}")
    print(f"New rows added: {len(new_rows_df)}")
    print(f"Duplicate rows skipped: {len(duplicate_rows_df)}")
    print(f"Updated master rows: {len(updated_df)}")
    print()
    print(f"Backup saved to: {BACKUP_FILE}")
    print(f"New rows report: {new_rows_report}")
    print(f"Duplicate rows report: {duplicate_report}")


if __name__ == "__main__":
    main()
