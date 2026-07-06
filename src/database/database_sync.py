from pathlib import Path
import pandas as pd

from src.database.database_manager import DatabaseManager
from src.database.database_paths import PROJECT_ROOT


REGISTRY_DIRS = [
    PROJECT_ROOT / "data" / "registries_csv",
]

INVENTORY_PATH = PROJECT_ROOT / "data" / "inventory.csv"
WORKFLOW_CATALOG_PATH = PROJECT_ROOT / "data" / "workflow_catalog" / "workflow_catalog.csv"


def bool_to_int(value):
    if pd.isna(value):
        return 0

    return str(value).strip().lower() in ["true", "yes", "1", "owned"]


def sync_paints(manager):
    total = 0

    for registry_dir in REGISTRY_DIRS:
        if not registry_dir.exists():
            continue

        for csv_path in registry_dir.glob("*.csv"):
            df = pd.read_csv(csv_path).fillna("")

            for _, row in df.iterrows():
                manager.execute(
                    """
                    INSERT OR REPLACE INTO paints (
                        paint_id, company, brand, product_line, paint_name,
                        hex, rgb, paint_type, status, source, notes
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row.get("Paint_ID", ""),
                        row.get("Company", ""),
                        row.get("Brand", ""),
                        row.get("Product_Line", ""),
                        row.get("Paint_Name", ""),
                        row.get("Hex", ""),
                        row.get("RGB", ""),
                        row.get("Paint_Type", ""),
                        row.get("Status", ""),
                        row.get("Source", ""),
                        row.get("Notes", ""),
                    ),
                )
                total += 1

    return total


def sync_inventory(manager):
    if not INVENTORY_PATH.exists():
        return 0

    df = pd.read_csv(INVENTORY_PATH).fillna("")
    total = 0

    for _, row in df.iterrows():
        manager.execute(
            """
            INSERT OR REPLACE INTO inventory (
                paint_id, owned, wishlist, qty
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                row.get("Paint_ID", ""),
                int(bool_to_int(row.get("Owned", ""))),
                int(bool_to_int(row.get("Wishlist", ""))),
                int(row.get("Qty", 0) or 0),
            ),
        )
        total += 1

    return total


def sync_workflow_catalog(manager):
    if not WORKFLOW_CATALOG_PATH.exists():
        return 0

    df = pd.read_csv(WORKFLOW_CATALOG_PATH).dropna(how="all").fillna("")
    total = 0

    for _, row in df.iterrows():
        manager.execute(
            """
            INSERT OR REPLACE INTO workflows (
                workflow_id,
                superfaction,
                faction,
                unit,
                character,
                workflow_file,
                status,
                verified,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row.get("Workflow_ID", ""),
                row.get("Superfaction", ""),
                row.get("Faction", ""),
                row.get("Unit", ""),
                row.get("Character", ""),
                row.get("Workflow_File", ""),
                row.get("Status", ""),
                int(bool_to_int(row.get("Verified", ""))),
                row.get("Notes", ""),
            ),
        )
        total += 1

    return total


def main():
    print("=" * 60)
    print("SYNCING CSV DATA TO SQLITE")
    print("=" * 60)

    manager = DatabaseManager()
    manager.initialize()

    paints = sync_paints(manager)
    inventory = sync_inventory(manager)
    workflows = sync_workflow_catalog(manager)

    print(f"Paints synced: {paints}")
    print(f"Inventory synced: {inventory}")
    print(f"Workflows synced: {workflows}")
    print("=" * 60)


if __name__ == "__main__":
    main()
