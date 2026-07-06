from pathlib import Path

from src.acquisition.import_manager import ImportManager


PROJECT_ROOT = Path(__file__).resolve().parents[2]


REQUIRED_PATHS = [
    PROJECT_ROOT / "src" / "acquisition",
    PROJECT_ROOT / "incoming" / "videos",
    PROJECT_ROOT / "incoming" / "screenshots",
    PROJECT_ROOT / "archive" / "videos",
    PROJECT_ROOT / "archive" / "screenshots",
    PROJECT_ROOT / "review",
    PROJECT_ROOT / "failed",
    PROJECT_ROOT / "data" / "imports",
]


def main():
    print("=" * 60)
    print("ACQUISITION DOCTOR")
    print("=" * 60)

    path_results = []

    print("\nPATH CHECKS")
    print("-" * 60)

    for path in REQUIRED_PATHS:
        exists = path.exists()
        path_results.append(exists)
        status = "PASS" if exists else "FAIL"
        print(f"{status:<6} {path}")

    print("\nSCAN CHECK")
    print("-" * 60)

    manager = ImportManager()
    results = manager.run()

    print(f"Files found:        {results['found']}")
    print(f"New queued:         {results['new']}")
    print(f"Duplicates skipped: {results['duplicates']}")
    print(f"Review queued:      {results['queued_for_review']}")

    print("\n" + "=" * 60)

    if all(path_results):
        print("ACQUISITION STATUS: PASS")
    else:
        print("ACQUISITION STATUS: FAIL")

    print("=" * 60)


if __name__ == "__main__":
    main()
