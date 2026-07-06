import subprocess
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
