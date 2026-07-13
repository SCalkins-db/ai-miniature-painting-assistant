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

TARGET_FILE = REGISTRY_DIR / "Army_Painter_registry_26.0.12_hex_enriched.xlsx"
OUTPUT_FILE = REGISTRY_DIR / "Army_Painter_registry_26.0.13_all_sources_enriched.xlsx"


USEFUL_SHEETS = [
    "ArmyPainter_All",
    "Speedpaint_Equivalents",
    "GW_Match_Audit",
    "Swatches_Master",
    "Vallejo_All",
    "Direct_Vallejo_Ref_Fills",
    "Equivalent_Color_Fill_Audit",
    "AK_All",
    "AK_Color_Pull_Audit",
    "ProAcryl_All",
    "GW_Color_Pull_Audit",
]


def is_blank(value):
    return pd.isna(value) or str(value).strip() == ""


def clean(value):
    if pd.isna(value):
        return ""
    return str(value).strip().lower()


def has_hex_rgb(row):
    return not is_blank(row.get("Hex", "")) and not is_blank(row.get("RGB", ""))


def find_column(df, possible_names):
    for name in possible_names:
        if name in df.columns:
            return name
    return None


def load_all_sheets():
    all_sources = []

    for workbook in REGISTRY_DIR.glob("*.xlsx"):
        sheets = pd.read_excel(workbook, sheet_name=None)

        for sheet_name, df in sheets.items():
            if sheet_name not in USEFUL_SHEETS:
                continue

            all_sources.append({
                "workbook": workbook.name,
                "sheet": sheet_name,
                "df": df
            })

    return all_sources


def build_lookup_sources(all_sources):
    lookup_rows = []

    for source in all_sources:
        df = source["df"]

        name_col = find_column(df, [
            "Paint_Name",
            "Match_Paint_Name",
            "Match_Name",
            "GW_Match_Name",
            "Source_Paint",
            "Source_Paint_Name",
            "Equivalent_Paint_Name",
            "Resolved_Paint_Name",
        ])

        hex_col = find_column(df, [
            "Hex",
            "Match_Hex",
            "GW_Match_Hex",
            "Resolved_Hex",
        ])

        rgb_col = find_column(df, [
            "RGB",
            "Match_RGB",
            "GW_Match_RGB",
            "Resolved_RGB",
        ])

        paint_id_col = find_column(df, [
            "Paint_ID",
            "Match_Paint_ID",
            "GW_Match_Paint_ID",
            "Resolved_Paint_ID",
        ])

        company_col = find_column(df, [
            "Company",
            "Match_Company",
            "Resolved_Company",
        ])

        product_line_col = find_column(df, [
            "Product_Line",
            "Match_Product_Line",
            "GW_Match_Product_Line",
            "Resolved_Product_Line",
        ])

        if name_col is None or hex_col is None or rgb_col is None:
            continue

        for _, row in df.iterrows():
            paint_name = row.get(name_col, "")
            hex_value = row.get(hex_col, "")
            rgb_value = row.get(rgb_col, "")

            if is_blank(paint_name) or is_blank(hex_value) or is_blank(rgb_value):
                continue

            lookup_rows.append({
                "Lookup_Name": clean(paint_name),
                "Source_Paint_Name": paint_name,
                "Source_Paint_ID": row.get(paint_id_col, "") if paint_id_col else "",
                "Source_Company": row.get(company_col, "") if company_col else "",
                "Source_Product_Line": row.get(product_line_col, "") if product_line_col else "",
                "Hex": hex_value,
                "RGB": rgb_value,
                "Workbook": source["workbook"],
                "Sheet": source["sheet"],
            })

    return pd.DataFrame(lookup_rows)


def get_match_names(row):
    names = []

    for col in [
        "Paint_Name",
        "GW_Match_Name",
        "AK_Match_Name",
        "Vallejo_Model_Match_Name",
        "Vallejo_Game_Match_Name",
        "Pro_Acryl_Match_Name",
        "Match_Paint_Name",
        "Equivalent_Paint_Name",
    ]:
        if col in row.index and not is_blank(row.get(col, "")):
            names.append(row.get(col, ""))

    return names


def enrich_army_painter():
    army_df = pd.read_excel(TARGET_FILE, sheet_name="ArmyPainter_All")
    all_sheets = pd.read_excel(TARGET_FILE, sheet_name=None)

    sources = load_all_sheets()
    lookup_df = build_lookup_sources(sources)

    updated_rows = []
    updated_count = 0

    for idx, row in army_df.iterrows():
        if has_hex_rgb(row):
            continue

        candidate_names = get_match_names(row)
        found_match = None

        for name in candidate_names:
            matches = lookup_df[lookup_df["Lookup_Name"] == clean(name)]

            if not matches.empty:
                found_match = matches.iloc[0]
                break

        if found_match is None:
            continue

        army_df.at[idx, "Hex"] = found_match["Hex"]
        army_df.at[idx, "RGB"] = found_match["RGB"]

        note = (
            f"Hex/RGB inferred from {found_match['Source_Paint_Name']} "
            f"via {found_match['Sheet']} in {found_match['Workbook']}."
        )

        if "Notes" in army_df.columns:
            existing_note = army_df.at[idx, "Notes"]

            if is_blank(existing_note):
                army_df.at[idx, "Notes"] = note
            else:
                army_df.at[idx, "Notes"] = str(existing_note) + " | " + note

        updated_rows.append({
            "Paint_ID": row.get("Paint_ID", ""),
            "Paint_Name": row.get("Paint_Name", ""),
            "Filled_Hex": found_match["Hex"],
            "Filled_RGB": found_match["RGB"],
            "Source_Paint_Name": found_match["Source_Paint_Name"],
            "Source_Company": found_match["Source_Company"],
            "Source_Product_Line": found_match["Source_Product_Line"],
            "Source_Workbook": found_match["Workbook"],
            "Source_Sheet": found_match["Sheet"],
        })

        updated_count += 1

    still_missing = army_df[
        army_df["Hex"].apply(is_blank) | army_df["RGB"].apply(is_blank)
    ]

    summary_df = pd.DataFrame([
        {"Metric": "Total Army Painter rows", "Value": len(army_df)},
        {"Metric": "Lookup source rows", "Value": len(lookup_df)},
        {"Metric": "Rows updated this run", "Value": updated_count},
        {"Metric": "Rows still missing Hex/RGB", "Value": len(still_missing)},
        {"Metric": "Rows with Hex/RGB", "Value": len(army_df) - len(still_missing)},
    ])

    all_sheets["ArmyPainter_All"] = army_df
    all_sheets["All_Source_Enrichment_Log"] = pd.DataFrame(updated_rows)
    all_sheets["All_Source_Update_Summary"] = summary_df
    all_sheets["Still_Missing_Hex_RGB"] = still_missing

    with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:
        for sheet_name, df in all_sheets.items():
            safe_name = sheet_name[:31]
            df.to_excel(writer, sheet_name=safe_name, index=False)

    print("ALL SOURCE ARMY PAINTER ENRICHMENT")
    print("----------------------------------")
    print(f"Lookup source rows: {len(lookup_df)}")
    print(f"Rows updated this run: {updated_count}")
    print(f"Rows still missing Hex/RGB: {len(still_missing)}")
    print(f"Rows with Hex/RGB: {len(army_df) - len(still_missing)}")
    print(f"Output saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    enrich_army_painter()
