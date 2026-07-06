from src.database.database_manager import DatabaseManager
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
