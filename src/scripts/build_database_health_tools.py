from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATABASE_SRC_DIR = PROJECT_ROOT / "src" / "database"
DEBUG_DIR = PROJECT_ROOT / "src" / "debug"


FILES = {
    DATABASE_SRC_DIR / "database_statistics.py": '''from src.database.database_manager import DatabaseManager


TABLES = [
    "paints",
    "inventory",
    "workflows",
    "workflow_steps",
    "techniques",
    "import_files",
    "review_queue",
]


def get_table_counts():
    manager = DatabaseManager()
    counts = {}

    for table in TABLES:
        row = manager.fetch_one(f"SELECT COUNT(*) FROM {table}")
        counts[table] = row[0]

    return counts


def main():
    print("=" * 60)
    print("DATABASE STATISTICS")
    print("=" * 60)

    counts = get_table_counts()

    for table, count in counts.items():
        print(f"{table:<20} {count}")

    print("=" * 60)


if __name__ == "__main__":
    main()
''',

    DATABASE_SRC_DIR / "database_integrity.py": '''from src.database.database_manager import DatabaseManager


def run_integrity_checks():
    manager = DatabaseManager()
    results = []

    integrity = manager.fetch_one("PRAGMA integrity_check;")[0]
    results.append(("SQLite integrity_check", integrity == "ok", integrity))

    foreign_keys = manager.fetch_all("PRAGMA foreign_key_check;")
    results.append(("Foreign key check", len(foreign_keys) == 0, str(foreign_keys)))

    orphan_inventory = manager.fetch_one("""
        SELECT COUNT(*)
        FROM inventory i
        LEFT JOIN paints p ON i.paint_id = p.paint_id
        WHERE p.paint_id IS NULL
    """)[0]
    results.append(("Orphan inventory paints", orphan_inventory == 0, orphan_inventory))

    orphan_steps_workflows = manager.fetch_one("""
        SELECT COUNT(*)
        FROM workflow_steps ws
        LEFT JOIN workflows w ON ws.workflow_id = w.workflow_id
        WHERE w.workflow_id IS NULL
    """)[0]
    results.append(("Orphan workflow steps", orphan_steps_workflows == 0, orphan_steps_workflows))

    return results


def main():
    print("=" * 60)
    print("DATABASE INTEGRITY")
    print("=" * 60)

    results = run_integrity_checks()

    for label, passed, detail in results:
        status = "PASS" if passed else "FAIL"
        print(f"{status:<6} {label:<30} {detail}")

    print("=" * 60)

    if all(passed for _, passed, _ in results):
        print("DATABASE INTEGRITY: PASS")
    else:
        print("DATABASE INTEGRITY: FAIL")

    print("=" * 60)


if __name__ == "__main__":
    main()
''',

    DATABASE_SRC_DIR / "database_optimize.py": '''from src.database.database_manager import DatabaseManager


def optimize_database():
    manager = DatabaseManager()

    with manager.connect() as conn:
        conn.execute("ANALYZE;")
        conn.execute("PRAGMA optimize;")
        conn.commit()


def main():
    print("=" * 60)
    print("DATABASE OPTIMIZE")
    print("=" * 60)

    optimize_database()

    print("Optimization complete.")
    print("=" * 60)


if __name__ == "__main__":
    main()
''',

    DATABASE_SRC_DIR / "database_vacuum.py": '''from src.database.database_manager import DatabaseManager
from src.database.database_paths import DATABASE_PATH


def vacuum_database():
    manager = DatabaseManager()

    before = DATABASE_PATH.stat().st_size if DATABASE_PATH.exists() else 0

    with manager.connect() as conn:
        conn.execute("VACUUM;")
        conn.commit()

    after = DATABASE_PATH.stat().st_size if DATABASE_PATH.exists() else 0

    return before, after


def main():
    print("=" * 60)
    print("DATABASE VACUUM")
    print("=" * 60)

    before, after = vacuum_database()

    print(f"Before: {before} bytes")
    print(f"After:  {after} bytes")
    print("=" * 60)


if __name__ == "__main__":
    main()
''',

    DATABASE_SRC_DIR / "database_health.py": '''import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


COMMANDS = [
    ("Database builder", ["python", "-m", "src.database.database_builder"]),
    ("Database sync", ["python", "-m", "src.database.database_sync"]),
    ("Database statistics", ["python", "-m", "src.database.database_statistics"]),
    ("Database integrity", ["python", "-m", "src.database.database_integrity"]),
    ("Database optimize", ["python", "-m", "src.database.database_optimize"]),
    ("Database test", ["python", "-m", "src.debug.database_test"]),
]


def run(label, command):
    print("=" * 60)
    print(label)
    print("=" * 60)

    result = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
    )

    print(result.stdout)

    if result.returncode != 0:
        print(result.stderr)
        print(f"FAILED: {label}")
        return False

    print(f"PASS: {label}")
    return True


def main():
    print("=" * 60)
    print("DATABASE HEALTH")
    print("=" * 60)

    results = []

    for label, command in COMMANDS:
        results.append(run(label, command))

    print("=" * 60)

    if all(results):
        print("DATABASE HEALTH: PASS")
    else:
        print("DATABASE HEALTH: FAIL")

    print("=" * 60)


if __name__ == "__main__":
    main()
''',

    DEBUG_DIR / "database_health_test.py": '''from src.database.database_statistics import get_table_counts
from src.database.database_integrity import run_integrity_checks


print("=" * 60)
print("DATABASE HEALTH TEST")
print("=" * 60)

counts = get_table_counts()

print("\\nTABLE COUNTS:")
for table, count in counts.items():
    print(f"{table:<20} {count}")

print("\\nINTEGRITY:")
results = run_integrity_checks()

for label, passed, detail in results:
    status = "PASS" if passed else "FAIL"
    print(f"{status:<6} {label:<30} {detail}")

print("=" * 60)

if all(passed for _, passed, _ in results):
    print("DATABASE HEALTH TEST: PASS")
else:
    print("DATABASE HEALTH TEST: FAIL")

print("=" * 60)
'''
}


def write_file(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"WROTE: {path}")


def main():
    print("=" * 60)
    print("BUILDING DATABASE HEALTH TOOLS")
    print("=" * 60)

    for path, content in FILES.items():
        write_file(path, content)

    print("=" * 60)
    print("DONE")
    print("=" * 60)
    print("Run:")
    print("python -m src.database.database_health")
    print("python -m src.debug.database_health_test")


if __name__ == "__main__":
    main()