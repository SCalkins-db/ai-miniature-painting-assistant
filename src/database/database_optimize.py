from src.database.database_manager import DatabaseManager


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
