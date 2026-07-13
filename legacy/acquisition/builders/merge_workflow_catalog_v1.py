from pathlib import Path
import shutil
import pandas as pd


# ============================================================
# MERGE WORKFLOW CATALOG - V1
# ============================================================
#
# PURPOSE
# -------
# Safely merges workflow catalog sources.
#
# CURRENT USE
# -----------
# Adds faction/unit data extracted from screen recordings into
# the canonical workflow catalog.
#
# SAFETY
# ------
# - Creates backup before replacing catalog
# - Does not delete source files
# - Does not modify seed files
# - Removes exact duplicate rows only
#
# FLOW
# ----
#
# Existing workflow_catalog.csv
#          +
# chaos_workflow_catalog_seed.csv
#
#          |
#          v
#
# merged workflow_catalog.csv
#
# ============================================================


PROJECT_ROOT = Path(__file__).resolve().parents[2]


CATALOG_DIR = (
    PROJECT_ROOT
    / "data"
    / "workflows"
    / "workflow_catalog"
)


MASTER_CATALOG = (
    CATALOG_DIR
    / "workflow_catalog.csv"
)


BACKUP_CATALOG = (
    CATALOG_DIR
    / "workflow_catalog_backup.csv"
)


SEED_FILES = [
    CATALOG_DIR / "chaos_workflow_catalog_seed.csv",
]


OUTPUT_FILE = MASTER_CATALOG


def load_csv(path):
    """
    Safely load CSV.
    """

    if not path.exists():
        print(f"Missing file: {path}")
        return pd.DataFrame()

    print(f"Loading: {path}")

    return pd.read_csv(path)


def normalize_columns(df):
    """
    Normalize column names.

    Prevents issues like:

    Workflow ID
    Workflow_ID
    workflow_id

    becoming separate columns.
    """

    df.columns = [
        str(col)
        .strip()
        .replace(" ", "_")
        for col in df.columns
    ]

    return df


def main():

    print("=" * 60)
    print("MERGE WORKFLOW CATALOG V1")
    print("=" * 60)


    CATALOG_DIR.mkdir(
        parents=True,
        exist_ok=True
    )


    # --------------------------------------------------------
    # Load existing catalog
    # --------------------------------------------------------

    existing_df = load_csv(
        MASTER_CATALOG
    )


    if not existing_df.empty:

        existing_df = normalize_columns(
            existing_df
        )


    # --------------------------------------------------------
    # Backup existing catalog
    # --------------------------------------------------------

    if MASTER_CATALOG.exists():

        print()
        print("Creating backup:")

        shutil.copy2(
            MASTER_CATALOG,
            BACKUP_CATALOG
        )

        print(BACKUP_CATALOG)


    # --------------------------------------------------------
    # Load seed files
    # --------------------------------------------------------

    seed_frames = []


    for seed in SEED_FILES:

        df = load_csv(seed)

        if not df.empty:

            df = normalize_columns(df)

            seed_frames.append(df)


    if not seed_frames:

        print("No seed files found.")
        return


    seed_df = pd.concat(
        seed_frames,
        ignore_index=True
    )


    # --------------------------------------------------------
    # Align columns
    # --------------------------------------------------------

    combined = pd.concat(
        [
            existing_df,
            seed_df
        ],
        ignore_index=True,
        sort=False
    )


    # --------------------------------------------------------
    # Remove exact duplicates
    # --------------------------------------------------------

    before = len(combined)


    combined = combined.drop_duplicates()


    after = len(combined)


    removed = before - after


    # --------------------------------------------------------
    # Sort catalog
    # --------------------------------------------------------

    sort_columns = [
        col
        for col in [
            "Superfaction",
            "Faction",
            "Unit",
            "Canonical_Unit",
        ]
        if col in combined.columns
    ]


    if sort_columns:

        combined = combined.sort_values(
            by=sort_columns
        )


    # --------------------------------------------------------
    # Save merged catalog
    # --------------------------------------------------------

    combined.to_csv(
        OUTPUT_FILE,
        index=False
    )


    print()
    print("SUMMARY")
    print("-" * 60)

    print(
        f"Original rows ............ {before}"
    )

    print(
        f"Duplicates removed ....... {removed}"
    )

    print(
        f"Final rows ............... {after}"
    )

    print()

    print(
        "Written:"
    )

    print(
        OUTPUT_FILE
    )

    print("=" * 60)
    print("MERGE COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()