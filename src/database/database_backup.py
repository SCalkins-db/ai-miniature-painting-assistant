from datetime import datetime
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
