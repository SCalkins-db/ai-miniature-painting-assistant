from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_DIR = PROJECT_ROOT / "data" / "registries_csv"

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