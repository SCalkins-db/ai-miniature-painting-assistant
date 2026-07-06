from pathlib import Path
import hashlib
import pandas as pd


# ============================================================
# UNRESOLVED WORKFLOW AUDIT - V1
# ============================================================
#
# PURPOSE
# -------
# This script audits unresolved workflow CSV files.
#
# It DOES NOT modify files.
# It DOES NOT move files.
# It DOES NOT import anything.
# It DOES NOT delete anything.
#
# This is a read-only inspection tool.
#
# WHY THIS EXISTS
# ---------------
# The acquisition pipeline is now working.
# Images are processed once, logged, and skipped on reruns.
#
# The current problem is that many extracted workflow CSVs are
# sitting in:
#
#     data/workflows/imported/
#
# with Workflow_ID values like:
#
#     UNRESOLVED_000004_FRAME_00005
#
# The rows contain useful paint workflow information, but the
# workflow identity is incomplete.
#
# This script answers:
#
#     How many unresolved files exist?
#     How many rows are inside them?
#     What units were detected?
#     Which identity fields are missing?
#     Which paint recipes appear duplicated?
#     Which files may belong together?
#
# OUTPUT
# ------
# Console summary.
#
# CSV report written to:
#
#     exports/reports/unresolved_workflow_audit_v1.csv
#
# ============================================================


PROJECT_ROOT = Path(__file__).resolve().parents[2]

WORKFLOW_IMPORTED_DIR = PROJECT_ROOT / "data" / "workflows" / "imported"

REPORT_PATH = PROJECT_ROOT / "exports" / "reports" / "unresolved_workflow_audit_v1.csv"


EXPECTED_COLUMNS = [
    "Workflow_ID",
    "Superfaction",
    "Faction",
    "Unit",
    "Model_Area",
    "Area_Order",
    "Step_Order",
    "Technique",
    "Paint_ID",
    "Paint_Name",
    "Purpose",
    "Optional",
    "Notes",
]


IDENTITY_COLUMNS = [
    "Workflow_ID",
    "Superfaction",
    "Faction",
    "Unit",
]


RECIPE_COLUMNS = [
    "Model_Area",
    "Area_Order",
    "Step_Order",
    "Technique",
    "Paint_ID",
    "Paint_Name",
    "Purpose",
]


def normalize_value(value):
    """
    Normalize values for comparison.

    This prevents tiny differences like:
        None
        NaN
        " "
        "ABADDON BLACK"
        "abaddon black"

    from creating fake differences during recipe hashing.
    """

    if pd.isna(value):
        return ""

    return str(value).strip().lower()


def build_recipe_hash(df):
    """
    Build a stable hash for the paint recipe rows.

    This lets us detect likely duplicate recipes even when the
    file names are different.

    Example:
        unresolved_000004_frame_00005.csv
        unresolved_000004_frame_00006.csv

    may both contain the same paint sequence.

    If they hash the same, they are probably duplicate extractions
    of the same workflow page or repeated video frame.
    """

    recipe_bits = []

    for _, row in df.iterrows():
        row_bits = []

        for col in RECIPE_COLUMNS:
            if col in df.columns:
                row_bits.append(normalize_value(row.get(col, "")))
            else:
                row_bits.append("")

        recipe_bits.append("|".join(row_bits))

    recipe_text = "\n".join(recipe_bits)

    return hashlib.sha256(recipe_text.encode("utf-8")).hexdigest()[:16]


def read_csv_safely(path):
    """
    Read a CSV without letting one bad file kill the whole audit.

    If a file is corrupt, malformed, or has encoding nonsense,
    we return None and record the file as unreadable.
    """

    try:
        return pd.read_csv(path)
    except Exception as exc:
        return None


def missing_columns(df):
    """
    Identify expected columns that are missing from a workflow CSV.
    """

    return [col for col in EXPECTED_COLUMNS if col not in df.columns]


def blank_identity_fields(df):
    """
    Identify identity fields that are blank across the file.

    These are the fields the resolver needs in order to promote
    an unresolved workflow into a real workflow.
    """

    blanks = []

    for col in IDENTITY_COLUMNS:
        if col not in df.columns:
            blanks.append(col)
            continue

        values = df[col].fillna("").astype(str).str.strip()

        if values.eq("").all():
            blanks.append(col)

    return blanks


def first_non_blank(df, column):
    """
    Return the first useful value from a column.
    """

    if column not in df.columns:
        return ""

    values = df[column].dropna().astype(str).str.strip()
    values = values[values != ""]

    if values.empty:
        return ""

    return values.iloc[0]


def count_unique_non_blank(df, column):
    """
    Count unique non-empty values in a column.
    """

    if column not in df.columns:
        return 0

    values = df[column].dropna().astype(str).str.strip()
    values = values[values != ""]

    return values.nunique()


