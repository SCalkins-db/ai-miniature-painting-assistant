"""
Creates the master workflow catalog CSV.

Run from project root:

.\.venv\Scripts\python.exe .\src\scripts\create_workflow_catalog.py
"""

from pathlib import Path
import csv

PROJECT_ROOT = Path(__file__).resolve().parents[2]

CATALOG_DIR = PROJECT_ROOT / "data" / "workflow_catalog"
CATALOG_FILE = CATALOG_DIR / "workflow_catalog.csv"

HEADERS = [
    "Workflow_ID",
    "Superfaction",
    "Faction",
    "Unit",
    "Character",
    "Workflow_File",
    "Status",
    "Verified",
    "Notes",
]


def main():
    CATALOG_DIR.mkdir(parents=True, exist_ok=True)

    if CATALOG_FILE.exists():
        print(f"Catalog already exists: {CATALOG_FILE}")
        return

    with CATALOG_FILE.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(HEADERS)

    print("Workflow catalog created.")
    print(f"Path: {CATALOG_FILE}")


if __name__ == "__main__":
    main()