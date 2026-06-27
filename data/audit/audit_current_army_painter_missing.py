from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
REGISTRY_DIR = DATA_DIR / "registries_xlsx"
REPORTS_DIR = DATA_DIR / "reports"

ARMY_FILE = REGISTRY_DIR / "Army_Painter_registry_26.0.14_speedpaint_doc_enriched.xlsx"

OUTPUT_XLSX = REPORTS_DIR / "current_army_painter_missing_hex_audit.xlsx"
OUTPUT_CSV = REPORTS_DIR / "current_army_painter_missing_hex_audit.csv"


def is_blank(value):
    return pd.isna(value) or str(value).strip() == "" or str(value).strip().lower() in {
        "nan",
        "none",
        "null",
    }


def classify_reason(row):
    product_line = str(row.get("Product_Line", "")).lower()
    paint_type = str(row.get("Paint_Type", "")).lower()
    paint_name = str(row.get("Paint_Name", "")).lower()
    notes = str(row.get("Notes", "")).lower()

    text = " ".join([product_line, paint_type, paint_name, notes])

    if "medium" in text:
        return "Medium / no pigment or special additive"

    if "varnish" in text:
        return "Varnish / no normal color value"

    if "primer" in text:
        return "Primer / may need separate source"

    if "metallic" in text or "gold" in text or "silver" in text or "bronze" in text or "copper" in text:
        return "Metallic / RGB less reliable"

    if "wash" in text or "shade" in text or "tone" in text or "shader" in text:
        return "Wash/Shade/Ink / transparent color"

    if "effect" in text or "blood" in text or "rust" in text or "goo" in text or "slime" in text:
        return "Effect paint / needs manual source"

    if "speedpaint" in text:
        return "Speedpaint / comparison data missing or unresolved"

    if "air" in text:
        return "Air paint / needs Air equivalent source"

    if "fanatic" in text or "acrylic" in text:
        return "Standard acrylic / should be enrichable"

    return "Unknown / manual review"


def main():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    sheets = pd.read_excel(ARMY_FILE, sheet_name=None)
    army_df = sheets["ArmyPainter_All"]

    missing_df = army_df[
        army_df["Hex"].apply(is_blank) | army_df["RGB"].apply(is_blank)
    ].copy()

    missing_df["Likely_Reason"] = missing_df.apply(classify_reason, axis=1)

    summary_by_product_line = (
        missing_df.groupby("Product_Line")
        .size()
        .reset_index(name="Missing_Count")
        .sort_values("Missing_Count", ascending=False)
    )

    summary_by_paint_type = (
        missing_df.groupby("Paint_Type")
        .size()
        .reset_index(name="Missing_Count")
        .sort_values("Missing_Count", ascending=False)
    )

    summary_by_reason = (
        missing_df.groupby("Likely_Reason")
        .size()
        .reset_index(name="Missing_Count")
        .sort_values("Missing_Count", ascending=False)
    )

    summary = pd.DataFrame([
        {"Metric": "Total Army Painter rows", "Value": len(army_df)},
        {"Metric": "Rows with Hex/RGB", "Value": len(army_df) - len(missing_df)},
        {"Metric": "Rows missing Hex/RGB", "Value": len(missing_df)},
    ])

    columns_to_show = [
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
        ]
        if col in missing_df.columns
    ]

    missing_export = missing_df[columns_to_show]

    with pd.ExcelWriter(OUTPUT_XLSX, engine="openpyxl") as writer:
        summary.to_excel(writer, sheet_name="Summary", index=False)
        summary_by_product_line.to_excel(writer, sheet_name="By_Product_Line", index=False)
        summary_by_paint_type.to_excel(writer, sheet_name="By_Paint_Type", index=False)
        summary_by_reason.to_excel(writer, sheet_name="By_Reason", index=False)
        missing_export.to_excel(writer, sheet_name="Missing_Rows", index=False)

    missing_export.to_csv(OUTPUT_CSV, index=False)

    print("CURRENT ARMY PAINTER MISSING HEX/RGB AUDIT")
    print("------------------------------------------")
    print(f"Total Army Painter rows: {len(army_df)}")
    print(f"Rows with Hex/RGB: {len(army_df) - len(missing_df)}")
    print(f"Rows missing Hex/RGB: {len(missing_df)}")
    print()
    print("Missing by reason:")
    print(summary_by_reason.to_string(index=False))
    print()
    print("Missing by product line:")
    print(summary_by_product_line.to_string(index=False))
    print()
    print("Missing by paint type:")
    print(summary_by_paint_type.to_string(index=False))
    print()
    print(f"Excel saved to: {OUTPUT_XLSX}")
    print(f"CSV saved to: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()