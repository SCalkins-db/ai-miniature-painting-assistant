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
from collections import Counter
from src.core.paths import PROJECT_ROOT, SRC_DIR, DATA_DIR, REGISTRIES_CSV_DIR, REGISTRIES_XLSX_DIR, MAPPINGS_DIR, REPORTS_DIR, SOURCE_DOCUMENTS_DIR, AUDIT_DIR, CSV_DIR, XLSX_DIR, SOURCE_DOCS_DIR

import pandas as pd

from src.utils.normalization import build_key


DATA_DIR = PROJECT_ROOT / "data"
REGISTRY_DIR = DATA_DIR / "registries_csv"
REPORTS_DIR = DATA_DIR / "reports"

OUTPUT_CSV = REPORTS_DIR / "missing_color_clusters.csv"
OUTPUT_JSON = REPORTS_DIR / "missing_color_clusters.json"
OUTPUT_MD = REPORTS_DIR / "missing_color_clusters.md"

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


def has_color(row) -> bool:
    return not is_blank(row.get("Hex")) and not is_blank(row.get("RGB"))


def load_registry_rows():
    rows = []

    for file_path in sorted(REGISTRY_DIR.glob("*.csv")):
        df = pd.read_csv(file_path)

        missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
        if missing_columns:
            print(f"Skipping non-registry file: {file_path.name}")
            continue

        for _, row in df.iterrows():
            rows.append({
                "Registry_File": file_path.name,
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
                "Cluster_Key": build_key(
                    row.get("Company", ""),
                    row.get("Paint_Name", ""),
                ),
            })

    return rows


def determine_cluster_status(rows):
    total = len(rows)
    with_color = sum(1 for row in rows if has_color(row))
    missing = total - with_color

    if missing == 0:
        return "COMPLETE"

    if with_color > 0 and missing > 0:
        return "CAN_PROPAGATE"

    return "ENTIRE_CLUSTER_MISSING"


def summarize_cluster(cluster_key, rows):
    status = determine_cluster_status(rows)

    rows_with_color = [row for row in rows if has_color(row)]
    rows_missing_color = [row for row in rows if not has_color(row)]

    example_color_row = rows_with_color[0] if rows_with_color else {}

    company = rows[0].get("Company", "")
    paint_name = rows[0].get("Paint_Name", "")

    product_lines = sorted({
        str(row.get("Product_Line", "")).strip()
        for row in rows
        if not is_blank(row.get("Product_Line"))
    })

    paint_types = sorted({
        str(row.get("Paint_Type", "")).strip()
        for row in rows
        if not is_blank(row.get("Paint_Type"))
    })

    paint_ids = sorted({
        str(row.get("Paint_ID", "")).strip()
        for row in rows
        if not is_blank(row.get("Paint_ID"))
    })

    missing_paint_ids = sorted({
        str(row.get("Paint_ID", "")).strip()
        for row in rows_missing_color
        if not is_blank(row.get("Paint_ID"))
    })

    if status == "CAN_PROPAGATE":
        action = "Copy existing Hex/RGB to missing rows in this same-company paint-name cluster."
    elif status == "ENTIRE_CLUSTER_MISSING":
        action = "Research this color once, then apply Hex/RGB to every row in the cluster if product lines represent the same color."
    else:
        action = "No action needed."

    return {
        "Cluster_Key": cluster_key,
        "Company": company,
        "Paint_Name": paint_name,
        "Cluster_Status": status,
        "Cluster_Size": len(rows),
        "Rows_With_Color": len(rows_with_color),
        "Rows_Missing_Color": len(rows_missing_color),
        "Product_Lines": " | ".join(product_lines),
        "Paint_Types": " | ".join(paint_types),
        "Paint_IDs": " | ".join(paint_ids),
        "Missing_Paint_IDs": " | ".join(missing_paint_ids),
        "Example_Hex": example_color_row.get("Hex", ""),
        "Example_RGB": example_color_row.get("RGB", ""),
        "Example_Source_Paint_ID": example_color_row.get("Paint_ID", ""),
        "Recommended_Action": action,
    }


