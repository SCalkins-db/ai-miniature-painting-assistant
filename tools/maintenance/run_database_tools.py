import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

COMMANDS = [
    ("Build database", ["python", "-m", "src.database.database_builder"]),
    ("Sync CSV data", ["python", "-m", "src.database.database_sync"]),
    ("Run database test", ["python", "-m", "src.debug.database_test"]),
    ("Backup database", ["python", "-m", "src.database.database_backup"]),
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
    print("DATABASE TOOL RUNNER")
    print("=" * 60)

    results = []

    for label, command in COMMANDS:
        results.append(run(label, command))

    print("=" * 60)

    if all(results):
        print("DATABASE TOOLS STATUS: PASS")
    else:
        print("DATABASE TOOLS STATUS: FAIL")

    print("=" * 60)


if __name__ == "__main__":
    main()