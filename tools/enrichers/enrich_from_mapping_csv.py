# Allow direct execution from project root
import sys
from pathlib import Path

_project_root = Path(__file__).resolve()
while _project_root.parent != _project_root:
    if (_project_root / "src").exists() and (_project_root / "data").exists():
        break
    _project_root = _project_root.parent

if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import json
import re
import pandas as pd

from src.core.registry_versions import get_active_registry, make_output_paths, set_active_registry

from src.core.paths import PROJECT_ROOT, SRC_DIR, DATA_DIR, REGISTRIES_CSV_DIR, REGISTRIES_XLSX_DIR, MAPPINGS_DIR, REPORTS_DIR, SOURCE_DOCUMENTS_DIR, AUDIT_DIR, CSV_DIR, XLSX_DIR, SOURCE_DOCS_DIR

REGISTRY_FILE = get_active_registry("Army Painter", "csv")
MAPPING_FILE = MAPPINGS_DIR / "army_painter_air_to_fanatic.csv"

OUTPUT_FILE, OUTPUT_XLSX = make_output_paths("Army Painter")
REPORT_CSV = REPORTS_DIR / "army_painter_air_mapping_enrichment_report.csv"
REPORT_JSON = REPORTS_DIR / "army_painter_air_mapping_enrichment_report.json"


def is_blank(value) -> bool:
    if pd.isna(value):
        return True

    value = str(value).strip()
    return value == "" or value.lower() in {"nan", "none", "null"}


def has_color(row) -> bool:
    return not is_blank(row.get("Hex")) and not is_blank(row.get("RGB"))


def norm(value) -> str:
    if pd.isna(value):
        return ""

    value = str(value).strip().lower()
    value = value.replace("&", "and")
    value = value.replace("’", "'")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()

    return value


def is_air_row(row) -> bool:
    text = " ".join(
        str(row.get(col, ""))
        for col in ["Brand", "Product_Line", "Paint_Type", "Paint_ID", "Notes"]
    ).lower()

    return "air" in text


def is_non_air_army_painter_row(row) -> bool:
    if str(row.get("Company", "")).strip().lower() != "army painter":
        return False

    return not is_air_row(row)


def append_note(existing, note):
    if is_blank(existing):
        return note

    existing = str(existing).strip()

    if note in existing:
        return existing

    return f"{existing}; {note}"


def find_air_rows(df, air_name):
    target = norm(air_name)

    mask = (
        df["Paint_Name"].apply(norm).eq(target)
        &
        df.apply(lambda row: is_air_row(row), axis=1)
    )

    return df[mask]


def find_main_rows(df, main_name):
    target = norm(main_name)

    mask = (
        df["Paint_Name"].apply(norm).eq(target)
        &
        df.apply(lambda row: is_non_air_army_painter_row(row), axis=1)
        &
        df.apply(lambda row: has_color(row), axis=1)
    )

    return df[mask]


def choose_main_match(main_rows):
    if main_rows.empty:
        return None, "MAIN_NOT_FOUND_OR_MISSING_COLOR"

    color_pairs = set()

    for _, row in main_rows.iterrows():
        color_pairs.add((
            str(row.get("Hex")).strip(),
            str(row.get("RGB")).strip(),
        ))

    if len(color_pairs) > 1:
        return None, "MAIN_HAS_CONFLICTING_COLORS"

    return main_rows.iloc[0], "MAIN_MATCH_FOUND"


