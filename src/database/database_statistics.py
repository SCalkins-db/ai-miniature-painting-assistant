from src.database.database_manager import DatabaseManager


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
