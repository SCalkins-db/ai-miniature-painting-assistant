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

from glob import glob

REGISTRY_FILES = {}

for file in DATA_DIR.glob("*.xlsx"):
    name = file.name.lower()

    if "army" in name:
        REGISTRY_FILES["Army Painter"] = file

    elif "gw" in name or "citadel" in name:
        REGISTRY_FILES["Games Workshop"] = file

    elif "vallejo" in name:
        REGISTRY_FILES["Vallejo"] = file

    elif "ak" in name:
        REGISTRY_FILES["AK Interactive"] = file

    elif "pro" in name:
        REGISTRY_FILES["Pro Acryl"] = file

    print("\nDetected registries:")

    for company, file in REGISTRY_FILES.items():
        print(f"{company}: {file.name}")

    print()

def clean_text(value):
    if pd.isna(value):
        return ""
    return str(value).strip().lower()


def load_registry(path):
    return pd.read_excel(path, sheet_name=0)


def has_hex(row):
    hex_value = row.get("Hex", "")
    rgb_value = row.get("RGB", "")

    return (
        not pd.isna(hex_value)
        and str(hex_value).strip() != ""
        and not pd.isna(rgb_value)
        and str(rgb_value).strip() != ""
    )

def is_blank(value):
    if pd.isna(value):
        return True

    return str(value).strip() == ""

def find_exact_name_matches(source_row, comparison_dfs):
    source_name = clean_text(source_row["Paint_Name"])
    matches = []

    for company, df in comparison_dfs.items():
        if "Paint_Name" not in df.columns:
            continue

        matched_rows = df[
            df["Paint_Name"].apply(clean_text) == source_name
        ]

        matched_rows = matched_rows[
            matched_rows.apply(has_hex, axis=1)
        ]

        for _, match in matched_rows.iterrows():
            matches.append({
                "Match_Source": "Exact Paint_Name",
                "Match_Company": company,
                "Match_Paint_ID": match.get("Paint_ID", ""),
                "Match_Paint_Name": match.get("Paint_Name", ""),
                "Match_Product_Line": match.get("Product_Line", ""),
                "Match_Paint_Type": match.get("Paint_Type", ""),
                "Match_Hex": match.get("Hex", ""),
                "Match_RGB": match.get("RGB", ""),
                "Confidence": "High"
            })

    return matches


def find_gw_match(source_row, comparison_dfs):
    matches = []

    gw_match_name = source_row.get("GW_Match_Name", "")

    if pd.isna(gw_match_name) or str(gw_match_name).strip() == "":
        return matches

    gw_df = comparison_dfs.get("Games Workshop")

    if gw_df is None:
        return matches

    matched_rows = gw_df[
        gw_df["Paint_Name"].apply(clean_text) == clean_text(gw_match_name)
    ]

    matched_rows = matched_rows[
        matched_rows.apply(has_hex, axis=1)
    ]

    for _, match in matched_rows.iterrows():
        matches.append({
            "Match_Source": "GW_Match_Name",
            "Match_Company": "Games Workshop",
            "Match_Paint_ID": match.get("Paint_ID", ""),
            "Match_Paint_Name": match.get("Paint_Name", ""),
            "Match_Product_Line": match.get("Product_Line", ""),
            "Match_Paint_Type": match.get("Paint_Type", ""),
            "Match_Hex": match.get("Hex", ""),
            "Match_RGB": match.get("RGB", ""),
            "Confidence": "High"
        })

    return matches

