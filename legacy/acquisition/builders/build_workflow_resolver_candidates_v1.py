from pathlib import Path
import difflib
import pandas as pd


# ============================================================
# BUILD WORKFLOW RESOLVER CANDIDATES - V1
# ============================================================
#
# PURPOSE
# -------
# Builds candidate matches for unresolved workflow recipe groups.
#
# This script DOES NOT modify workflow files.
# This script DOES NOT approve anything.
# This script DOES NOT import anything.
#
# It creates a review CSV where you can approve the correct
# canonical unit/workflow candidate.
#
# INPUT
# -----
# data/workflows/resolver/workflow_recipe_hash_index_v1.csv
#
# OPTIONAL INPUT
# --------------
# data/workflows/resolver/canonical_workflow_units_v1.csv
#
# If canonical_workflow_units_v1.csv does not exist, this script
# will create a starter version from the best unit guesses already
# found in the resolver index.
#
# OUTPUT
# ------
# data/workflows/resolver/workflow_resolver_candidates_v1.csv
#
# ============================================================


PROJECT_ROOT = Path(__file__).resolve().parents[2]

RESOLVER_DIR = PROJECT_ROOT / "data" / "workflows" / "resolver"

INDEX_FILE = RESOLVER_DIR / "workflow_recipe_hash_index_v1.csv"

CANONICAL_UNITS_FILE = RESOLVER_DIR / "canonical_workflow_units_v1.csv"

CANDIDATES_FILE = RESOLVER_DIR / "workflow_resolver_candidates_v1.csv"


def clean(value):
    if pd.isna(value):
        return ""
    return str(value).strip()


def normalize(value):
    value = clean(value).lower()

    replacements = {
        "€": "",
        "<": "",
        ">": "",
        "=": "",
        "(": " ",
        ")": " ",
        "[": " ",
        "]": " ",
        "'": "",
        '"': "",
        ".": " ",
        ",": " ",
        ":": " ",
        ";": " ",
        "-": " ",
        "_": " ",
    }

    for old, new in replacements.items():
        value = value.replace(old, new)

    noise_words = [
        "back",
        "sack",
        "eack",
    ]

    parts = [part for part in value.split() if part not in noise_words]

    return " ".join(parts).strip()


def similarity(a, b):
    a = normalize(a)
    b = normalize(b)

    if not a or not b:
        return 0

    return round(difflib.SequenceMatcher(None, a, b).ratio() * 100, 2)


def make_workflow_id(unit):
    unit = clean(unit)

    if not unit:
        return ""

    text = unit.upper()

    for ch in ["-", "/", "\\", "(", ")", "[", "]", ".", ",", ":", ";", "'", '"']:
        text = text.replace(ch, " ")

    text = "_".join(text.split())

    return f"{text}_WORKFLOW"


def build_starter_canonical_units(index_df):
    """
    Build a starter canonical unit list from extracted unit guesses.

    This is not perfect. That's fine.

    The whole point is to give you a starting list that you can
    clean over time instead of manually typing everything from zero.
    """

    rows = []

    units = (
        index_df["Suggested_Unit"]
        .dropna()
        .astype(str)
        .str.strip()
    )

    units = units[units != ""].drop_duplicates().sort_values()

    for unit in units:
        normalized = normalize(unit)

        if not normalized:
            continue

        rows.append({
            "Canonical_Unit": unit,
            "Canonical_Workflow_ID": make_workflow_id(unit),
            "Superfaction": "",
            "Faction": "",
            "Notes": "Starter canonical value generated from resolver index. Review later.",
        })

    canonical_df = pd.DataFrame(rows)
    canonical_df.to_csv(CANONICAL_UNITS_FILE, index=False)

    return canonical_df


def load_or_create_canonical_units(index_df):
    RESOLVER_DIR.mkdir(parents=True, exist_ok=True)

    if CANONICAL_UNITS_FILE.exists():
        return pd.read_csv(CANONICAL_UNITS_FILE)

    print("Canonical unit file not found.")
    print("Creating starter canonical unit file:")
    print(CANONICAL_UNITS_FILE)
    print()

    return build_starter_canonical_units(index_df)


def find_top_candidates(ocr_unit, canonical_df, limit=5):
    candidates = []

    for _, row in canonical_df.iterrows():
        canonical_unit = clean(row.get("Canonical_Unit", ""))
        canonical_workflow_id = clean(row.get("Canonical_Workflow_ID", ""))
        superfaction = clean(row.get("Superfaction", ""))
        faction = clean(row.get("Faction", ""))

        score = similarity(ocr_unit, canonical_unit)

        if score <= 0:
            continue

        candidates.append({
            "Candidate_Unit": canonical_unit,
            "Candidate_Workflow_ID": canonical_workflow_id,
            "Candidate_Superfaction": superfaction,
            "Candidate_Faction": faction,
            "Candidate_Score": score,
        })

    candidates = sorted(
        candidates,
        key=lambda item: item["Candidate_Score"],
        reverse=True,
    )

    return candidates[:limit]


