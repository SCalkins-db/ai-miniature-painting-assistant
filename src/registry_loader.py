from pathlib import Path
import pandas as pd


def load_registries(registry_folder="data/registries_csv"):

    # Always locate project root regardless of where script is launched
    project_root = Path(__file__).parent.parent

    registry_path = project_root / registry_folder

    csv_files = list(registry_path.glob("*.csv"))

    if not csv_files:
        raise FileNotFoundError(
            f"No CSV files found in {registry_path}"
        )

    dataframes = []

    for csv_file in csv_files:
        df = pd.read_csv(csv_file)
        dataframes.append(df)

    master_df = pd.concat(dataframes, ignore_index=True)

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
        "Notes"
    ]

    master_df = master_df[FINAL_COLUMNS]

    return master_df