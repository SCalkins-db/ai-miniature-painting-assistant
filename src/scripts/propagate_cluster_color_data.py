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
from collections import defaultdict
import pandas as pd
from src.core.paths import PROJECT_ROOT, SRC_DIR, DATA_DIR, REGISTRIES_CSV_DIR, REGISTRIES_XLSX_DIR, MAPPINGS_DIR, REPORTS_DIR, SOURCE_DOCUMENTS_DIR, AUDIT_DIR, CSV_DIR, XLSX_DIR, SOURCE_DOCS_DIR

from src.utils.normalization import build_key


DATA_DIR = PROJECT_ROOT / "data"
REGISTRY_DIR = DATA_DIR / "registries_csv"
REPORTS_DIR = DATA_DIR / "reports"

REPORT_FILE = REPORTS_DIR / "cluster_color_propagation_report.csv"

REQUIRED_COLUMNS = [
    "Paint_ID",
    "Company",
    "Paint_Name",
    "Hex",
    "RGB",
]


def is_blank(value) -> bool:
    if pd.isna(value):
        return True

    value = str(value).strip()

    return value == "" or value.lower() in {"nan", "none", "null"}


def has_color(row) -> bool:
    return not is_blank(row.get("Hex")) and not is_blank(row.get("RGB"))


def make_cluster_key(row):
    return build_key(
        row.get("Company", ""),
        row.get("Paint_Name", ""),
    )


def main():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    report_rows = []
    total_updated = 0

    for file_path in sorted(REGISTRY_DIR.glob("*.csv")):
        df = pd.read_csv(file_path)

        missing_columns = [
            col for col in REQUIRED_COLUMNS
            if col not in df.columns
        ]

        if missing_columns:
            print(f"Skipping non-registry file: {file_path.name}")
            continue

        clusters = defaultdict(list)

        for index, row in df.iterrows():
            cluster_key = make_cluster_key(row)
            clusters[cluster_key].append(index)

        file_updated = 0

        for cluster_key, indexes in clusters.items():
            cluster_rows = df.loc[indexes]

            color_source_rows = cluster_rows[
                cluster_rows.apply(has_color, axis=1)
            ]

            if color_source_rows.empty:
                continue

            source_row = color_source_rows.iloc[0]
            source_hex = source_row["Hex"]
            source_rgb = source_row["RGB"]
            source_paint_id = source_row["Paint_ID"]

            for index in indexes:
                current_hex = df.at[index, "Hex"]
                current_rgb = df.at[index, "RGB"]

                if not is_blank(current_hex) and not is_blank(current_rgb):
                    continue

                df.at[index, "Hex"] = source_hex
                df.at[index, "RGB"] = source_rgb

                if "Notes" in df.columns:
                    existing_note = df.at[index, "Notes"]

                    new_note = (
                        f"Hex/RGB propagated from same-company color cluster "
                        f"source {source_paint_id}."
                    )

                    if is_blank(existing_note):
                        df.at[index, "Notes"] = new_note
                    else:
                        df.at[index, "Notes"] = f"{existing_note} | {new_note}"

                report_rows.append({
                    "Registry_File": file_path.name,
                    "Updated_Row_Index": int(index + 2),
                    "Updated_Paint_ID": df.at[index, "Paint_ID"],
                    "Company": df.at[index, "Company"],
                    "Product_Line": df.at[index, "Product_Line"] if "Product_Line" in df.columns else "",
                    "Paint_Name": df.at[index, "Paint_Name"],
                    "Source_Paint_ID": source_paint_id,
                    "Source_Product_Line": source_row.get("Product_Line", ""),
                    "Source_Hex": source_hex,
                    "Source_RGB": source_rgb,
                    "Applied_Hex": source_hex,
                    "Applied_RGB": source_rgb,
                    "Cluster_Key": cluster_key,
                })

                file_updated += 1
                total_updated += 1

        if file_updated > 0:
            backup_file = REPORTS_DIR / f"{file_path.stem}_before_cluster_propagation_backup.csv"
            df_original = pd.read_csv(file_path)
            df_original.to_csv(backup_file, index=False)

            df.to_csv(file_path, index=False)

        print(f"{file_path.name}: {file_updated} rows updated")

    report_df = pd.DataFrame(report_rows)
    report_df.to_csv(REPORT_FILE, index=False)

    print()
    print("CLUSTER COLOR PROPAGATION")
    print("-------------------------")
    print(f"Total rows updated: {total_updated}")
    print(f"Report saved to: {REPORT_FILE}")


if __name__ == "__main__":
    main()
