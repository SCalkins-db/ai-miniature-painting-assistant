from pathlib import Path
import pandas as pd


# ============================================================
# BUILD WORKFLOW RECIPE HASH INDEX - V1
# ============================================================
#
# PURPOSE
# -------
# Builds the first resolver index from the grouped unresolved
# workflow recipes.
#
# This DOES NOT modify workflow CSV files.
# This DOES NOT import anything.
# This DOES NOT move anything.
#
# It creates a resolver workbook that becomes the single source
# of truth for approving workflow identities.
#
# WHY THIS EXISTS
# ---------------
#
# We now know:
#
#     2642 unresolved workflow files
#     ↓
#     grouped into
#     ↓
#     1549 unique recipe groups
#
# Instead of resolving thousands of CSV files individually,
# we resolve each Recipe_Hash once.
#
# Every future duplicate simply inherits the approved identity.
#
# ============================================================
#
# OUTPUT
#
# data/workflows/resolver/
#     workflow_recipe_hash_index_v1.csv
#
# ============================================================


PROJECT_ROOT = Path(__file__).resolve().parents[2]

GROUP_REPORT = (
    PROJECT_ROOT
    / "exports"
    / "reports"
    / "unresolved_workflow_recipe_groups_v1.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "workflows"
    / "resolver"
)

OUTPUT_FILE = (
    OUTPUT_DIR
    / "workflow_recipe_hash_index_v1.csv"
)


def clean(value):
    """
    Normalize values.
    """

    if pd.isna(value):
        return ""

    return str(value).strip()


def make_suggested_id(unit):
    """
    Build a very rough suggested workflow id.

    Human approval still required.
    """

    unit = clean(unit)

    if not unit:
        return ""

    unit = unit.upper()

    for ch in [
        "-",
        "/",
        "(",
        ")",
        "[",
        "]",
        ".",
        ",",
        ":",
        ";",
        "'",
        '"',
    ]:
        unit = unit.replace(ch, " ")

    unit = "_".join(unit.split())

    return f"{unit}_WORKFLOW"


def main():

    print("=" * 60)
    print("BUILD WORKFLOW RECIPE HASH INDEX V1")
    print("=" * 60)

    if not GROUP_REPORT.exists():
        print()
        print("Missing group report:")
        print(GROUP_REPORT)
        print()
        print("Run:")
        print("python -m src.scripts.group_unresolved_workflow_recipes_v1")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    group_df = pd.read_csv(GROUP_REPORT)

    records = []

    for _, row in group_df.iterrows():

        unit = clean(row.get("Best_Unit_Guess", ""))
        superfaction = clean(row.get("Best_Superfaction_Guess", ""))
        faction = clean(row.get("Best_Faction_Guess", ""))

        records.append({

            # -------------------------------------------------
            # Permanent recipe identity
            # -------------------------------------------------

            "Recipe_Hash":
                clean(row["Recipe_Hash"]),

            "File_Count":
                int(row["File_Count"]),

            "Total_Rows":
                int(row["Total_Rows"]),

            # -------------------------------------------------
            # Automatic suggestions
            # -------------------------------------------------

            "Suggested_Workflow_ID":
                make_suggested_id(unit),

            "Suggested_Superfaction":
                superfaction,

            "Suggested_Faction":
                faction,

            "Suggested_Unit":
                unit,

            # -------------------------------------------------
            # Human approved values
            # -------------------------------------------------

            "Approved_Workflow_ID":
                "",

            "Approved_Superfaction":
                "",

            "Approved_Faction":
                "",

            "Approved_Unit":
                "",

            "Approved_Workflow_Name":
                "",

            # -------------------------------------------------
            # Resolver state
            # -------------------------------------------------

            "Resolver_Status":
                "Pending",

            "Confidence":
                "",

            "Priority":
                row["Resolver_Priority"],

            "Reviewed_By":
                "",

            "Review_Date":
                "",

            "Notes":
                "",

            # -------------------------------------------------
            # Helpful reference data
            # -------------------------------------------------

            "Sample_Units":
                clean(row["Sample_Units"]),

            "Sample_Files":
                clean(row["Sample_Files"]),

            "Sample_Paths":
                clean(row["Sample_Paths"]),

            "Notes_Sample":
                clean(row["Notes_Sample"]),
        })

    resolver_df = pd.DataFrame(records)

    resolver_df = resolver_df.sort_values(
        by=[
            "Priority",
            "File_Count",
            "Total_Rows",
        ],
        ascending=[
            True,
            False,
            False,
        ],
    )

    resolver_df.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    print()
    print("SUMMARY")
    print("-" * 60)

    print(f"Recipe Groups ............ {len(resolver_df)}")

    print(f"Pending ................. {(resolver_df['Resolver_Status'] == 'Pending').sum()}")

    print()

    print("TOP CANDIDATES")
    print("-" * 60)

    preview = resolver_df[
        [
            "Recipe_Hash",
            "Suggested_Workflow_ID",
            "Suggested_Unit",
            "Priority",
        ]
    ].head(25)

    print(preview.to_string(index=False))

    print()

    print(f"Resolver index written:")
    print(OUTPUT_FILE)

    print()
    print("=" * 60)
    print("BUILD COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()