def build_markdown(summary, status_counts, company_counts, largest_missing):
    lines = []

    lines.append("# Missing Color Cluster Report")
    lines.append("")
    lines.append("## Overall Summary")
    lines.append("")
    lines.append(f"- Total registry rows checked: {summary['total_registry_rows']}")
    lines.append(f"- Total clusters found: {summary['total_clusters']}")
    lines.append(f"- Complete clusters: {summary['complete_clusters']}")
    lines.append(f"- Can propagate clusters: {summary['can_propagate_clusters']}")
    lines.append(f"- Entire cluster missing: {summary['entire_cluster_missing']}")
    lines.append(f"- Total rows missing Hex/RGB: {summary['total_rows_missing_color']}")
    lines.append("")

    lines.append("## Cluster Status Breakdown")
    lines.append("")
    lines.append("| Cluster Status | Count |")
    lines.append("|---|---:|")
    for status, count in status_counts.items():
        lines.append(f"| {status} | {count} |")

    lines.append("")
    lines.append("## Missing Rows by Company")
    lines.append("")
    lines.append("| Company | Missing Rows |")
    lines.append("|---|---:|")
    for company, count in company_counts.items():
        lines.append(f"| {company} | {count} |")

    lines.append("")
    lines.append("## Largest Missing Clusters")
    lines.append("")
    lines.append("| Company | Paint Name | Missing Rows | Product Lines | Action |")
    lines.append("|---|---|---:|---|---|")
    for row in largest_missing:
        lines.append(
            f"| {row['Company']} | {row['Paint_Name']} | "
            f"{row['Rows_Missing_Color']} | {row['Product_Lines']} | "
            f"{row['Recommended_Action']} |"
        )

    lines.append("")
    lines.append("## Recommended Workflow")
    lines.append("")
    lines.append("1. Filter the CSV by `CAN_PROPAGATE` first. These are easy wins.")
    lines.append("2. Then filter by `ENTIRE_CLUSTER_MISSING` and prioritize clusters with multiple rows.")
    lines.append("3. Research one Hex/RGB value per cluster instead of one value per row.")
    lines.append("4. Do not blindly copy values across product lines if the paint is a medium, varnish, primer, metallic, effect paint, or technical paint.")
    lines.append("")

    return "\n".join(lines)


def main():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    rows = load_registry_rows()

    clusters = {}
    for row in rows:
        clusters.setdefault(row["Cluster_Key"], []).append(row)

    cluster_summaries = [
        summarize_cluster(cluster_key, cluster_rows)
        for cluster_key, cluster_rows in clusters.items()
    ]

    output_df = pd.DataFrame(cluster_summaries)
    output_df = output_df.sort_values(
        by=["Cluster_Status", "Company", "Paint_Name"],
        ascending=[True, True, True],
    )

    output_df.to_csv(OUTPUT_CSV, index=False)

    status_counts = Counter(output_df["Cluster_Status"])
    company_counts = Counter()

    for row in rows:
        if not has_color(row):
            company_counts[row.get("Company", "")] += 1

    total_missing = sum(1 for row in rows if not has_color(row))

    summary = {
        "report_name": "Missing Color Cluster Report",
        "total_registry_rows": len(rows),
        "total_clusters": len(cluster_summaries),
        "complete_clusters": status_counts.get("COMPLETE", 0),
        "can_propagate_clusters": status_counts.get("CAN_PROPAGATE", 0),
        "entire_cluster_missing": status_counts.get("ENTIRE_CLUSTER_MISSING", 0),
        "total_rows_missing_color": total_missing,
        "status_counts": dict(status_counts),
        "missing_rows_by_company": dict(company_counts),
        "output_csv": str(OUTPUT_CSV),
        "output_markdown": str(OUTPUT_MD),
    }

    with open(OUTPUT_JSON, "w", encoding="utf-8") as json_file:
        json.dump(summary, json_file, indent=4)

    largest_missing = (
        output_df[output_df["Rows_Missing_Color"] > 0]
        .sort_values(by="Rows_Missing_Color", ascending=False)
        .head(25)
        .to_dict(orient="records")
    )

    markdown = build_markdown(
        summary=summary,
        status_counts=status_counts,
        company_counts=company_counts,
        largest_missing=largest_missing,
    )

    with open(OUTPUT_MD, "w", encoding="utf-8") as md_file:
        md_file.write(markdown)

    print("MISSING COLOR CLUSTER AUDIT")
    print("---------------------------")
    print(f"Registry rows checked: {len(rows)}")
    print(f"Clusters found: {len(cluster_summaries)}")
    print(f"Complete clusters: {summary['complete_clusters']}")
    print(f"Can propagate clusters: {summary['can_propagate_clusters']}")
    print(f"Entire cluster missing: {summary['entire_cluster_missing']}")
    print(f"Rows missing Hex/RGB: {summary['total_rows_missing_color']}")
    print()
    print(f"CSV saved to: {OUTPUT_CSV}")
    print(f"JSON saved to: {OUTPUT_JSON}")
    print(f"Markdown saved to: {OUTPUT_MD}")


if __name__ == "__main__":
    main()
