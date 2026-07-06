from pathlib import Path
import time
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

    return 1 if str(value).strip().lower() in ["true", "yes", "1", "owned"] else 0


def safe_int(value):
    if pd.isna(value) or value == "":
        return 0

    try:
        return int(value)
    except ValueError:
        return 0


def sync_paints(conn):
    rows = []

    for registry_dir in REGISTRY_DIRS:
        if not registry_dir.exists():
            continue

        for csv_path in registry_dir.glob("*.csv"):
            df = pd.read_csv(csv_path).fillna("")

            for _, row in df.iterrows():
                paint_id = row.get("Paint_ID", "")

                if not paint_id:
                    continue

                rows.append(
                    (
                        paint_id,
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
                    )
                )

    conn.executemany(
        """
        INSERT OR REPLACE INTO paints (
            paint_id,
            company,
            brand,
            product_line,
            paint_name,
            hex,
            rgb,
            paint_type,
            status,
            source,
            notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )

    return len(rows)


def sync_inventory(conn):
    if not INVENTORY_PATH.exists():
        return 0

    df = pd.read_csv(INVENTORY_PATH).fillna("")
    rows = []

    for _, row in df.iterrows():
        paint_id = row.get("Paint_ID", "")

        if not paint_id:
            continue

        rows.append(
            (
                paint_id,
                bool_to_int(row.get("Owned", "")),
                bool_to_int(row.get("Wishlist", "")),
                safe_int(row.get("Qty", 0)),
            )
        )

    conn.executemany(
        """
        INSERT OR REPLACE INTO inventory (
            paint_id,
            owned,
            wishlist,
            qty
        )
        VALUES (?, ?, ?, ?)
        """,
        rows,
    )

    return len(rows)


def sync_workflow_catalog(conn):
    if not WORKFLOW_CATALOG_PATH.exists():
        return 0

    df = pd.read_csv(WORKFLOW_CATALOG_PATH).dropna(how="all").fillna("")
    rows = []

    for _, row in df.iterrows():
        workflow_id = row.get("Workflow_ID", "")

        if not workflow_id:
            continue

        rows.append(
            (
                workflow_id,
                row.get("Superfaction", ""),
                row.get("Faction", ""),
                "",
                "",
                row.get("Unit", ""),
                row.get("Character", ""),
                "",
                "",
                "",
                "",
                row.get("Workflow_File", ""),
                row.get("Status", ""),
                bool_to_int(row.get("Verified", "")),
                row.get("Notes", ""),
            )
        )

    conn.executemany(
        """
        INSERT OR REPLACE INTO workflows (
            workflow_id,
            superfaction,
            faction,
            subfaction,
            army,
            unit,
            character,
            classification,
            painter,
            video_title,
            youtube_url,
            workflow_file,
            status,
            verified,
            notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )

    return len(rows)


def main():
    print("=" * 60)
    print("SYNCING CSV DATA TO SQLITE")
    print("=" * 60)

    manager = DatabaseManager()
    manager.initialize()

    start = time.perf_counter()

    with manager.connect() as conn:
        paints_start = time.perf_counter()
        paints = sync_paints(conn)
        paints_time = time.perf_counter() - paints_start

        inventory_start = time.perf_counter()
        inventory = sync_inventory(conn)
        inventory_time = time.perf_counter() - inventory_start

        workflows_start = time.perf_counter()
        workflows = sync_workflow_catalog(conn)
        workflows_time = time.perf_counter() - workflows_start

        conn.commit()

    total_time = time.perf_counter() - start

    print(f"Paints synced: {paints} ({paints_time:.2f}s)")
    print(f"Inventory synced: {inventory} ({inventory_time:.2f}s)")
    print(f"Workflows synced: {workflows} ({workflows_time:.2f}s)")
    print(f"Total sync time: {total_time:.2f}s")
    print("=" * 60)


if __name__ == "__main__":
    main()