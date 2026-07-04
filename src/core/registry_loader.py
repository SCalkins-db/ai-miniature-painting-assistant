import json
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

from pathlib import Path
import pandas as pd

from src.utils.normalization import build_key
from src.core.paths import REGISTRY_MANIFEST


FINAL_COLUMNS = [
    "Paint_ID",
    "Company",
    "Brand",
    "Product_Line",
    "Paint_Name",
    "Hex",
    "RGB",
    "Paint_Type",
    "Status",
    "Source",
    "Notes",
]


def load_registries(registry_folder: str = "data/registries_csv"):
    project_root = Path(__file__).resolve().parents[2]
    registry_path = project_root / registry_folder
    csv_files = sorted([p for p in registry_path.glob("*.csv") if not _manifest_active_csv_names() or p.name in _manifest_active_csv_names()])

    if not csv_files:
        raise FileNotFoundError(
            f"No CSV files found in {registry_path}"
        )

    dataframes = []

    for csv_file in csv_files:
        df = pd.read_csv(csv_file)

        for column in FINAL_COLUMNS:
            if column not in df.columns:
                df[column] = ""

        df = df[FINAL_COLUMNS].copy()
        df["Registry_File"] = csv_file.name

        dataframes.append(df)

    master_df = pd.concat(dataframes, ignore_index=True)

    master_df["Canonical_Paint_Key"] = master_df.apply(
        lambda row: build_key(
            row.get("Company"),
            row.get("Product_Line"),
            row.get("Paint_Name"),
        ),
        axis=1,
    )

    master_df["Canonical_Search_Key"] = master_df.apply(
        lambda row: build_key(
            row.get("Company"),
            row.get("Brand"),
            row.get("Product_Line"),
            row.get("Paint_Type"),
            row.get("Paint_Name"),
        ),
        axis=1,
    )

    return master_df



def _manifest_active_csv_names() -> set[str]:
    if not REGISTRY_MANIFEST.exists():
        return set()
    try:
        manifest = json.loads(REGISTRY_MANIFEST.read_text(encoding="utf-8"))
    except Exception:
        return set()

    active = set()
    for company_data in manifest.values():
        filename = company_data.get("active_csv")
        if filename:
            active.add(filename)
    return active
