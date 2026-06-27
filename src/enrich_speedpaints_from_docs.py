from pathlib import Path
import re
import pandas as pd
from docx import Document


PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
REGISTRY_DIR = DATA_DIR / "registries_xlsx"
DOC_DIR = DATA_DIR / "comparison_docs"

ARMY_FILE = REGISTRY_DIR / "Army_Painter_registry_26.0.13_all_sources_enriched.xlsx"
VALLEJO_FILE = REGISTRY_DIR / "Vallejo_registry_26.0.9.xlsx"
OUTPUT_FILE = REGISTRY_DIR / "Army_Painter_registry_26.0.14_speedpaint_doc_enriched.xlsx"


def is_blank(value):
    return pd.isna(value) or str(value).strip() == ""


def clean(value):
    if pd.isna(value):
        return ""
    return str(value).strip().lower()


def extract_doc_text(path):
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def build_vallejo_lookup():
    sheets = pd.read_excel(VALLEJO_FILE, sheet_name=None)
    lookup = {}

    for sheet_name, df in sheets.items():
        if "Paint_Name" not in df.columns or "Hex" not in df.columns or "RGB" not in df.columns:
            continue

        for _, row in df.iterrows():
            name = row.get("Paint_Name", "")
            hex_value = row.get("Hex", "")
            rgb_value = row.get("RGB", "")

            if is_blank(name) or is_blank(hex_value) or is_blank(rgb_value):
                continue

            lookup[clean(name)] = {
                "Paint_ID": row.get("Paint_ID", ""),
                "Paint_Name": name,
                "Product_Line": row.get("Product_Line", ""),
                "Paint_Type": row.get("Paint_Type", ""),
                "Hex": hex_value,
                "RGB": rgb_value,
                "Sheet": sheet_name,
            }

    return lookup


def parse_speedpaint_docs():
    records = []

    paint_header_pattern = re.compile(r"^[A-Z][A-Za-z0-9 '\-–]+$")
    vallejo_pattern = re.compile(r"Vallejo: ([^\n]+)\n([^\n]+)\n(?:.*?\n){0,4}?([0-9]{2,3}(?:\.[0-9])?)% similar", re.MULTILINE)

    for path in DOC_DIR.glob("*.docx"):
        text = extract_doc_text(path)
        lines = [line.strip() for line in text.splitlines() if line.strip()]

        current_paint = None

        for i, line in enumerate(lines):
            if i + 1 < len(lines) and lines[i + 1].lower() == "acrylicspeed":
                current_paint = line

            if current_paint and line.startswith("Vallejo:"):
                product_line = line.replace("Vallejo:", "").strip()

                if i + 1 < len(lines):
                    match_name = lines[i + 1].strip()

                    similarity = None
                    for j in range(i + 1, min(i + 8, len(lines))):
                        sim_match = re.search(r"([0-9]{2,3}(?:\.[0-9])?)% similar", lines[j])
                        if sim_match:
                            similarity = float(sim_match.group(1))
                            break

                    if similarity is not None:
                        records.append({
                            "Source_Paint": current_paint,
                            "Match_Company": "Vallejo",
                            "Match_Product_Line": product_line,
                            "Match_Paint_Name_Raw": match_name,
                            "Match_Paint_Name_Clean": re.sub(r"\s*\([^)]*\)", "", match_name).strip(),
                            "Similarity": similarity,
                            "Source_Document": path.name,
                        })

    return pd.DataFrame(records)


def main():
    army_sheets = pd.read_excel(ARMY_FILE, sheet_name=None)
    army_df = army_sheets["ArmyPainter_All"]

    vallejo_lookup = build_vallejo_lookup()
    speedpaint_matches = parse_speedpaint_docs()

    updated_rows = []
    updated_count = 0

    missing_mask = army_df["Hex"].apply(is_blank) | army_df["RGB"].apply(is_blank)

    for idx, row in army_df[missing_mask].iterrows():
        paint_name = row.get("Paint_Name", "")
        paint_type = row.get("Paint_Type", "")
        product_line = row.get("Product_Line", "")

        if "speed" not in clean(paint_type) and "speed" not in clean(product_line):
            continue

        matches = speedpaint_matches[
            speedpaint_matches["Source_Paint"].apply(clean) == clean(paint_name)
        ].copy()

        if matches.empty:
            continue

        matches = matches.sort_values("Similarity", ascending=False)

        chosen = None
        chosen_vallejo = None

        for _, match in matches.iterrows():
            raw_name = match["Match_Paint_Name_Raw"]
            clean_name = match["Match_Paint_Name_Clean"]

            candidates = [
                clean(raw_name),
                clean(clean_name),
            ]

            for candidate in candidates:
                if candidate in vallejo_lookup:
                    chosen = match
                    chosen_vallejo = vallejo_lookup[candidate]
                    break

            if chosen_vallejo:
                break

        if not chosen_vallejo:
            continue

        army_df.at[idx, "Hex"] = chosen_vallejo["Hex"]
        army_df.at[idx, "RGB"] = chosen_vallejo["RGB"]

        note = (
            f"Hex/RGB inferred from Vallejo {chosen_vallejo['Paint_Name']} "
            f"({chosen['Similarity']}% similarity) using Speedpaint comparison document "
            f"{chosen['Source_Document']}."
        )

        if "Notes" in army_df.columns:
            existing = army_df.at[idx, "Notes"]
            army_df.at[idx, "Notes"] = note if is_blank(existing) else str(existing) + " | " + note

        updated_rows.append({
            "Paint_ID": row.get("Paint_ID", ""),
            "Paint_Name": paint_name,
            "Filled_Hex": chosen_vallejo["Hex"],
            "Filled_RGB": chosen_vallejo["RGB"],
            "Vallejo_Source_Paint": chosen_vallejo["Paint_Name"],
            "Vallejo_Product_Line": chosen_vallejo["Product_Line"],
            "Similarity": chosen["Similarity"],
            "Source_Document": chosen["Source_Document"],
        })

        updated_count += 1

    still_missing = army_df[
        army_df["Hex"].apply(is_blank) | army_df["RGB"].apply(is_blank)
    ]

    summary_df = pd.DataFrame([
        {"Metric": "Total Army Painter rows", "Value": len(army_df)},
        {"Metric": "Speedpaint doc matches parsed", "Value": len(speedpaint_matches)},
        {"Metric": "Rows updated this run", "Value": updated_count},
        {"Metric": "Rows with Hex/RGB", "Value": len(army_df) - len(still_missing)},
        {"Metric": "Rows still missing Hex/RGB", "Value": len(still_missing)},
    ])

    army_sheets["ArmyPainter_All"] = army_df
    army_sheets["Speedpaint_Doc_Enrichment_Log"] = pd.DataFrame(updated_rows)
    army_sheets["Speedpaint_Doc_Update_Summary"] = summary_df
    army_sheets["Still_Missing_Hex_RGB"] = still_missing

    with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:
        for sheet_name, df in army_sheets.items():
            df.to_excel(writer, sheet_name=sheet_name[:31], index=False)

    print("SPEEDPAINT DOC ENRICHMENT")
    print("-------------------------")
    print(f"Speedpaint doc matches parsed: {len(speedpaint_matches)}")
    print(f"Rows updated this run: {updated_count}")
    print(f"Rows with Hex/RGB: {len(army_df) - len(still_missing)}")
    print(f"Rows still missing Hex/RGB: {len(still_missing)}")
    print(f"Output saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()