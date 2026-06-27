from pathlib import Path
import pandas as pd

from src.utils.normalization import build_key


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
IMPORT_DIR = DATA_DIR / "imports"
REPORTS_DIR = DATA_DIR / "reports"

IMPORT_FILE = IMPORT_DIR / "chart_equivalencies_import.csv"
MASTER_FILE = DATA_DIR / "paint_equivalency_database.csv"

BACKUP_FILE = REPORTS_DIR / "paint_equivalency_database_before_chart_import_backup.csv"
NEW_ROWS_REPORT = REPORTS_DIR / "chart_equivalencies_new_rows.csv"
DUPLICATE_ROWS_REPORT = REPORTS_DIR / "chart_equivalencies_duplicate_rows.csv"

MASTER_COLUMNS = [
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


def is_blank(value) -> bool:
    if pd.isna(value):
        return True

    value = str(value).strip()
    return value == "" or value.lower() in {"nan", "none", "null"}


def clean_text(value):
    if is_blank(value):
        return ""
    return str(value).strip()


def ensure_columns(df):
    for column in MASTER_COLUMNS:
        if column not in df.columns:
            df[column] = ""

    return df[MASTER_COLUMNS].copy()


def make_relationship_key(row):
    return build_key(
        row.get("Source_Company", ""),
        row.get("Source_Product_Line", ""),
        row.get("Source_Paint_Name", ""),
        row.get("Equivalent_Company", ""),
        row.get("Equivalent_Product_Line", ""),
        row.get("Equivalent_Paint_Name", ""),
    )


def clean_import_rows(df):
    df = ensure_columns(df)

    for column in MASTER_COLUMNS:
        df[column] = df[column].apply(clean_text)

    # Remove blank rows
    df = df[
        ~(
            df["Source_Company"].eq("")
            & df["Source_Paint_Name"].eq("")
            & df["Equivalent_Company"].eq("")
            & df["Equivalent_Paint_Name"].eq("")
        )
    ].copy()

    # Remove rows without enough relationship data
    df = df[
        df["Source_Company"].ne("")
        & df["Source_Paint_Name"].ne("")
        & df["Equivalent_Company"].ne("")
        & df["Equivalent_Paint_Name"].ne("")
    ].copy()

    # Set sane defaults
    df.loc[df["Match_Type"].eq(""), "Match_Type"] = "Chart Equivalency"
    df.loc[df["Confidence"].eq(""), "Confidence"] = "Medium"
    df.loc[df["Source"].eq(""), "Source"] = IMPORT_FILE.name

    df["_relationship_key"] = df.apply(make_relationship_key, axis=1)

    # Drop duplicate rows inside the import itself
    df = df.drop_duplicates(subset=["_relationship_key"], keep="first").copy()

    return df


def main():
    IMPORT_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    if not IMPORT_FILE.exists():
        raise FileNotFoundError(
            f"Missing import file: {IMPORT_FILE}\n"
            f"Create it first with the required headers."
        )

    import_df = pd.read_csv(IMPORT_FILE)
    import_df = clean_import_rows(import_df)

    if MASTER_FILE.exists():
        master_df = pd.read_csv(MASTER_FILE)
        master_df = ensure_columns(master_df)

        for column in MASTER_COLUMNS:
            master_df[column] = master_df[column].apply(clean_text)

        master_df["_relationship_key"] = master_df.apply(make_relationship_key, axis=1)
    else:
        master_df = pd.DataFrame(columns=MASTER_COLUMNS)
        master_df["_relationship_key"] = ""

    # Backup before changing anything
    master_df.drop(columns=["_relationship_key"], errors="ignore").to_csv(
        BACKUP_FILE,
        index=False,
    )

    existing_keys = set(master_df["_relationship_key"].dropna().astype(str))

    new_rows = import_df[
        ~import_df["_relationship_key"].isin(existing_keys)
    ].copy()

    duplicate_rows = import_df[
        import_df["_relationship_key"].isin(existing_keys)
    ].copy()

    updated_master = pd.concat(
        [
            master_df,
            new_rows,
        ],
        ignore_index=True,
    )

    updated_master = updated_master.drop_duplicates(
        subset=["_relationship_key"],
        keep="first",
    )

    updated_master.drop(columns=["_relationship_key"], errors="ignore").to_csv(
        MASTER_FILE,
        index=False,
    )

    new_rows.drop(columns=["_relationship_key"], errors="ignore").to_csv(
        NEW_ROWS_REPORT,
        index=False,
    )

    duplicate_rows.drop(columns=["_relationship_key"], errors="ignore").to_csv(
        DUPLICATE_ROWS_REPORT,
        index=False,
    )

    print("IMPORT CHART EQUIVALENCIES")
    print("--------------------------")
    print(f"Import file: {IMPORT_FILE}")
    print(f"Master file: {MASTER_FILE}")
    print()
    print(f"Rows in import file after cleaning: {len(import_df)}")
    print(f"Existing master rows: {len(master_df)}")
    print(f"New rows added: {len(new_rows)}")
    print(f"Duplicate rows skipped: {len(duplicate_rows)}")
    print(f"Updated master rows: {len(updated_master)}")
    print()
    print(f"Backup saved to: {BACKUP_FILE}")
    print(f"New rows report: {NEW_ROWS_REPORT}")
    print(f"Duplicate rows report: {DUPLICATE_ROWS_REPORT}")


if __name__ == "__main__":
    main()