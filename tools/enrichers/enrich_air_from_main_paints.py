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

from src.core.paths import PROJECT_ROOT, SRC_DIR, DATA_DIR, REGISTRIES_CSV_DIR, REGISTRIES_XLSX_DIR, MAPPINGS_DIR, REPORTS_DIR, SOURCE_DOCUMENTS_DIR, AUDIT_DIR, CSV_DIR, XLSX_DIR, SOURCE_DOCS_DIR

ARCHIVE_DIR = REGISTRIES_CSV_DIR / "archive"

INPUT_CSV = REGISTRIES_CSV_DIR / "archive" / "Army_Painter_registry_26.0.11_aligned.csv"

OUTPUT_CSV = REGISTRIES_CSV_DIR / "Army_Painter_registry_26.0.16_air_inheritance_enriched.csv"
OUTPUT_XLSX = REGISTRIES_XLSX_DIR / "Army_Painter_registry_26.0.16_air_inheritance_enriched.xlsx"

REPORT_CSV = REPORTS_DIR / "army_painter_air_inheritance_report.csv"
REPORT_JSON = REPORTS_DIR / "army_painter_air_inheritance_report.json"
REPORT_MD = REPORTS_DIR / "army_painter_air_inheritance_report.md"


def is_blank(value) -> bool:
    if pd.isna(value):
        return True
    value = str(value).strip()
    return value == "" or value.lower() in {"nan", "none", "null"}


def has_color(row) -> bool:
    return not is_blank(row.get("Hex")) and not is_blank(row.get("RGB"))


def normalize_name(value: str) -> str:
    if is_blank(value):
        return ""

    value = str(value).lower().strip()
    value = value.replace("&", "and")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()

    return value


def is_air_row(row) -> bool:
    fields = [
        row.get("Product_Line", ""),
        row.get("Brand", ""),
        row.get("Paint_Type", ""),
        row.get("Notes", ""),
        row.get("Source", ""),
    ]

    combined = " ".join(str(x).lower() for x in fields)

    return "air" in combined


def is_main_army_painter_color(row) -> bool:
    if str(row.get("Company", "")).strip().lower() != "army painter":
        return False

    if is_air_row(row):
        return False

    if not has_color(row):
        return False

    name = str(row.get("Paint_Name", "")).lower()

    non_color_terms = [
        "medium",
        "varnish",
        "primer",
        "cleaner",
        "retarder",
        "stabilizer",
    ]

    return not any(term in name for term in non_color_terms)


def append_note(existing, new_note):
    if is_blank(existing):
        return new_note

    existing = str(existing).strip()

    if new_note in existing:
        return existing

    return f"{existing}; {new_note}"


def build_main_paint_lookup(df):
    lookup = {}

    for _, row in df.iterrows():
        if not is_main_army_painter_color(row):
            continue

        key = normalize_name(row.get("Paint_Name"))

        if not key:
            continue

        lookup.setdefault(key, []).append(row.to_dict())

    return lookup


def choose_best_match(matches):
    """
    Only auto-fill when all matching candidates agree on Hex/RGB.
    If the same paint name exists multiple times with different colors,
    force review instead of guessing.
    """

    usable = [
        match for match in matches
        if not is_blank(match.get("Hex")) and not is_blank(match.get("RGB"))
    ]

    if not usable:
        return None, "MATCH_EXISTS_BUT_NO_COLOR"

    color_pairs = {
        (
            str(match.get("Hex")).strip(),
            str(match.get("RGB")).strip(),
        )
        for match in usable
    }

    if len(color_pairs) > 1:
        return None, "MULTIPLE_COLOR_VALUES_REVIEW"

    return usable[0], "SAFE_MATCH"


