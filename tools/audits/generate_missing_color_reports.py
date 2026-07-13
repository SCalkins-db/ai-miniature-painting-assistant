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
import pandas as pd
from src.core.paths import PROJECT_ROOT, SRC_DIR, DATA_DIR, REGISTRIES_CSV_DIR, REGISTRIES_XLSX_DIR, MAPPINGS_DIR, REPORTS_DIR, SOURCE_DOCUMENTS_DIR, AUDIT_DIR, CSV_DIR, XLSX_DIR, SOURCE_DOCS_DIR


DATA_DIR = PROJECT_ROOT / "data"
REGISTRY_DIR = DATA_DIR / "registries_xlsx"
REPORTS_DIR = DATA_DIR / "reports" / "missing_color_reports"

REPORTS_DIR.mkdir(parents=True, exist_ok=True)


REGISTRY_FILES = {
    "Army Painter": REGISTRY_DIR / "Army_Painter_registry_26.0.14_speedpaint_doc_enriched.xlsx",
    "Games Workshop": REGISTRY_DIR / "GW_registry_26.0.11.xlsx",
    "Vallejo": REGISTRY_DIR / "Vallejo_registry_26.0.9.xlsx",
    "AK Interactive": REGISTRY_DIR / "AK_Interactive_registry_26.0.6.xlsx",
    "Pro Acryl": REGISTRY_DIR / "Pro_Acryl_registry_26.0.7.xlsx",
}


def is_blank(value):
    return pd.isna(value) or str(value).strip() == "" or str(value).strip().lower() in {
        "nan", "none", "null"
    }


def classify_reason(row):
    text = " ".join([
        str(row.get("Product_Line", "")),
        str(row.get("Paint_Type", "")),
        str(row.get("Paint_Name", "")),
        str(row.get("Notes", "")),
    ]).lower()

    if "medium" in text:
        return "Medium / additive, low priority"
    if "varnish" in text:
        return "Varnish / no normal color value"
    if "primer" in text:
        return "Primer / separate source needed"
    if "metallic" in text or any(x in text for x in ["gold", "silver", "bronze", "copper"]):
        return "Metallic / manual source recommended"
    if any(x in text for x in ["wash", "shade", "tone", "shader", "ink"]):
        return "Wash/Shade/Ink / transparent color"
    if any(x in text for x in ["effect", "blood", "rust", "goo", "slime"]):
        return "Effect paint / manual source recommended"
    if "speedpaint" in text:
        return "Speedpaint / comparison source needed"
    if "air" in text:
        return "Air paint / air equivalent source needed"
    if "acrylic" in text or "fanatic" in text:
        return "Standard acrylic / should be fillable"

    return "Unknown / manual review"


def assign_priority(reason):
    if "Standard acrylic" in reason:
        return "High"
    if "Speedpaint" in reason:
        return "High"
    if "Air paint" in reason:
        return "Medium"
    if "Metallic" in reason:
        return "Medium"
    if "Primer" in reason:
        return "Low"
    if "Wash" in reason or "Effect" in reason:
        return "Low"
    if "Medium" in reason or "Varnish" in reason:
        return "Ignore / Very Low"
    return "Manual Review"


def get_main_sheet(path):
    sheets = pd.read_excel(path, sheet_name=None)

    preferred = [
        "ArmyPainter_All",
        "Vallejo_All",
        "AK_All",
        "ProAcryl_All",
        "GW_All",
    ]

    for name in preferred:
        if name in sheets:
            return name, sheets[name]

    first_name = list(sheets.keys())[0]
    return first_name, sheets[first_name]


def write_markdown(company, missing_df, output_path):
    lines = []
    lines.append(f"# {company} Missing Hex/RGB Report")
    lines.append("")
    lines.append(f"Total missing paints: {len(missing_df)}")
    lines.append("")

    for reason, group in missing_df.groupby("Likely_Reason"):
        lines.append(f"## {reason} ({len(group)})")
        lines.append("")
        lines.append("| Paint Name | Product Line | Paint Type | Priority | Source | Notes |")
        lines.append("|---|---|---|---|---|---|")

        for _, row in group.iterrows():
            lines.append(
                f"| {row.get('Paint_Name', '')} "
                f"| {row.get('Product_Line', '')} "
                f"| {row.get('Paint_Type', '')} "
                f"| {row.get('Priority', '')} "
                f"| {row.get('Source', '')} "
                f"| {str(row.get('Notes', '')).replace('|', '/')} |"
            )

        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")


