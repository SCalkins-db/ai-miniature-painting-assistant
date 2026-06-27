from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_DIR = PROJECT_ROOT / "data" / "registries_csv"

REQUIRED = {"Paint_ID", "Company", "Brand", "Product_Line", "Paint_Name", "Hex", "RGB"}

for file in sorted(REGISTRY_DIR.glob("*.csv")):
    df = pd.read_csv(file)
    missing = REQUIRED - set(df.columns)

    print(file.name)
    print(f"Columns: {list(df.columns)}")

    if missing:
        print(f"BAD FILE - missing columns: {missing}")
    else:
        print("OK registry file")

    print()