def main():
    if not REGISTRY_FILE.exists():
        raise FileNotFoundError(f"Missing registry file: {REGISTRY_FILE}")

    if not MAPPING_FILE.exists():
        raise FileNotFoundError(f"Missing mapping file: {MAPPING_FILE}")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_CSV.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(REGISTRY_FILE)
    mappings = pd.read_csv(MAPPING_FILE)

    required_mapping_cols = ["Air_Paint", "Main_Paint"]
    for col in required_mapping_cols:
        if col not in mappings.columns:
            raise ValueError(
                f"Mapping file is missing required column '{col}'. "
                f"Found columns: {list(mappings.columns)}"
            )

    for col in ["Company", "Brand", "Product_Line", "Paint_Name", "Paint_Type", "Hex", "RGB", "Notes", "Paint_ID"]:
        if col not in df.columns:
            df[col] = ""

    report_rows = []

    filled_count = 0
    already_complete_count = 0
    air_not_found_count = 0
    main_not_found_count = 0
    conflict_count = 0

    for _, mapping in mappings.iterrows():
        air_name = mapping.get("Air_Paint")
        main_name = mapping.get("Main_Paint")

        if is_blank(air_name) or is_blank(main_name):
            continue

        air_rows = find_air_rows(df, air_name)
        main_rows = find_main_rows(df, main_name)
        main_match, main_status = choose_main_match(main_rows)

        if air_rows.empty:
            air_not_found_count += 1
            report_rows.append({
                "Air_Paint": air_name,
                "Main_Paint": main_name,
                "Status": "AIR_NOT_FOUND",
                "Matched_Main_Paint_ID": "",
                "Matched_Main_Product_Line": "",
                "Inherited_Hex": "",
                "Inherited_RGB": "",
            })
            continue

        if main_match is None:
            if main_status == "MAIN_HAS_CONFLICTING_COLORS":
                conflict_count += len(air_rows)
            else:
                main_not_found_count += len(air_rows)

            for _, air_row in air_rows.iterrows():
                report_rows.append({
                    "Air_Paint": air_name,
                    "Main_Paint": main_name,
                    "Status": main_status,
                    "Air_Paint_ID": air_row.get("Paint_ID", ""),
                    "Matched_Main_Paint_ID": "",
                    "Matched_Main_Product_Line": "",
                    "Inherited_Hex": "",
                    "Inherited_RGB": "",
                })
            continue

        inherited_hex = str(main_match.get("Hex")).strip()
        inherited_rgb = str(main_match.get("RGB")).strip()

        for index, air_row in air_rows.iterrows():
            if has_color(air_row):
                already_complete_count += 1
                report_rows.append({
                    "Air_Paint": air_name,
                    "Main_Paint": main_name,
                    "Status": "AIR_ALREADY_HAS_COLOR",
                    "Air_Paint_ID": air_row.get("Paint_ID", ""),
                    "Matched_Main_Paint_ID": main_match.get("Paint_ID", ""),
                    "Matched_Main_Product_Line": main_match.get("Product_Line", ""),
                    "Inherited_Hex": air_row.get("Hex", ""),
                    "Inherited_RGB": air_row.get("RGB", ""),
                })
                continue

            df.at[index, "Hex"] = inherited_hex
            df.at[index, "RGB"] = inherited_rgb
            df.at[index, "Notes"] = append_note(
                df.at[index, "Notes"],
                f"Hex/RGB inherited from Army Painter mapping: Air '{air_name}' -> Main '{main_name}' ({main_match.get('Paint_ID', '')})",
            )

            filled_count += 1

            report_rows.append({
                "Air_Paint": air_name,
                "Main_Paint": main_name,
                "Status": "FILLED",
                "Air_Paint_ID": air_row.get("Paint_ID", ""),
                "Matched_Main_Paint_ID": main_match.get("Paint_ID", ""),
                "Matched_Main_Product_Line": main_match.get("Product_Line", ""),
                "Inherited_Hex": inherited_hex,
                "Inherited_RGB": inherited_rgb,
            })

    df.to_csv(OUTPUT_FILE, index=False)

    with pd.ExcelWriter(OUTPUT_XLSX, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Registry")

        report_df = pd.DataFrame(report_rows)
        report_df.to_excel(
            writer,
            index=False,
            sheet_name="Mapping_Report"
        )

    report_df = pd.DataFrame(report_rows)
    report_df.to_csv(REPORT_CSV, index=False)

    set_active_registry("Army Painter", OUTPUT_FILE, OUTPUT_XLSX, archive_previous=True)

    summary = {
        "registry_file": str(REGISTRY_FILE),
        "mapping_file": str(MAPPING_FILE),
        "output_file": str(OUTPUT_FILE),
        "output_xlsx": str(OUTPUT_XLSX),
        "report_csv": str(REPORT_CSV),
        "filled_count": filled_count,
        "already_complete_count": already_complete_count,
        "air_not_found_count": air_not_found_count,
        "main_not_found_or_missing_color_count": main_not_found_count,
        "conflict_count": conflict_count,
        "mapping_rows_checked": len(mappings),
        "report_rows": len(report_rows),
    }

    with open(REPORT_JSON, "w", encoding="utf-8") as file:
        json.dump(summary, file, indent=4)

    print("AIR MAPPING ENRICHMENT")
    print("----------------------")
    print(f"Mapping rows checked: {len(mappings)}")
    print(f"Rows filled: {filled_count}")
    print(f"Already complete: {already_complete_count}")
    print(f"Air not found: {air_not_found_count}")
    print(f"Main missing/no color: {main_not_found_count}")
    print(f"Conflicts: {conflict_count}")
    print()
    print(f"Output: {OUTPUT_FILE}")
    print(f"Output CSV : {OUTPUT_FILE}")
    print(f"Output XLSX: {OUTPUT_XLSX}")
    print(f"Report CSV : {REPORT_CSV}")
    print(f"Report JSON: {REPORT_JSON}")


if __name__ == "__main__":
    main()
