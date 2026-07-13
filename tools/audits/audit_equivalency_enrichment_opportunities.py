# Allow direct execution from project root or with python -m
import sys
from pathlib import Path

_project_root = Path(__file__).resolve()
while _project_root.parent != _project_root:
    if (_project_root / "src").exists() and (_project_root / "data").exists():
        break
    _project_root = _project_root.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

# Allow direct execution from the project root, e.g. python src/debug/script.py
import sys
from pathlib import Path

_project_root = Path(__file__).resolve()
while _project_root.parent != _project_root:
    if (_project_root / "src").exists() and (_project_root / "data").exists():
        break
    _project_root = _project_root.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from pathlib import Path
import json
import pandas as pd
from src.core.paths import PROJECT_ROOT, SRC_DIR, DATA_DIR, REGISTRIES_CSV_DIR, REGISTRIES_XLSX_DIR, MAPPINGS_DIR, REPORTS_DIR, SOURCE_DOCUMENTS_DIR, AUDIT_DIR, CSV_DIR, XLSX_DIR, SOURCE_DOCS_DIR

from src.utils.normalization import build_key

DATA_DIR = PROJECT_ROOT / "data"
REGISTRY_DIR = DATA_DIR / "registries_csv"
REPORTS_DIR = DATA_DIR / "reports"

EQUIVALENCY_FILE = DATA_DIR / "paint_equivalency_database.csv"
OUTPUT_JSON = REPORTS_DIR / "equivalency_enrichment_opportunities.json"
OUTPUT_CSV = REPORTS_DIR / "equivalency_enrichment_opportunities.csv"


REGISTRY_COLUMNS = [
    "Paint_ID",
    "Company",
    "Brand",
    "Product_Line",
    "Paint_Name",
    "Hex",
    "RGB",
    "Paint_Type",
    "Status",
    "Source",
    "Notes",
]


def is_blank(value) -> bool:
    if pd.isna(value):
        return True

    value = str(value).strip()
    return value == "" or value.lower() in {"nan", "none", "null"}


def has_color_data(record) -> bool:
    return not is_blank(record.get("Hex")) and not is_blank(record.get("RGB"))


def similarity_to_number(value) -> float:
    value = str(value).replace("%", "").strip()

    try:
        return float(value)
    except ValueError:
        return 0.0


def load_registries():
    registry_rows = []
    exact_lookup = {}
    loose_lookup = {}

    for file_path in sorted(REGISTRY_DIR.glob("*.csv")):
        df = pd.read_csv(file_path)

        for column in REGISTRY_COLUMNS:
            if column not in df.columns:
                df[column] = ""

        for _, row in df.iterrows():
            record = {
                "registry_file": file_path.name,
                "Paint_ID": row.get("Paint_ID", ""),
                "Company": row.get("Company", ""),
                "Brand": row.get("Brand", ""),
                "Product_Line": row.get("Product_Line", ""),
                "Paint_Name": row.get("Paint_Name", ""),
                "Hex": row.get("Hex", ""),
                "RGB": row.get("RGB", ""),
                "Paint_Type": row.get("Paint_Type", ""),
                "Status": row.get("Status", ""),
                "Source": row.get("Source", ""),
                "Notes": row.get("Notes", ""),
            }

            registry_rows.append(record)

            exact_key = build_key(
                record["Company"],
                record["Product_Line"],
                record["Paint_Name"],
            )

            loose_key = build_key(
                record["Company"],
                record["Paint_Name"],
            )

            exact_lookup.setdefault(exact_key, []).append(record)
            loose_lookup.setdefault(loose_key, []).append(record)

    return registry_rows, exact_lookup, loose_lookup


def find_source_equivalencies(equivalencies, missing):
    """
    First tries exact Company + Product_Line + Paint_Name.
    Falls back to Company + Paint_Name because product lines are still being normalized.
    """

    missing_exact_key = build_key(
        missing.get("Company"),
        missing.get("Product_Line"),
        missing.get("Paint_Name"),
    )

    missing_loose_key = build_key(
        missing.get("Company"),
        missing.get("Paint_Name"),
    )

    exact_matches = equivalencies[
        equivalencies["_source_exact_key"] == missing_exact_key
    ]

    if not exact_matches.empty:
        return exact_matches

    return equivalencies[
        equivalencies["_source_loose_key"] == missing_loose_key
    ]


def find_registry_equivalent(equiv, exact_lookup, loose_lookup):
    """
    Finds equivalent paint in the loaded registries.
    First tries exact Company + Product_Line + Paint_Name.
    Falls back to Company + Paint_Name.
    """

    exact_key = build_key(
        equiv.get("Equivalent_Company"),
        equiv.get("Equivalent_Product_Line"),
        equiv.get("Equivalent_Paint_Name"),
    )

    loose_key = build_key(
        equiv.get("Equivalent_Company"),
        equiv.get("Equivalent_Paint_Name"),
    )

    matches = exact_lookup.get(exact_key, [])

    if matches:
        return matches

    return loose_lookup.get(loose_key, [])

def find_same_company_name_matches(missing, registry_rows):
    matches = []

    for row in registry_rows:
        if row == missing:
            continue

        if not has_color_data(row):
            continue

        same_company = build_key(row.get("Company")) == build_key(missing.get("Company"))
        same_name = build_key(row.get("Paint_Name")) == build_key(missing.get("Paint_Name"))

        if same_company and same_name:
            matches.append(row)

    return matches

