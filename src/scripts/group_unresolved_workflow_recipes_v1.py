from pathlib import Path
import pandas as pd


# ============================================================
# GROUP UNRESOLVED WORKFLOW RECIPES - V1
# ============================================================
#
# PURPOSE
# -------
# Groups unresolved workflow CSVs by Recipe_Hash.
#
# This DOES NOT modify workflow files.
# This DOES NOT move files.
# This DOES NOT import anything.
# This is read-only.
#
# WHY THIS EXISTS
# ---------------
# The unresolved audit showed:
#
#     2669 unresolved CSVs
#     17345 rows
#     2642 likely usable
#     1556 unique recipe hashes
#     1113 duplicate recipe hits
#
# That means we do not want to resolve 2669 files one by one.
#
# Instead, we group files that appear to contain the same paint
# recipe. Then the resolver can work from recipe groups.
#
# OUTPUT
# ------
# exports/reports/unresolved_workflow_recipe_groups_v1.csv
#
# ============================================================


PROJECT_ROOT = Path(__file__).resolve().parents[2]

AUDIT_REPORT_PATH = PROJECT_ROOT / "exports" / "reports" / "unresolved_workflow_audit_v1.csv"

GROUP_REPORT_PATH = PROJECT_ROOT / "exports" / "reports" / "unresolved_workflow_recipe_groups_v1.csv"


def clean_text(value):
    """
    Safely normalize display text.
    """

    if pd.isna(value):
        return ""

    return str(value).strip()


def most_common_value(series):
    """
    Return the most common non-empty value from a pandas Series.

    This is useful because OCR may produce several bad guesses.
    The most repeated value is often the best first guess.
    """

    values = series.dropna().astype(str).str.strip()
    values = values[values != ""]

    if values.empty:
        return ""

    return values.value_counts().idxmax()


def join_sample_values(series, limit=8):
    """
    Join a small sample of unique non-empty values.

    This keeps the report readable instead of dumping hundreds
    of filenames or unit guesses into one cell.
    """

    values = series.dropna().astype(str).str.strip()
    values = values[values != ""]
    unique_values = list(dict.fromkeys(values.tolist()))

    return " | ".join(unique_values[:limit])


def main():
    print("=" * 60)
    print("GROUP UNRESOLVED WORKFLOW RECIPES V1")
    print("=" * 60)

    if not AUDIT_REPORT_PATH.exists():
        print(f"Missing audit report: {AUDIT_REPORT_PATH}")
        print()
        print("Run this first:")
        print("python -m src.scripts.audit_unresolved_workflows_v1")
        return

    GROUP_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    audit_df = pd.read_csv(AUDIT_REPORT_PATH)

    if audit_df.empty:
        print("Audit report is empty. Nothing to group.")
        return

    required_columns = [
        "File",
        "Path",
        "Rows",
        "Workflow_ID",
        "Superfaction",
        "Faction",
        "Unit",
        "Unique_Paint_IDs",
        "Unique_Paint_Names",
        "Recipe_Hash",
        "Likely_Usable",
        "Notes",
    ]

    missing = [col for col in required_columns if col not in audit_df.columns]

    if missing:
        print("Audit report is missing required columns:")
        for col in missing:
            print(f" - {col}")
        return

    usable_df = audit_df[
        (audit_df["Likely_Usable"] == True)
        & audit_df["Recipe_Hash"].notna()
        & (audit_df["Recipe_Hash"].astype(str).str.strip() != "")
    ].copy()

    if usable_df.empty:
        print("No usable unresolved recipes found.")
        return

    records = []

    grouped = usable_df.groupby("Recipe_Hash", dropna=True)

    for recipe_hash, group in grouped:
        files = group["File"].dropna().astype(str).tolist()
        paths = group["Path"].dropna().astype(str).tolist()

        file_count = len(group)
        total_rows = int(group["Rows"].fillna(0).sum())

        best_unit_guess = most_common_value(group["Unit"])
        best_superfaction_guess = most_common_value(group["Superfaction"])
        best_faction_guess = most_common_value(group["Faction"])

        unique_units = group["Unit"].dropna().astype(str).str.strip()
        unique_units = unique_units[unique_units != ""].nunique()

        max_unique_paint_ids = int(group["Unique_Paint_IDs"].fillna(0).max())
        max_unique_paint_names = int(group["Unique_Paint_Names"].fillna(0).max())

        sample_files = " | ".join(files[:8])
        sample_paths = " | ".join(paths[:4])
        sample_units = join_sample_values(group["Unit"], limit=10)

        unresolved_count = group["Workflow_ID"].astype(str).str.upper().str.startswith("UNRESOLVED").sum()

        notes_sample = join_sample_values(group["Notes"], limit=5)

        if best_unit_guess == "":
            resolver_priority = "LOW - Missing Unit"
        elif max_unique_paint_ids == 0 and max_unique_paint_names == 0:
            resolver_priority = "LOW - No Paints"
        elif file_count > 1:
            resolver_priority = "HIGH - Duplicate Recipe Group"
        else:
            resolver_priority = "NORMAL"

        records.append({
            "Recipe_Hash": recipe_hash,
            "File_Count": file_count,
            "Total_Rows": total_rows,
            "Unresolved_File_Count": int(unresolved_count),
            "Best_Unit_Guess": best_unit_guess,
            "Best_Superfaction_Guess": best_superfaction_guess,
            "Best_Faction_Guess": best_faction_guess,
            "Unique_Unit_Guesses": int(unique_units),
            "Max_Unique_Paint_IDs": max_unique_paint_ids,
            "Max_Unique_Paint_Names": max_unique_paint_names,
            "Resolver_Priority": resolver_priority,
            "Sample_Units": sample_units,
            "Sample_Files": sample_files,
            "Sample_Paths": sample_paths,
            "Notes_Sample": notes_sample,
        })

    group_df = pd.DataFrame(records)

    group_df = group_df.sort_values(
        by=["File_Count", "Total_Rows", "Max_Unique_Paint_IDs"],
        ascending=[False, False, False],
    )

    group_df.to_csv(GROUP_REPORT_PATH, index=False)

    print()
    print("SUMMARY")
    print("-" * 60)
    print(f"Usable unresolved files .... {len(usable_df)}")
    print(f"Recipe groups .............. {len(group_df)}")
    print(f"Duplicate groups ........... {len(group_df[group_df['File_Count'] > 1])}")
    print(f"Single-file groups ......... {len(group_df[group_df['File_Count'] == 1])}")
    print()

    print("TOP GROUPS")
    print("-" * 60)

    preview_columns = [
        "Recipe_Hash",
        "File_Count",
        "Total_Rows",
        "Best_Unit_Guess",
        "Resolver_Priority",
    ]

    print(group_df[preview_columns].head(25).to_string(index=False))

    print()
    print(f"Group report written: {GROUP_REPORT_PATH}")

    print("=" * 60)
    print("GROUPING COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()