def main():
    print("=" * 60)
    print("BUILD WORKFLOW RESOLVER CANDIDATES V1")
    print("=" * 60)

    if not INDEX_FILE.exists():
        print("Missing resolver index:")
        print(INDEX_FILE)
        print()
        print("Run this first:")
        print("python -m src.scripts.build_workflow_recipe_hash_index_v1")
        return

    index_df = pd.read_csv(INDEX_FILE)

    if index_df.empty:
        print("Resolver index is empty. Nothing to do.")
        return

    canonical_df = load_or_create_canonical_units(index_df)

    required_canonical_columns = [
        "Canonical_Unit",
        "Canonical_Workflow_ID",
        "Superfaction",
        "Faction",
    ]

    missing = [col for col in required_canonical_columns if col not in canonical_df.columns]

    if missing:
        print("Canonical unit file is missing required columns:")
        for col in missing:
            print(f" - {col}")
        return

    records = []

    for _, row in index_df.iterrows():
        recipe_hash = clean(row.get("Recipe_Hash", ""))
        suggested_unit = clean(row.get("Suggested_Unit", ""))
        priority = clean(row.get("Priority", ""))
        file_count = clean(row.get("File_Count", ""))
        total_rows = clean(row.get("Total_Rows", ""))

        candidates = find_top_candidates(
            ocr_unit=suggested_unit,
            canonical_df=canonical_df,
            limit=5,
        )

        if not candidates:
            records.append({
                "Recipe_Hash": recipe_hash,
                "OCR_Unit_Text": suggested_unit,
                "Candidate_Rank": "",
                "Candidate_Unit": "",
                "Candidate_Workflow_ID": "",
                "Candidate_Superfaction": "",
                "Candidate_Faction": "",
                "Candidate_Score": 0,
                "Approved": "",
                "Approved_Workflow_ID": "",
                "Approved_Superfaction": "",
                "Approved_Faction": "",
                "Approved_Unit": "",
                "Resolver_Status": "Needs Manual Review",
                "Priority": priority,
                "File_Count": file_count,
                "Total_Rows": total_rows,
                "Notes": "No candidate found.",
            })
            continue

        for rank, candidate in enumerate(candidates, start=1):
            records.append({
                "Recipe_Hash": recipe_hash,
                "OCR_Unit_Text": suggested_unit,
                "Candidate_Rank": rank,
                "Candidate_Unit": candidate["Candidate_Unit"],
                "Candidate_Workflow_ID": candidate["Candidate_Workflow_ID"],
                "Candidate_Superfaction": candidate["Candidate_Superfaction"],
                "Candidate_Faction": candidate["Candidate_Faction"],
                "Candidate_Score": candidate["Candidate_Score"],
                "Approved": "",
                "Approved_Workflow_ID": "",
                "Approved_Superfaction": "",
                "Approved_Faction": "",
                "Approved_Unit": "",
                "Resolver_Status": "Pending",
                "Priority": priority,
                "File_Count": file_count,
                "Total_Rows": total_rows,
                "Notes": "",
            })

    candidates_df = pd.DataFrame(records)

    candidates_df = candidates_df.sort_values(
        by=[
            "Recipe_Hash",
            "Candidate_Rank",
        ],
        ascending=[
            True,
            True,
        ],
    )

    candidates_df.to_csv(CANDIDATES_FILE, index=False)

    print()
    print("SUMMARY")
    print("-" * 60)
    print(f"Recipe groups ............ {index_df['Recipe_Hash'].nunique()}")
    print(f"Canonical units .......... {len(canonical_df)}")
    print(f"Candidate rows ........... {len(candidates_df)}")
    print(f"Needs manual review ...... {(candidates_df['Resolver_Status'] == 'Needs Manual Review').sum()}")
    print()

    print("TOP CANDIDATES")
    print("-" * 60)

    preview = candidates_df[
        [
            "Recipe_Hash",
            "OCR_Unit_Text",
            "Candidate_Rank",
            "Candidate_Unit",
            "Candidate_Score",
        ]
    ].head(30)

    print(preview.to_string(index=False))

    print()
    print("Candidate file written:")
    print(CANDIDATES_FILE)

    print()
    print("=" * 60)
    print("CANDIDATE BUILD COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()