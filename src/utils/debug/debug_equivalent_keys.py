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

from src.utils.normalization import build_key


DATA_DIR = PROJECT_ROOT / "data"
REGISTRY_DIR = DATA_DIR / "registries_csv"
EQUIVALENCY_FILE = DATA_DIR / "paint_equivalency_database.csv"


def main():
    eq = pd.read_csv(EQUIVALENCY_FILE)

    print("FIRST 80 EQUIVALENT KEYS")
    print("------------------------")

    for _, row in eq.head(80).iterrows():
        print(
            row.get("Equivalent_Company"),
            "|",
            row.get("Equivalent_Product_Line"),
            "|",
            row.get("Equivalent_Paint_Name"),
            "=>",
            build_key(
                row.get("Equivalent_Company"),
                row.get("Equivalent_Product_Line"),
                row.get("Equivalent_Paint_Name"),
            ),
        )

    print()
    print("FIRST 120 REGISTRY KEYS WITH COLOR DATA")
    print("---------------------------------------")

    shown = 0

    for file_path in sorted(REGISTRY_DIR.glob("*.csv")):
        df = pd.read_csv(file_path)

        for _, row in df.iterrows():
            hex_value = str(row.get("Hex", "")).strip()
            rgb_value = str(row.get("RGB", "")).strip()

            if not hex_value or not rgb_value:
                continue

            print(
                row.get("Company"),
                "|",
                row.get("Product_Line"),
                "|",
                row.get("Paint_Name"),
                "=>",
                build_key(
                    row.get("Company"),
                    row.get("Product_Line"),
                    row.get("Paint_Name"),
                ),
            )

            shown += 1

            if shown >= 120:
                return


if __name__ == "__main__":
    main()