def main():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    REGISTRIES_XLSX_DIR.mkdir(parents=True, exist_ok=True)

    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"Missing input CSV: {INPUT_CSV}")

    df = pd.read_csv(INPUT_CSV)

    for col in ["Hex", "RGB", "Notes", "Product_Line", "Brand", "Paint_Type", "Paint_Name", "Company"]:
        if col not in df.columns:
            df[col] = ""

    main_lookup = build_main_paint_lookup(df)

    report_rows = []
    fills = 0
    needs_review = 0
    skipped_not_air = 0
    skipped_already_complete = 0

    for index, row in df.iterrows():
        row_dict = row.to_dict()

        if not is_air_row(row_dict):
            skipped_not_air += 1
            continue

        if has_color(row_dict):
            skipped_already_complete += 1
            continue

        air_name = row_dict.get("Paint_Name", "")
        key = normalize_name(air_name)

        matches = main_lookup.get(key, [])

        report = {
            "Row_Index": index,
            "Paint_ID": row_dict.get("Paint_ID", ""),
            "Air_Paint_Name": air_name,
            "Air_Product_Line": row_dict.get("Product_Line", ""),
            "Air_Paint_Type": row_dict.get("Paint_Type", ""),
            "Original_Hex": row_dict.get("Hex", ""),
            "Original_RGB": row_dict.get("RGB", ""),
            "Match_Status": "",
            "Matched_Paint_ID": "",
            "Matched_Product_Line": "",
            "Matched_Paint_Name": "",
            "Inherited_Hex": "",
            "Inherited_RGB": "",
            "Action": "",
        }

        if not matches:
            report["Match_Status"] = "NO_MAIN_PAINT_NAME_MATCH"
            report["Action"] = "Needs review"
            needs_review += 1
            report_rows.append(report)
            continue

        best_match, status = choose_best_match(matches)

        report["Match_Status"] = status

        if best_match is None:
            report["Action"] = "Needs review"
            needs_review += 1
            report_rows.append(report)
            continue

        inherited_hex = str(best_match.get("Hex")).strip()
        inherited_rgb = str(best_match.get("RGB")).strip()

        df.at[index, "Hex"] = inherited_hex
        df.at[index, "RGB"] = inherited_rgb

        df.at[index, "Notes"] = append_note(
            df.at[index, "Notes"],
            f"Hex/RGB inherited from matching Army Painter main paint: {best_match.get('Paint_Name')} ({best_match.get('Paint_ID')})",
        )

        report.update({
            "Matched_Paint_ID": best_match.get("Paint_ID", ""),
            "Matched_Product_Line": best_match.get("Product_Line", ""),
            "Matched_Paint_Name": best_match.get("Paint_Name", ""),
            "Inherited_Hex": inherited_hex,
            "Inherited_RGB": inherited_rgb,
            "Action": "Filled",
        })

        fills += 1
        report_rows.append(report)

    df.to_csv(OUTPUT_CSV, index=False)

    with pd.ExcelWriter(OUTPUT_XLSX, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Registry")

        report_df = pd.DataFrame(report_rows)
        report_df.to_excel(writer, index=False, sheet_name="Air_Inheritance_Report")

        still_missing = df[
            df.apply(lambda r: is_air_row(r.to_dict()), axis=1)
            & (df["Hex"].apply(is_blank) | df["RGB"].apply(is_blank))
        ]

        still_missing.to_excel(writer, index=False, sheet_name="Still_Missing_Air")

    report_df = pd.DataFrame(report_rows)
    report_df.to_csv(REPORT_CSV, index=False)

    summary = {
        "script": "enrich_air_from_main_paints.py",
        "input_csv": str(INPUT_CSV),
        "output_csv": str(OUTPUT_CSV),
        "output_xlsx": str(OUTPUT_XLSX),
        "air_rows_filled": fills,
        "air_rows_needing_review": needs_review,
        "skipped_not_air": skipped_not_air,
        "skipped_already_complete_air": skipped_already_complete,
        "report_csv": str(REPORT_CSV),
    }

    with open(REPORT_JSON, "w", encoding="utf-8") as file:
        json.dump(summary, file, indent=4)

    md = [
        "# Army Painter Air Inheritance Report",
        "",
        f"Input CSV: `{INPUT_CSV}`",
        f"Output CSV: `{OUTPUT_CSV}`",
        f"Output XLSX: `{OUTPUT_XLSX}`",
        "",
        "## Summary",
        "",
        f"- Air rows filled: {fills}",
        f"- Air rows needing review: {needs_review}",
        f"- Skipped non-Air rows: {skipped_not_air}",
        f"- Skipped already-complete Air rows: {skipped_already_complete}",
        "",
        "## Method",
        "",
        "This script fills missing Hex/RGB for Army Painter Air rows by matching the Air paint name against completed non-Air Army Painter paints.",
        "",
        "It only auto-fills when the matched main paint has usable Hex/RGB and there is no conflicting color value.",
    ]

    REPORT_MD.write_text("\n".join(md), encoding="utf-8")

    print("ARMY PAINTER AIR INHERITANCE ENRICHMENT")
    print("---------------------------------------")
    print(f"Input: {INPUT_CSV}")
    print(f"Rows filled: {fills}")
    print(f"Needs review: {needs_review}")
    print()
    print(f"Output CSV: {OUTPUT_CSV}")
    print(f"Output XLSX: {OUTPUT_XLSX}")
    print(f"Report CSV: {REPORT_CSV}")
    print(f"Report JSON: {REPORT_JSON}")
    print(f"Report MD: {REPORT_MD}")


if __name__ == "__main__":
    main()