def find_extra_sheet_matches(source_row, army_workbook_sheets, comparison_dfs):
    matches = []

    source_name = clean_text(source_row.get("Paint_Name", ""))

    possible_sheet_names = [
        "Speedpaint_Equivalents",
        "GW_Match_Audit",
        "Crossref_Audit"
    ]

    for sheet_name in possible_sheet_names:
        if sheet_name not in army_workbook_sheets:
            continue

        sheet_df = army_workbook_sheets[sheet_name]

        source_columns = [
            "Source_Paint",
            "Source_Paint_Name",
            "Paint_Name",
            "Army_Painter_Paint_Name"
        ]

        match_columns = [
            "Match_Paint",
            "Match_Paint_Name",
            "Equivalent_Paint_Name",
            "GW_Match_Name",
            "Match_Name"
        ]

        company_columns = [
            "Match_Company",
            "Equivalent_Company",
            "Company"
        ]

        source_col = next((col for col in source_columns if col in sheet_df.columns), None)
        match_col = next((col for col in match_columns if col in sheet_df.columns), None)
        company_col = next((col for col in company_columns if col in sheet_df.columns), None)

        if source_col is None or match_col is None:
            continue

        source_matches = sheet_df[
            sheet_df[source_col].apply(clean_text) == source_name
        ]

        for _, sheet_row in source_matches.iterrows():
            match_name = sheet_row.get(match_col, "")
            match_company = sheet_row.get(company_col, "")

            if is_blank(match_name):
                continue

            # If company is blank, search all comparison registries
            companies_to_search = []

            if not is_blank(match_company):
                for company in comparison_dfs.keys():
                    if clean_text(match_company) in clean_text(company) or clean_text(company) in clean_text(match_company):
                        companies_to_search.append(company)

            if not companies_to_search:
                companies_to_search = list(comparison_dfs.keys())

            for company in companies_to_search:
                df = comparison_dfs[company]

                if "Paint_Name" not in df.columns:
                    continue

                matched_rows = df[
                    df["Paint_Name"].apply(clean_text) == clean_text(match_name)
                ]

                matched_rows = matched_rows[
                    matched_rows.apply(has_hex, axis=1)
                ]

                for _, match in matched_rows.iterrows():
                    matches.append({
                        "Match_Source": f"{sheet_name}",
                        "Match_Company": company,
                        "Match_Paint_ID": match.get("Paint_ID", ""),
                        "Match_Paint_Name": match.get("Paint_Name", ""),
                        "Match_Product_Line": match.get("Product_Line", ""),
                        "Match_Paint_Type": match.get("Paint_Type", ""),
                        "Match_Hex": match.get("Hex", ""),
                        "Match_RGB": match.get("RGB", ""),
                        "Confidence": "High"
                    })

    return matches

def main():
    army_df = load_registry(REGISTRY_FILES["Army Painter"])

    army_workbook_sheets = pd.read_excel(
        REGISTRY_FILES["Army Painter"],
        sheet_name=None
    )

    comparison_dfs = {
        company: load_registry(path)
        for company, path in REGISTRY_FILES.items()
        if company != "Army Painter"
    }

    missing_df = army_df[
        ~army_df.apply(has_hex, axis=1)
    ]

    report_rows = []

    for _, row in missing_df.iterrows():
        paint_id = row.get("Paint_ID", "")
        paint_name = row.get("Paint_Name", "")
        product_line = row.get("Product_Line", "")
        paint_type = row.get("Paint_Type", "")

        matches = []
        matches.extend(find_exact_name_matches(row, comparison_dfs))
        matches.extend(find_gw_match(row, comparison_dfs))
        matches.extend(find_extra_sheet_matches(row, army_workbook_sheets, comparison_dfs))

        if not matches:
            report_rows.append({
                "Paint_ID": paint_id,
                "Paint_Name": paint_name,
                "Product_Line": product_line,
                "Paint_Type": paint_type,
                "Match_Source": "No Match Found",
                "Match_Company": "",
                "Match_Paint_ID": "",
                "Match_Paint_Name": "",
                "Match_Product_Line": "",
                "Match_Paint_Type": "",
                "Match_Hex": "",
                "Match_RGB": "",
                "Confidence": "Review"
            })
        else:
            for match in matches:
                report_rows.append({
                    "Paint_ID": paint_id,
                    "Paint_Name": paint_name,
                    "Product_Line": product_line,
                    "Paint_Type": paint_type,
                    **match
                })

    report_df = pd.DataFrame(report_rows)

    output_path = DATA_DIR / "army_painter_missing_hex_crossref_audit.csv"
    report_df.to_csv(output_path, index=False)

    print("ARMY PAINTER MISSING HEX CROSSREF AUDIT")
    print("--------------------------------------")
    print(f"Total Army Painter rows: {len(army_df)}")
    print(f"Missing Hex/RGB rows: {len(missing_df)}")
    print(f"Possible matches found: {len(report_df[report_df['Match_Source'] != 'No Match Found'])}")
    print(f"No match found: {len(report_df[report_df['Match_Source'] == 'No Match Found'])}")
    print()
    print(f"Audit saved to: {output_path}")


if __name__ == "__main__":
    main()
