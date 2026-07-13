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

REGISTRY_DIR = REGISTRIES_CSV_DIR

total = 0
missing = 0

print("REGISTRY SUMMARY")
print("----------------")

for file in sorted(REGISTRY_DIR.glob("*.csv")):
    df = pd.read_csv(file)

    missing_rows = (
        df["Hex"].fillna("").astype(str).str.strip().eq("")
        |
        df["RGB"].fillna("").astype(str).str.strip().eq("")
    ).sum()

    total += len(df)
    missing += missing_rows

    print(f"{file.name}")
    print(f"  Rows: {len(df)}")
    print(f"  Missing: {missing_rows}")
    print()

print("----------------")
print(f"TOTAL ROWS: {total}")
print(f"TOTAL MISSING: {missing}")
