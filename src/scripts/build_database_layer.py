from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATABASE_SRC_DIR = PROJECT_ROOT / "src" / "database"
DATABASE_DIR = PROJECT_ROOT / "database"
DEBUG_DIR = PROJECT_ROOT / "src" / "debug"


FILES = {
    DATABASE_SRC_DIR / "__init__.py": "",

    DATABASE_SRC_DIR / "database_paths.py": '''from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATABASE_DIR = PROJECT_ROOT / "database"
DATABASE_PATH = DATABASE_DIR / "miniature_painting.db"
''',

    DATABASE_SRC_DIR / "database_schema.py": '''SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS paints (
    paint_id TEXT PRIMARY KEY,
    company TEXT,
    brand TEXT,
    product_line TEXT,
    paint_name TEXT NOT NULL,
    hex TEXT,
    rgb TEXT,
    paint_type TEXT,
    status TEXT,
    source TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS inventory (
    paint_id TEXT PRIMARY KEY,
    owned INTEGER DEFAULT 0,
    wishlist INTEGER DEFAULT 0,
    qty INTEGER DEFAULT 0,
    FOREIGN KEY (paint_id) REFERENCES paints(paint_id)
);

CREATE TABLE IF NOT EXISTS workflows (
    workflow_id TEXT PRIMARY KEY,
    superfaction TEXT,
    faction TEXT,
    subfaction TEXT,
    army TEXT,
    unit TEXT,
    character TEXT,
    classification TEXT,
    painter TEXT,
    video_title TEXT,
    youtube_url TEXT,
    workflow_file TEXT,
    status TEXT,
    verified INTEGER DEFAULT 0,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS workflow_steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workflow_id TEXT NOT NULL,
    area_order INTEGER,
    step_order INTEGER,
    model_area TEXT,
    technique TEXT,
    paint_id TEXT,
    paint_name TEXT,
    paint_type TEXT,
    purpose TEXT,
    optional INTEGER DEFAULT 0,
    notes TEXT,
    FOREIGN KEY (workflow_id) REFERENCES workflows(workflow_id),
    FOREIGN KEY (paint_id) REFERENCES paints(paint_id)
);

CREATE TABLE IF NOT EXISTS techniques (
    technique TEXT PRIMARY KEY,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS import_files (
    file_hash TEXT PRIMARY KEY,
    file_name TEXT,
    file_path TEXT,
    file_type TEXT,
    import_date TEXT,
    status TEXT,
    workflow_id TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS review_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file TEXT,
    workflow_id TEXT,
    issue_type TEXT,
    issue_detail TEXT,
    status TEXT DEFAULT 'Open',
    created_at TEXT,
    resolved_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_workflow_steps_workflow_id
ON workflow_steps(workflow_id);

CREATE INDEX IF NOT EXISTS idx_workflow_steps_paint_id
ON workflow_steps(paint_id);

CREATE INDEX IF NOT EXISTS idx_workflows_faction_unit
ON workflows(faction, unit);

CREATE INDEX IF NOT EXISTS idx_paints_name
ON paints(paint_name);
"""
''',

    DATABASE_SRC_DIR / "database_manager.py": '''import sqlite3

from src.database.database_paths import DATABASE_DIR, DATABASE_PATH
from src.database.database_schema import SCHEMA_SQL


class DatabaseManager:
    def __init__(self, database_path=DATABASE_PATH):
        self.database_path = database_path
        DATABASE_DIR.mkdir(parents=True, exist_ok=True)

    def connect(self):
        conn = sqlite3.connect(self.database_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def initialize(self):
        with self.connect() as conn:
            conn.executescript(SCHEMA_SQL)
            conn.commit()

    def execute(self, sql, params=None):
        params = params or ()

        with self.connect() as conn:
            cursor = conn.execute(sql, params)
            conn.commit()
            return cursor

    def fetch_all(self, sql, params=None):
        params = params or ()

        with self.connect() as conn:
            cursor = conn.execute(sql, params)
            return cursor.fetchall()

    def fetch_one(self, sql, params=None):
        params = params or ()

        with self.connect() as conn:
            cursor = conn.execute(sql, params)
            return cursor.fetchone()
''',

    DATABASE_SRC_DIR / "database_builder.py": '''from src.database.database_manager import DatabaseManager
from src.database.database_paths import DATABASE_PATH


def main():
    print("=" * 60)
    print("BUILDING SQLITE DATABASE")
    print("=" * 60)

    manager = DatabaseManager()
    manager.initialize()

    print(f"DATABASE READY: {DATABASE_PATH}")
    print("=" * 60)


if __name__ == "__main__":
    main()
''',

    DATABASE_SRC_DIR / "database_sync.py": '''from pathlib import Path
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
''',

    DATABASE_SRC_DIR / "database_queries.py": '''from src.database.database_manager import DatabaseManager


class DatabaseQueries:
    def __init__(self):
        self.manager = DatabaseManager()

    def count_paints(self):
        row = self.manager.fetch_one("SELECT COUNT(*) FROM paints")
        return row[0]

    def count_inventory(self):
        row = self.manager.fetch_one("SELECT COUNT(*) FROM inventory")
        return row[0]

    def count_workflows(self):
        row = self.manager.fetch_one("SELECT COUNT(*) FROM workflows")
        return row[0]

    def find_paint_by_name(self, paint_name):
        return self.manager.fetch_all(
            """
            SELECT paint_id, company, product_line, paint_name, paint_type
            FROM paints
            WHERE paint_name LIKE ?
            ORDER BY company, product_line, paint_name
            """,
            (f"%{paint_name}%",),
        )

    def find_workflows_by_unit(self, unit):
        return self.manager.fetch_all(
            """
            SELECT workflow_id, superfaction, faction, unit, workflow_file, status
            FROM workflows
            WHERE unit LIKE ?
            ORDER BY faction, unit
            """,
            (f"%{unit}%",),
        )
''',

    DATABASE_SRC_DIR / "database_backup.py": '''from datetime import datetime
from pathlib import Path
import shutil

from src.database.database_paths import DATABASE_PATH, DATABASE_DIR


def backup_database():
    if not DATABASE_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DATABASE_PATH}")

    backup_dir = DATABASE_DIR / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"miniature_painting_{timestamp}.db"

    shutil.copy2(DATABASE_PATH, backup_path)

    return backup_path


def main():
    print("=" * 60)
    print("DATABASE BACKUP")
    print("=" * 60)

    backup_path = backup_database()

    print(f"BACKUP CREATED: {backup_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
''',

    DEBUG_DIR / "database_test.py": '''from src.database.database_manager import DatabaseManager
from src.database.database_queries import DatabaseQueries


print("=" * 60)
print("DATABASE TEST")
print("=" * 60)

manager = DatabaseManager()
manager.initialize()

queries = DatabaseQueries()

print(f"Paint count: {queries.count_paints()}")
print(f"Inventory count: {queries.count_inventory()}")
print(f"Workflow count: {queries.count_workflows()}")

print("\\nFind paint: Macragge")
for row in queries.find_paint_by_name("Macragge"):
    print(row)

print("\\nFind workflow: Intercessors")
for row in queries.find_workflows_by_unit("Intercessors"):
    print(row)

print("=" * 60)
print("DATABASE TEST COMPLETE")
print("=" * 60)
'''
}


def write_file(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"WROTE: {path}")


def main():
    print("=" * 60)
    print("BUILDING DATABASE LAYER")
    print("=" * 60)

    DATABASE_DIR.mkdir(parents=True, exist_ok=True)

    for path, content in FILES.items():
        write_file(path, content)

    print("=" * 60)
    print("DONE")
    print("=" * 60)
    print("Run these next:")
    print("python -m src.database.database_builder")
    print("python -m src.database.database_sync")
    print("python -m src.debug.database_test")


if __name__ == "__main__":
    main()