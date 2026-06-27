from pathlib import Path
import pandas as pd

from src.utils.normalization import build_key


PROJECT_ROOT = Path(__file__).resolve().parent.parent
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