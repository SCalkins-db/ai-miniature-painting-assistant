from pathlib import Path
import json
import pandas as pd

from src.utils.normalization import build_key


PROJECT_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_DIR = PROJECT_ROOT / "data" / "registries_csv"
REPORTS_DIR = PROJECT_ROOT / "data" / "reports"

OUTPUT_FILE = REPORTS_DIR / "missing_color_data_report.json"


REQUIRED_COLUMNS = [
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


def classify_missing(row) -> str:
    missing_hex = is_blank(row.get("Hex"))
    missing_rgb = is_blank(row.get("RGB"))

    if missing_hex and missing_rgb:
        return "Missing Hex and RGB"

    if missing_hex:
        return "Missing Hex Only"

    if missing_rgb:
        return "Missing RGB Only"

    return "Complete"


def audit_registry(file_path: Path) -> dict:
    df = pd.read_csv(file_path)

    missing_columns = [
        col for col in REQUIRED_COLUMNS
        if col not in df.columns
    ]

    registry_report = {
        "file": file_path.name,
        "total_rows": len(df),
        "missing_columns": missing_columns,
        "summary": {
            "complete": 0,
            "missing_hex_only": 0,
            "missing_rgb_only": 0,
            "missing_hex_and_rgb": 0,
            "total_problem_rows": 0,
        },
        "problem_rows": [],
    }

    if missing_columns:
        registry_report["error"] = "Registry is missing required columns."
        return registry_report

    for index, row in df.iterrows():
        qualifier = classify_missing(row)

        if qualifier == "Complete":
            registry_report["summary"]["complete"] += 1
            continue

        if qualifier == "Missing Hex Only":
            registry_report["summary"]["missing_hex_only"] += 1

        elif qualifier == "Missing RGB Only":
            registry_report["summary"]["missing_rgb_only"] += 1

        elif qualifier == "Missing Hex and RGB":
            registry_report["summary"]["missing_hex_and_rgb"] += 1

        registry_report["summary"]["total_problem_rows"] += 1

        registry_report["problem_rows"].append({
            "row_number": int(index + 2),
            "qualifier": qualifier,
            "canonical_key": build_key(
                row.get("Company"),
                row.get("Product_Line"),
                row.get("Paint_Name"),
            ),
            "paint_id": row.get("Paint_ID"),
            "company": row.get("Company"),
            "brand": row.get("Brand"),
            "product_line": row.get("Product_Line"),
            "paint_name": row.get("Paint_Name"),
            "paint_type": row.get("Paint_Type"),
            "hex": None if is_blank(row.get("Hex")) else row.get("Hex"),
            "rgb": None if is_blank(row.get("RGB")) else row.get("RGB"),
            "status": row.get("Status"),
            "source": row.get("Source"),
            "notes": row.get("Notes"),
        })

    return registry_report


def main():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    registry_files = sorted(REGISTRY_DIR.glob("*.csv"))

    full_report = {
        "report_name": "Missing Hex/RGB Registry Audit",
        "registry_directory": str(REGISTRY_DIR),
        "total_registries_checked": len(registry_files),
        "registries": [],
        "overall_summary": {
            "total_rows": 0,
            "complete": 0,
            "missing_hex_only": 0,
            "missing_rgb_only": 0,
            "missing_hex_and_rgb": 0,
            "total_problem_rows": 0,
        },
    }

    for file_path in registry_files:
        registry_report = audit_registry(file_path)
        full_report["registries"].append(registry_report)

        summary = registry_report.get("summary", {})

        full_report["overall_summary"]["total_rows"] += registry_report.get("total_rows", 0)
        full_report["overall_summary"]["complete"] += summary.get("complete", 0)
        full_report["overall_summary"]["missing_hex_only"] += summary.get("missing_hex_only", 0)
        full_report["overall_summary"]["missing_rgb_only"] += summary.get("missing_rgb_only", 0)
        full_report["overall_summary"]["missing_hex_and_rgb"] += summary.get("missing_hex_and_rgb", 0)
        full_report["overall_summary"]["total_problem_rows"] += summary.get("total_problem_rows", 0)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as json_file:
        json.dump(full_report, json_file, indent=4)

    print("MISSING HEX/RGB JSON AUDIT")
    print("--------------------------")
    print(f"Registries checked: {full_report['total_registries_checked']}")
    print(f"Total rows: {full_report['overall_summary']['total_rows']}")
    print(f"Complete rows: {full_report['overall_summary']['complete']}")
    print(f"Problem rows: {full_report['overall_summary']['total_problem_rows']}")
    print(f"Missing Hex only: {full_report['overall_summary']['missing_hex_only']}")
    print(f"Missing RGB only: {full_report['overall_summary']['missing_rgb_only']}")
    print(f"Missing Hex and RGB: {full_report['overall_summary']['missing_hex_and_rgb']}")
    print()
    print(f"Report saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
