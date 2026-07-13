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
REPORTS_DIR = DATA_DIR / "reports"

EQUIVALENCY_FILE = DATA_DIR / "paint_equivalency_database.csv"

REGISTRY_DUPES_REPORT = REPORTS_DIR / "duplicate_registry_entries.csv"
EQUIV_DUPES_REPORT = REPORTS_DIR / "duplicate_equivalency_entries.csv"


def audit_registry_duplicates():
    rows = []

    for file_path in sorted(REGISTRY_DIR.glob("*.csv")):
        df = pd.read_csv(file_path)

        df["_exact_key"] = df.apply(
            lambda row: build_key(
                row.get("Company"),
                row.get("Product_Line"),
                row.get("Paint_Name"),
            ),
            axis=1,
        )

        df["_loose_key"] = df.apply(
            lambda row: build_key(
                row.get("Company"),
                row.get("Paint_Name"),
            ),
            axis=1,
        )

        exact_dupes = df[df.duplicated("_exact_key", keep=False)].copy()
        exact_dupes["Duplicate_Type"] = "Exact: Company + Product_Line + Paint_Name"
        exact_dupes["Registry_File"] = file_path.name

        loose_dupes = df[df.duplicated("_loose_key", keep=False)].copy()
        loose_dupes["Duplicate_Type"] = "Loose: Company + Paint_Name"
        loose_dupes["Registry_File"] = file_path.name

        rows.append(exact_dupes)
        rows.append(loose_dupes)

    if rows:
        return pd.concat(rows, ignore_index=True)

    return pd.DataFrame()


def audit_equivalency_duplicates():
    df = pd.read_csv(EQUIVALENCY_FILE)

    df["_relationship_key"] = df.apply(
        lambda row: build_key(
            row.get("Source_Company"),
            row.get("Source_Product_Line"),
            row.get("Source_Paint_Name"),
            row.get("Equivalent_Company"),
            row.get("Equivalent_Product_Line"),
            row.get("Equivalent_Paint_Name"),
        ),
        axis=1,
    )

    dupes = df[df.duplicated("_relationship_key", keep=False)].copy()

    return dupes


def main():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    registry_dupes = audit_registry_duplicates()
    equivalency_dupes = audit_equivalency_duplicates()

    registry_dupes.to_csv(REGISTRY_DUPES_REPORT, index=False)
    equivalency_dupes.to_csv(EQUIV_DUPES_REPORT, index=False)

    print("REDUNDANT ENTRY AUDIT")
    print("---------------------")
    print(f"Registry duplicate rows found: {len(registry_dupes)}")
    print(f"Equivalency duplicate rows found: {len(equivalency_dupes)}")
    print()
    print(f"Registry duplicate report: {REGISTRY_DUPES_REPORT}")
    print(f"Equivalency duplicate report: {EQUIV_DUPES_REPORT}")


if __name__ == "__main__":
    main()