def main():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    if not EQUIVALENCY_FILE.exists():
        raise FileNotFoundError(f"Missing equivalency file: {EQUIVALENCY_FILE}")

    registry_rows, exact_lookup, loose_lookup = load_registries()
    equivalencies = pd.read_csv(EQUIVALENCY_FILE)

    for column in [
        "Source_Company",
        "Source_Product_Line",
        "Source_Paint_Name",
        "Equivalent_Company",
        "Equivalent_Product_Line",
        "Equivalent_Paint_Name",
        "Similarity_Percent",
        "Confidence",
        "Match_Type",
        "Source",
        "Notes",
    ]:
        if column not in equivalencies.columns:
            equivalencies[column] = ""

    equivalencies["_source_exact_key"] = equivalencies.apply(
        lambda row: build_key(
            row.get("Source_Company"),
            row.get("Source_Product_Line"),
            row.get("Source_Paint_Name"),
        ),
        axis=1,
    )

    equivalencies["_source_loose_key"] = equivalencies.apply(
        lambda row: build_key(
            row.get("Source_Company"),
            row.get("Source_Paint_Name"),
        ),
        axis=1,
    )

    missing_registry_rows = [
        row for row in registry_rows
        if is_blank(row.get("Hex")) or is_blank(row.get("RGB"))
    ]

    opportunities = []

    for missing in missing_registry_rows:

        same_name_matches = find_same_company_name_matches(missing, registry_rows)

        if same_name_matches:
            matched = same_name_matches[0]

            opportunities.append({
                "missing_registry_file": missing.get("registry_file"),
                "missing_paint_id": missing.get("Paint_ID"),
                "missing_company": missing.get("Company"),
                "missing_product_line": missing.get("Product_Line"),
                "missing_paint_name": missing.get("Paint_Name"),
                "missing_hex": missing.get("Hex"),
                "missing_rgb": missing.get("RGB"),

                "equivalent_paint_id": matched.get("Paint_ID"),
                "equivalent_company": matched.get("Company"),
                "equivalent_product_line": matched.get("Product_Line"),
                "equivalent_paint_name": matched.get("Paint_Name"),
                "equivalent_hex": matched.get("Hex"),
                "equivalent_rgb": matched.get("RGB"),

                "similarity_percent": 100,
                "confidence": "High",
                "match_type": "Same Company Same Paint Name",
                "source": "Registry Cross Product-Line Match",
                "notes": (
                    f"Matched same company and paint name across product lines: "
                    f"{matched.get('Product_Line')}"
                ),
            })

            continue

        possible_equivs = find_source_equivalencies(equivalencies, missing)

        best_match = None

        for _, equiv in possible_equivs.iterrows():
            registry_matches = find_registry_equivalent(
                equiv,
                exact_lookup,
                loose_lookup,
            )

            for matched_registry_paint in registry_matches:
                if not has_color_data(matched_registry_paint):
                    continue

                candidate = {
                    "missing_registry_file": missing.get("registry_file"),
                    "missing_paint_id": missing.get("Paint_ID"),
                    "missing_company": missing.get("Company"),
                    "missing_product_line": missing.get("Product_Line"),
                    "missing_paint_name": missing.get("Paint_Name"),
                    "missing_hex": missing.get("Hex"),
                    "missing_rgb": missing.get("RGB"),

                    "equivalent_paint_id": matched_registry_paint.get("Paint_ID"),
                    "equivalent_company": matched_registry_paint.get("Company"),
                    "equivalent_product_line": matched_registry_paint.get("Product_Line"),
                    "equivalent_paint_name": matched_registry_paint.get("Paint_Name"),
                    "equivalent_hex": matched_registry_paint.get("Hex"),
                    "equivalent_rgb": matched_registry_paint.get("RGB"),

                    "similarity_percent": equiv.get("Similarity_Percent"),
                    "confidence": equiv.get("Confidence"),
                    "match_type": equiv.get("Match_Type"),
                    "source": equiv.get("Source"),
                    "notes": equiv.get("Notes"),
                }

                if best_match is None:
                    best_match = candidate
                    continue

                old_score = similarity_to_number(best_match.get("similarity_percent"))
                new_score = similarity_to_number(candidate.get("similarity_percent"))

                if new_score > old_score:
                    best_match = candidate

        if best_match:
            opportunities.append(best_match)

    opportunities_df = pd.DataFrame(opportunities)
    opportunities_df.to_csv(OUTPUT_CSV, index=False)

    report = {
        "report_name": "Equivalency Enrichment Opportunities",
        "missing_color_rows_checked": len(missing_registry_rows),
        "enrichment_opportunities_found": len(opportunities),
        "remaining_without_equivalency_match": len(missing_registry_rows) - len(opportunities),
        "output_csv": str(OUTPUT_CSV),
        "opportunities": opportunities,
    }

    with open(OUTPUT_JSON, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=4)

    print("EQUIVALENCY ENRICHMENT OPPORTUNITY AUDIT")
    print("----------------------------------------")
    print(f"Missing color rows checked: {len(missing_registry_rows)}")
    print(f"Can be enriched from equivalencies: {len(opportunities)}")
    print(f"Still unresolved: {len(missing_registry_rows) - len(opportunities)}")
    print()
    print(f"CSV saved to: {OUTPUT_CSV}")
    print(f"JSON saved to: {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