def audit_registry(company, path):
    if not path.exists():
        print(f"SKIPPED {company}: missing file {path}")
        return None

    sheet_name, df = get_main_sheet(path)

    missing_df = df[
        df["Hex"].apply(is_blank) | df["RGB"].apply(is_blank)
    ].copy()

    if missing_df.empty:
        return {
            "Company": company,
            "Total_Rows": len(df),
            "Missing": 0,
            "Workbook": path.name,
            "Sheet": sheet_name,
        }

    missing_df["Likely_Reason"] = missing_df.apply(classify_reason, axis=1)
    missing_df["Priority"] = missing_df["Likely_Reason"].apply(assign_priority)

    columns = [
        col for col in [
            "Paint_ID",
            "Company",
            "Brand",
            "Product_Line",
            "Paint_Type",
            "Paint_Name",
            "Hex",
            "RGB",
            "Status",
            "Source",
            "Notes",
            "Likely_Reason",
            "Priority",
        ]
        if col in missing_df.columns
    ]

    missing_export = missing_df[columns]

    excel_path = REPORTS_DIR / f"{company.replace(' ', '_')}_missing_hex_rgb_report.xlsx"
    md_path = REPORTS_DIR / f"{company.replace(' ', '_')}_missing_hex_rgb_report.md"
    csv_path = REPORTS_DIR / f"{company.replace(' ', '_')}_missing_hex_rgb_report.csv"

    by_reason = (
        missing_df.groupby("Likely_Reason")
        .size()
        .reset_index(name="Missing_Count")
        .sort_values("Missing_Count", ascending=False)
    )

    by_product_line = (
        missing_df.groupby("Product_Line")
        .size()
        .reset_index(name="Missing_Count")
        .sort_values("Missing_Count", ascending=False)
    )

    by_paint_type = (
        missing_df.groupby("Paint_Type")
        .size()
        .reset_index(name="Missing_Count")
        .sort_values("Missing_Count", ascending=False)
    )

    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        pd.DataFrame([
            {"Metric": "Company", "Value": company},
            {"Metric": "Workbook", "Value": path.name},
            {"Metric": "Sheet", "Value": sheet_name},
            {"Metric": "Total Rows", "Value": len(df)},
            {"Metric": "Missing Hex/RGB", "Value": len(missing_df)},
        ]).to_excel(writer, sheet_name="Summary", index=False)

        by_reason.to_excel(writer, sheet_name="By_Reason", index=False)
        by_product_line.to_excel(writer, sheet_name="By_Product_Line", index=False)
        by_paint_type.to_excel(writer, sheet_name="By_Paint_Type", index=False)
        missing_export.to_excel(writer, sheet_name="Exact_Missing_Paints", index=False)

    missing_export.to_csv(csv_path, index=False)
    write_markdown(company, missing_export, md_path)

    return {
        "Company": company,
        "Total_Rows": len(df),
        "Missing": len(missing_df),
        "Workbook": path.name,
        "Sheet": sheet_name,
        "Excel_Report": excel_path.name,
        "Markdown_Report": md_path.name,
        "CSV_Report": csv_path.name,
    }


def main():
    summaries = []

    for company, path in REGISTRY_FILES.items():
        result = audit_registry(company, path)
        if result:
            summaries.append(result)

    summary_df = pd.DataFrame(summaries)
    summary_path = REPORTS_DIR / "ALL_missing_hex_rgb_summary.xlsx"
    summary_csv = REPORTS_DIR / "ALL_missing_hex_rgb_summary.csv"

    summary_df.to_excel(summary_path, index=False)
    summary_df.to_csv(summary_csv, index=False)

    print("MISSING HEX/RGB HUMAN READABLE REPORTS")
    print("-------------------------------------")
    print(summary_df.to_string(index=False))
    print()
    print(f"Reports saved to: {REPORTS_DIR}")


if __name__ == "__main__":
    main()
