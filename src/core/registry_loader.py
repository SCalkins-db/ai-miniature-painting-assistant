from pathlib import Path
import pandas as pd

from src.utils.normalization import build_key


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


def load_registries(registry_folder="data/registries_csv"):
    project_root = Path(__file__).resolve().parent.parent
    registry_path = project_root / registry_folder

    csv_files = sorted(registry_path.glob("*.csv"))

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
