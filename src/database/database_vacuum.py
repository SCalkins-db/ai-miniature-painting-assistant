from src.database.database_manager import DatabaseManager
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
