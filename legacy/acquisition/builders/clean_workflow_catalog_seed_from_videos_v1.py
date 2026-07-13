from pathlib import Path
import csv
import re
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]

CATALOG_DIR = PROJECT_ROOT / "data" / "workflows" / "workflow_catalog"

INPUT_FILE = CATALOG_DIR / "workflow_catalog_seed_from_videos_v1.csv"
OUTPUT_FILE = CATALOG_DIR / "workflow_catalog_seed_from_videos_cleaned_v1.csv"
OUTPUT_FILE = CATALOG_DIR / "workflow_catalog_seed_from_videos_cleaned_v1.xlsx"

def clean_text(value):
    if value is None:
        return ""
    return str(value).strip()


def normalize_spaces(value):
    return re.sub(r"\s+", " ", value).strip()


def strip_before_first_capital(unit):
    """
    Removes everything before the first capital letter.

    Examples:
        "ey Space Wolves Redemptor" -> "Space Wolves Redemptor"
        "5d Black Templars Intercessors" -> "Black Templars Intercessors"
        "### Emperor's Champion" -> "Emperor's Champion"
    """
    return re.sub(r"^[^A-Z]*", "", unit)


def strip_metadata_from_unit(unit, row):
    """
    Removes faction/subfaction/army names from anywhere in the unit.

    Examples:
        "Space Wolves Redemptor" -> "Redemptor"
        "Black Templars Intercessors" -> "Intercessors"
    """
    removals = []

    for column in ["Faction", "Subfaction", "Army"]:
        value = clean_text(row.get(column, ""))

        if not value:
            continue

        pieces = [piece.strip() for piece in value.split(";") if piece.strip()]
        removals.extend(pieces)

    removals = sorted(set(removals), key=len, reverse=True)

    for removal in removals:
        unit = re.sub(
            r"\b" + re.escape(removal) + r"\b",
            "",
            unit,
            flags=re.IGNORECASE,
        )

    return normalize_spaces(unit).strip(" -_:;,.()[]{}#*&")


def basic_noise_cleanup(unit):
    unit = clean_text(unit)

    unit = unit.replace("(+)", "")
    unit = unit.replace("+", "")
    unit = unit.replace("|", "")
    unit = unit.replace("•", "")
    unit = unit.replace("©", "")
    unit = unit.replace("®", "")
    unit = unit.replace("™", "")

    unit = re.sub(r"\([^)]*$", "", unit)
    unit = re.sub(r"\s+", " ", unit)

    return unit.strip(" -_:;,.()[]{}#*&")


def clean_unit(unit, row):
    unit = basic_noise_cleanup(unit)
    unit = strip_before_first_capital(unit)
    unit = strip_metadata_from_unit(unit, row)
    unit = normalize_spaces(unit)

    return unit.strip(" -_:;,.()[]{}#*&")


def looks_like_garbage(unit):
    value = clean_text(unit)

    if len(value) < 3:
        return True

    if value.isdigit():
        return True

    if re.fullmatch(r"[^\w]+", value):
        return True

    letters = re.findall(r"[A-Za-z]", value)
    if len(letters) < 3:
        return True

    return False


def rebuild_workflow_id(row, unit):
    parts = [
        clean_text(row.get("Superfaction", "")),
        clean_text(row.get("Faction", "")),
        clean_text(row.get("Subfaction", "")),
        unit,
        "Workflow",
    ]

    text = "_".join(part for part in parts if part)
    text = text.upper()
    text = re.sub(r"[^A-Z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text)

    return text.strip("_")


def main():
    print("=" * 60)
    print("CLEAN WORKFLOW CATALOG SEED FROM VIDEOS V1")
    print("=" * 60)

    if not INPUT_FILE.exists():
        print("Missing input file:")
        print(INPUT_FILE)
        return

    cleaned_rows = []
    dropped = 0

    with INPUT_FILE.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []

        for row in reader:
            original_unit = clean_text(row.get("Unit", ""))
            cleaned_unit = clean_unit(original_unit, row)

            if looks_like_garbage(cleaned_unit):
                dropped += 1
                continue

            row["Unit"] = cleaned_unit
            row["Workflow_ID"] = rebuild_workflow_id(row, cleaned_unit)
            row["Review_Status"] = "Needs Review"
            row["Notes"] = "Cleaned from OCR seed. Verify unit name before merge."

            cleaned_rows.append(row)

    unique = {}

    for row in cleaned_rows:
        key = (
            clean_text(row.get("Superfaction", "")),
            clean_text(row.get("Faction", "")),
            clean_text(row.get("Subfaction", "")),
            clean_text(row.get("Unit", "")),
            clean_text(row.get("Source_Video", "")),
        )

        if key not in unique:
            unique[key] = row

    final_rows = sorted(
        unique.values(),
        key=lambda row: (
            clean_text(row.get("Superfaction", "")),
            clean_text(row.get("Faction", "")),
            clean_text(row.get("Subfaction", "")),
            clean_text(row.get("Unit", "")),
        ),
    )

    output_df = pd.DataFrame(final_rows, columns=fieldnames)

    with pd.ExcelWriter(
            OUTPUT_FILE,
            engine="openpyxl",
    ) as writer:
        output_df.to_excel(
            writer,
            sheet_name="Catalog Review",
            index=False,
        )

        worksheet = writer.sheets["Catalog Review"]

        # Freeze the header row.
        worksheet.freeze_panes = "A2"

        # Turn on Excel filtering.
        worksheet.auto_filter.ref = worksheet.dimensions

        # Set practical column widths for manual review.
        column_widths = {
            "A": 55,  # Workflow_ID
            "B": 16,  # Superfaction
            "C": 24,  # Faction
            "D": 30,  # Subfaction
            "E": 30,  # Army
            "F": 45,  # Unit
            "G": 16,  # Unit_Type
            "H": 35,  # Source
            "I": 45,  # Source_Video
            "J": 18,  # Review_Status
            "K": 60,  # Notes
        }

        for column, width in column_widths.items():
            worksheet.column_dimensions[column].width = width

        # Keep long text readable.
        for row in worksheet.iter_rows(min_row=2):
            for cell in row:
                cell.alignment = cell.alignment.copy(
                    vertical="top",
                    wrap_text=True,
                )

    print()
    print("SUMMARY")
    print("-" * 60)
    print(f"Input rows ........... {len(cleaned_rows) + dropped}")
    print(f"Dropped garbage ...... {dropped}")
    print(f"Output rows .......... {len(final_rows)}")
    print()
    print("Written:")
    print(OUTPUT_FILE)
    print("=" * 60)


if __name__ == "__main__":
    main()