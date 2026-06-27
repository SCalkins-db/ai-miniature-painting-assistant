from pathlib import Path
import re
import pandas as pd


PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
REGISTRY_DIR = DATA_DIR / "registries_xlsx"

INPUT_FILE = REGISTRY_DIR / "Army_Painter_registry_26.0.14_speedpaint_doc_enriched.xlsx"
OUTPUT_FILE = REGISTRY_DIR / "Army_Painter_registry_26.0.15_inheritance_enriched.xlsx"


def is_blank(value):
    return pd.isna(value) or str(value).strip() == "" or str(value).strip().lower() in {
        "nan", "none", "null"
    }


def has_color(row):
    return not is_blank(row.get("Hex")) and not is_blank(row.get("RGB"))


def normalize_name(value):
    if pd.isna(value):
        return ""

    value = str(value).lower().strip()
    value = re.sub(r"\bair\b", "", value)
    value = re.sub(r"\bairbrush\b", "", value)
    value = re.sub(r"[^a-z0-9]+", "", value)

    return value


def is_non_color(row):
    text = " ".join([
        str(row.get("Paint_Name", "")),
        str(row.get("Paint_Type", "")),
        str(row.get("Product_Line", "")),
        str(row.get("Notes", "")),
    ]).lower()

    non_color_terms = [
        "medium",
        "thinner",
        "varnish",
        "cleaner",
        "brush-on primer",
        "airbrush cleaner",
        "mixing medium",
    ]

    return any(term in text for term in non_color_terms)


def source_priority(row):
    product_line = str(row.get("Product_Line", "")).lower()
    brand = str(row.get("Brand", "")).lower()

    if "fanatic" in product_line or "fanatic" in brand:
        return 1
    if "warpaints" in product_line or "warpaints" in brand:
        return 2
    if "speedpaint" in product_line or "speedpaint" in brand:
        return 3
    if "air" in product_line or "air" in brand:
        return 4

    return 9


def build_color_lookup(df):
    color_rows = df[df.apply(has_color, axis=1)].copy()
    color_rows["Normalized_Name"] = color_rows["Paint_Name"].apply(normalize_name)
    color_rows["Priority"] = color_rows.apply(source_priority, axis=1)

    lookup = {}

    for name, group in color_rows.groupby("Normalized_Name"):
        if not name:
            continue

        best = group.sort_values("Priority").iloc[0]
        lookup[name] = best

    return lookup


def main():
    sheets = pd.read_excel(INPUT_FILE, sheet_name=None)
    army_df = sheets["ArmyPainter_All"].copy()

    starting_missing = len(
        army_df[army_df["Hex"].apply(is_blank) | army_df["RGB"].apply(is_blank)]
    )

    lookup = build_color_lookup(army_df)

    updated_rows = []
    skipped_rows = []

    for idx, row in army_df.iterrows():
        if has_color(row):
            continue

        paint_name = row.get("Paint_Name", "")
        normalized = normalize_name(paint_name)

        if is_non_color(row):
            skipped_rows.append({
                "Paint_ID": row.get("Paint_ID", ""),
                "Paint_Name": paint_name,
                "Reason": "Skipped non-color product",
                "Product_Line": row.get("Product_Line", ""),
                "Paint_Type": row.get("Paint_Type", ""),
            })
            continue

        if normalized not in lookup:
            continue

        source = lookup[normalized]

        army_df.at[idx, "Hex"] = source.get("Hex", "")
        army_df.at[idx, "RGB"] = source.get("RGB", "")

        note = (
            f"Hex/RGB inherited from Army Painter {source.get('Product_Line', '')} "
            f"{source.get('Paint_Name', '')} using normalized same-name match."
        )

        if "Notes" in army_df.columns:
            existing_note = army_df.at[idx, "Notes"]
            army_df.at[idx, "Notes"] = note if is_blank(existing_note) else str(existing_note) + " | " + note

        updated_rows.append({
            "Target_Paint_ID": row.get("Paint_ID", ""),
            "Target_Paint_Name": paint_name,
            "Target_Product_Line": row.get("Product_Line", ""),
            "Target_Paint_Type": row.get("Paint_Type", ""),
            "Filled_Hex": source.get("Hex", ""),
            "Filled_RGB": source.get("RGB", ""),
            "Source_Paint_ID": source.get("Paint_ID", ""),
            "Source_Paint_Name": source.get("Paint_Name", ""),
            "Source_Product_Line": source.get("Product_Line", ""),
            "Source_Paint_Type": source.get("Paint_Type", ""),
            "Match_Method": "Normalized same-name inheritance",
            "Confidence": "High",
        })

    ending_missing_df = army_df[
        army_df["Hex"].apply(is_blank) | army_df["RGB"].apply(is_blank)
    ].copy()

    summary_df = pd.DataFrame([
        {"Metric": "Starting missing Hex/RGB", "Value": starting_missing},
        {"Metric": "Rows updated this run", "Value": len(updated_rows)},
        {"Metric": "Rows skipped as non-color", "Value": len(skipped_rows)},
        {"Metric": "Ending missing Hex/RGB", "Value": len(ending_missing_df)},
        {"Metric": "Rows with Hex/RGB", "Value": len(army_df) - len(ending_missing_df)},
    ])

    sheets["ArmyPainter_All"] = army_df
    sheets["Inheritance_Enrichment_Log"] = pd.DataFrame(updated_rows)
    sheets["Inheritance_Skipped_NonColor"] = pd.DataFrame(skipped_rows)
    sheets["Still_Missing_Hex_RGB"] = ending_missing_df
    sheets["Inheritance_Update_Summary"] = summary_df

    with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:
        for sheet_name, sheet_df in sheets.items():
            sheet_df.to_excel(writer, sheet_name=sheet_name[:31], index=False)

    print("ARMY PAINTER INHERITANCE ENRICHMENT")
    print("-----------------------------------")
    print(f"Starting missing Hex/RGB: {starting_missing}")
    print(f"Rows updated this run: {len(updated_rows)}")
    print(f"Rows skipped as non-color: {len(skipped_rows)}")
    print(f"Ending missing Hex/RGB: {len(ending_missing_df)}")
    print(f"Rows with Hex/RGB: {len(army_df) - len(ending_missing_df)}")
    print(f"Output saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()