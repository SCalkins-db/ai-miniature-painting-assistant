from pathlib import Path
import pandas as pd


# ============================================================
# ACQUISITION DOCTOR
# ============================================================
#
# PURPOSE
# -------
# Performs a READ-ONLY health check of the acquisition system.
#
# IMPORTANT
# ---------
# This script MUST NEVER:
#
#   - Extract ZIP files
#   - Process videos
#   - Hash files
#   - Queue files
#   - Run OCR
#   - Archive files
#   - Modify CSVs
#
# It ONLY reports the current health of the acquisition system.
#
# ============================================================


PROJECT_ROOT = Path(__file__).resolve().parents[2]

REQUIRED_PATHS = [
    PROJECT_ROOT / "src" / "acquisition",
    PROJECT_ROOT / "incoming" / "zips",
    PROJECT_ROOT / "incoming" / "videos",
    PROJECT_ROOT / "incoming" / "screenshots",
    PROJECT_ROOT / "incoming" / "extracted",
    PROJECT_ROOT / "archive" / "zips",
    PROJECT_ROOT / "archive" / "videos",
    PROJECT_ROOT / "archive" / "screenshots",
    PROJECT_ROOT / "review",
    PROJECT_ROOT / "failed",
    PROJECT_ROOT / "data" / "imports",
]

IMPORT_LOG = PROJECT_ROOT / "data" / "imports" / "import_log.csv"
REVIEW_QUEUE = PROJECT_ROOT / "review" / "review_queue.csv"

MEDIA_TYPES = {
    ".zip": "zip",
    ".mp4": "video",
    ".mov": "video",
    ".m4v": "video",
    ".avi": "video",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".webp": "image",
}


def count_media(folder: Path):

    counts = {
        "zip": 0,
        "video": 0,
        "image": 0,
        "other": 0,
    }

    if not folder.exists():
        return counts

    for item in folder.rglob("*"):

        if not item.is_file():
            continue

        counts[
            MEDIA_TYPES.get(item.suffix.lower(), "other")
        ] += 1

    return counts


def csv_rows(path):

    if not path.exists():
        return 0

    try:
        return len(pd.read_csv(path))
    except Exception:
        return 0


def main():

    print("=" * 60)
    print("ACQUISITION DOCTOR")
    print("=" * 60)

    print("\nPATH CHECKS")
    print("-" * 60)

    ok = True

    for path in REQUIRED_PATHS:

        exists = path.exists()

        print(f'{"PASS" if exists else "FAIL":<6} {path}')

        ok &= exists

    print("\nREAD ONLY SOURCE COUNTS")
    print("-" * 60)

    total = {
        "zip": 0,
        "video": 0,
        "image": 0,
        "other": 0,
    }

    for folder in [
        PROJECT_ROOT / "incoming",
        PROJECT_ROOT / "archive",
    ]:

        print(f"\n{folder}")

        counts = count_media(folder)

        print(f'ZIP Files     : {counts["zip"]}')
        print(f'Video Files   : {counts["video"]}')
        print(f'Image Files   : {counts["image"]}')
        print(f'Other Files   : {counts["other"]}')

        for key in total:
            total[key] += counts[key]

    print("\nIMPORT STATE")
    print("-" * 60)

    print(f"Import Log Rows : {csv_rows(IMPORT_LOG)}")
    print(f"Review Queue    : {csv_rows(REVIEW_QUEUE)}")

    print("\nTOTAL MEDIA")
    print("-" * 60)

    print(f'ZIP Files     : {total["zip"]}')
    print(f'Video Files   : {total["video"]}')
    print(f'Image Files   : {total["image"]}')
    print(f'Other Files   : {total["other"]}')

    print("\n" + "=" * 60)

    if ok:
        print("ACQUISITION STATUS : PASS")
    else:
        print("ACQUISITION STATUS : FAIL")

    print("=" * 60)


if __name__ == "__main__":
    main()