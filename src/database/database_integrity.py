from src.database.database_manager import DatabaseManager


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
