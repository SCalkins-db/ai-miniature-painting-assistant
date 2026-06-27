from pathlib import Path
import csv
import re


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_DIR = PROJECT_ROOT / "data" / "imports" / "extracted_text" / "dakka"
OUTPUT_DIR = PROJECT_ROOT / "data" / "imports" / "parsed" / "dakka"
OUTPUT_FILE = OUTPUT_DIR / "dakka_equivalencies.csv"

HEX_RE = re.compile(r"^[A-Fa-f0-9]{6}$")
PAINT_CODE_RE = re.compile(r"\(([^)]*)\)")


COLUMNS = [
    "Source_Company",
    "Source_Product_Line",
    "Source_Paint_Name",
    "Source_Paint_ID",
    "Equivalent_Company",
    "Equivalent_Product_Line",
    "Equivalent_Paint_Name",
    "Equivalent_Paint_ID",
    "Match_Type",
    "Similarity_Percent",
    "Confidence",
    "Source",
    "Notes",
    "Hex",
]

HEADER_LINES = (
    "Citadel paints with every known equivalent",
    "Please note",
    "Paint Comparison Chart",
    "Colour Comparison",
    "www.dakkadakka.com",
    "Compiled by",
    "Version",
)

def clean_line(line: str) -> str:
    return (
        line.replace("\xa0", " ")
        .replace("|", "")
        .strip()
    )


def is_noise(line: str) -> bool:
    if any(text in line for text in HEADER_LINES):
        return True

    if not line:
        return True

    noise_prefixes = (
        "--- PAGE",
        "Paint Comparison Chart",
        "Unable to find",
        "note, hex codes",
        "Colour",
        "New Citadel",
        "Old Citadel",
        "Vallejo Game Color",
        "Vallejo Model Color",
        "INSTAR",
        "Rackham",
        "Reaper Master",
        "Privateer",
        "Press P3",
        "Coat D'arms",
        "Army Painter",
        "Scale 75",
        "Two Thin",
        "Hex",
        "Code",
        "https://",
        "Pagina",
        "References",
        "This table has been compiled",
        "http://",
        "(* =",
        "( 1)",
        "( 2)",
        "( 3)",
        "( 4)",
        "( 5)",
        "( 6)",
        "( 7)",
        "( 8)",
    )

    return any(line.startswith(prefix) for prefix in noise_prefixes)


def extract_paint_id(value: str) -> str:
    match = PAINT_CODE_RE.search(value)
    if not match:
        return ""

    return match.group(1).strip()


def strip_code(value: str) -> str:
    return PAINT_CODE_RE.sub("", value).strip()


def guess_company_slots(row_values):
    """
    Dakka chart text is line-based, not table-perfect.
    This parser handles the common older/newer Dakka formats.

    Newer format approximate slots:
    0 New Citadel
    1 Old Citadel
    2 Vallejo Game Color
    3 Vallejo Model Color
    ...
    Army Painter usually appears near the end before Scale75 / Two Thin Coats / Hex.

    Older format approximate slots:
    0 Citadel
    1 Vallejo Game Color
    2 Vallejo Model Color
    3 Rackham
    4 Reaper Master
    5 Coat D'arms
    6 Hex
    """

    return row_values


def make_relationships(row_values, hex_code, source_name):
    relationships = []

    if len(row_values) < 2:
        return relationships

    # Use first value as the row's anchor paint.
    # In newer Dakka: New Citadel.
    # In older Dakka: Citadel.
    source_paint = row_values[0]

    if not source_paint:
        return relationships

    source_company = "Games Workshop"
    source_product_line = "Citadel"

    candidates = []

    # Dakka old chart: Citadel, VGC, VMC, Rackham, Reaper, Coat D'arms
    if "258583605-Dakka-Dakka" in source_name:
        slots = [
            ("Vallejo", "Game Color", 1),
            ("Vallejo", "Model Color", 2),
            ("Rackham", "", 3),
            ("Reaper", "Master Series", 4),
            ("Coat D'arms", "", 5),
        ]

    # Dakka newer chart: New Citadel, Old Citadel, VGC, VMC, ... AP, Scale75, Two Thin Coats
    else:
        slots = [
            ("Games Workshop", "Old Citadel", 1),
            ("Vallejo", "Game Color", 2),
            ("Vallejo", "Model Color", 3),
            ("Rackham", "", 6),
            ("Reaper", "Master Series", 7),
            ("Privateer Press", "P3", 8),
            ("Coat D'arms", "", 9),
            ("Army Painter", "", 10),
            ("Scale75", "", 11),
            ("Two Thin Coats", "", 12),
        ]

    for company, product_line, index in slots:
        if index >= len(row_values):
            continue

        equivalent = row_values[index]

        if not equivalent:
            continue

        # Skip values that are clearly not paint names.
        if HEX_RE.match(equivalent):
            continue

        candidates.append((company, product_line, equivalent))

    for equivalent_company, equivalent_product_line, equivalent_name in candidates:
        relationships.append({
            "Source_Company": source_company,
            "Source_Product_Line": source_product_line,
            "Source_Paint_Name": strip_code(source_paint),
            "Source_Paint_ID": extract_paint_id(source_paint),
            "Equivalent_Company": equivalent_company,
            "Equivalent_Product_Line": equivalent_product_line,
            "Equivalent_Paint_Name": strip_code(equivalent_name),
            "Equivalent_Paint_ID": extract_paint_id(equivalent_name),
            "Match_Type": "Dakka Chart Equivalency",
            "Similarity_Percent": "",
            "Confidence": "Medium",
            "Source": source_name,
            "Notes": "Parsed from Dakka paint compatibility chart; hex is approximate.",
            "Hex": hex_code,
        })

    return relationships


def parse_text_file(path: Path):
    raw_lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()

    lines = [
        clean_line(line)
        for line in raw_lines
    ]

    lines = [
        line for line in lines
        if not is_noise(line)
    ]

    rows = []
    buffer = []

    for line in lines:
        if HEX_RE.match(line):
            hex_code = line.upper()

            row_values = [value for value in buffer if value]
            relationships = make_relationships(
                row_values=row_values,
                hex_code=hex_code,
                source_name=path.name,
            )

            rows.extend(relationships)
            buffer = []
        else:
            buffer.append(line)

    return rows


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    text_files = sorted(INPUT_DIR.glob("*.txt"))

    if not text_files:
        raise FileNotFoundError(f"No extracted Dakka text files found in {INPUT_DIR}")

    all_rows = []

    print("PARSE DAKKA EQUIVALENCIES")
    print("-------------------------")

    for text_file in text_files:
        rows = parse_text_file(text_file)
        all_rows.extend(rows)
        print(f"{text_file.name}: {len(rows)} relationship rows parsed")

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(all_rows)

    print()
    print(f"Total relationship rows: {len(all_rows)}")
    print(f"Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()