def audit_file(path):
    """
    Audit one unresolved workflow CSV.
    """

    df = read_csv_safely(path)

    if df is None:
        return {
            "File": path.name,
            "Path": str(path),
            "Readable": False,
            "Rows": 0,
            "Workflow_ID": "",
            "Superfaction": "",
            "Faction": "",
            "Unit": "",
            "Missing_Columns": "UNREADABLE",
            "Blank_Identity_Fields": "UNREADABLE",
            "Unique_Paint_IDs": 0,
            "Unique_Paint_Names": 0,
            "Recipe_Hash": "",
            "Likely_Usable": False,
            "Notes": "Could not read CSV.",
        }

    missing = missing_columns(df)
    blank_identity = blank_identity_fields(df)

    workflow_id = first_non_blank(df, "Workflow_ID")
    superfaction = first_non_blank(df, "Superfaction")
    faction = first_non_blank(df, "Faction")
    unit = first_non_blank(df, "Unit")

    recipe_hash = build_recipe_hash(df)

    unique_paint_ids = count_unique_non_blank(df, "Paint_ID")
    unique_paint_names = count_unique_non_blank(df, "Paint_Name")

    likely_usable = (
        len(df) > 0
        and unit != ""
        and unique_paint_ids > 0
        and "Workflow_ID" in df.columns
    )

    notes = []

    if workflow_id.upper().startswith("UNRESOLVED"):
        notes.append("Workflow_ID unresolved")

    if not superfaction:
        notes.append("Missing Superfaction")

    if not faction:
        notes.append("Missing Faction")

    if not unit:
        notes.append("Missing Unit")

    if unique_paint_ids == 0 and unique_paint_names == 0:
        notes.append("No paints detected")

    if not notes:
        notes.append("Looks usable but still unresolved")

    return {
        "File": path.name,
        "Path": str(path),
        "Readable": True,
        "Rows": len(df),
        "Workflow_ID": workflow_id,
        "Superfaction": superfaction,
        "Faction": faction,
        "Unit": unit,
        "Missing_Columns": ", ".join(missing),
        "Blank_Identity_Fields": ", ".join(blank_identity),
        "Unique_Paint_IDs": unique_paint_ids,
        "Unique_Paint_Names": unique_paint_names,
        "Recipe_Hash": recipe_hash,
        "Likely_Usable": likely_usable,
        "Notes": "; ".join(notes),
    }


def main():
    print("=" * 60)
    print("UNRESOLVED WORKFLOW AUDIT V1")
    print("=" * 60)

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not WORKFLOW_IMPORTED_DIR.exists():
        print(f"Missing folder: {WORKFLOW_IMPORTED_DIR}")
        print("Nothing to audit.")
        return

    unresolved_files = sorted(WORKFLOW_IMPORTED_DIR.glob("unresolved_*.csv"))

    print(f"Scanning folder: {WORKFLOW_IMPORTED_DIR}")
    print(f"Unresolved CSVs found: {len(unresolved_files)}")
    print("-" * 60)

    records = []

    for path in unresolved_files:
        records.append(audit_file(path))

    if not records:
        print("No unresolved workflow files found.")
        return

    audit_df = pd.DataFrame(records)
    audit_df.to_csv(REPORT_PATH, index=False)

    total_files = len(audit_df)
    readable_files = int(audit_df["Readable"].sum())
    total_rows = int(audit_df["Rows"].sum())
    usable_files = int(audit_df["Likely_Usable"].sum())

    unique_units = audit_df["Unit"].replace("", pd.NA).dropna().nunique()
    unique_recipe_hashes = audit_df["Recipe_Hash"].replace("", pd.NA).dropna().nunique()

    duplicate_recipe_count = (
        audit_df["Recipe_Hash"]
        .replace("", pd.NA)
        .dropna()
        .duplicated()
        .sum()
    )

    print()
    print("SUMMARY")
    print("-" * 60)
    print(f"Files scanned ............ {total_files}")
    print(f"Readable files ........... {readable_files}")
    print(f"Total rows ............... {total_rows}")
    print(f"Likely usable files ...... {usable_files}")
    print(f"Unique units ............. {unique_units}")
    print(f"Unique recipe hashes ..... {unique_recipe_hashes}")
    print(f"Duplicate recipe hits .... {duplicate_recipe_count}")

    print()
    print("TOP UNITS")
    print("-" * 60)

    unit_counts = (
        audit_df["Unit"]
        .replace("", "UNKNOWN")
        .value_counts()
        .head(20)
    )

    print(unit_counts.to_string())

    print()
    print("TOP NOTES")
    print("-" * 60)

    note_counts = (
        audit_df["Notes"]
        .replace("", "No notes")
        .value_counts()
        .head(20)
    )

    print(note_counts.to_string())

    print()
    print("LIKELY DUPLICATE RECIPES")
    print("-" * 60)

    recipe_counts = (
        audit_df["Recipe_Hash"]
        .replace("", pd.NA)
        .dropna()
        .value_counts()
    )

    duplicate_recipes = recipe_counts[recipe_counts > 1].head(20)

    if duplicate_recipes.empty:
        print("No duplicate recipe hashes found.")
    else:
        print(duplicate_recipes.to_string())

    print()
    print(f"Audit report written: {REPORT_PATH}")

    print("=" * 60)
    print("UNRESOLVED WORKFLOW AUDIT COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()