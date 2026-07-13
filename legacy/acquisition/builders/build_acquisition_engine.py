from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

ACQ_DIR = PROJECT_ROOT / "src" / "acquisition"
SCRIPTS_DIR = PROJECT_ROOT / "src" / "scripts"

FOLDERS = [
    PROJECT_ROOT / "incoming" / "videos",
    PROJECT_ROOT / "incoming" / "screenshots",
    PROJECT_ROOT / "archive" / "videos",
    PROJECT_ROOT / "archive" / "screenshots",
    PROJECT_ROOT / "review",
    PROJECT_ROOT / "failed",
    PROJECT_ROOT / "data" / "imports",
]

FILES = {
    ACQ_DIR / "__init__.py": "",

    ACQ_DIR / "hashing.py": '''import hashlib
from pathlib import Path


def file_sha256(file_path):
    file_path = Path(file_path)
    sha256 = hashlib.sha256()

    with file_path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            sha256.update(chunk)

    return sha256.hexdigest()
''',

    ACQ_DIR / "scanner.py": '''from pathlib import Path


SUPPORTED_VIDEO = {".mp4", ".mov", ".m4v"}
SUPPORTED_IMAGE = {".png", ".jpg", ".jpeg", ".webp"}


class MediaScanner:
    def __init__(self, incoming_dir="incoming"):
        self.incoming_dir = Path(incoming_dir)

    def scan(self):
        files = []

        if not self.incoming_dir.exists():
            return files

        for path in self.incoming_dir.rglob("*"):
            if not path.is_file():
                continue

            suffix = path.suffix.lower()

            if suffix in SUPPORTED_VIDEO:
                file_type = "video"
            elif suffix in SUPPORTED_IMAGE:
                file_type = "image"
            else:
                continue

            files.append({
                "path": path,
                "file_name": path.name,
                "file_type": file_type,
            })

        return files
''',

    ACQ_DIR / "import_log.py": '''import csv
from datetime import datetime
from pathlib import Path

from src.acquisition.hashing import file_sha256


IMPORT_LOG_PATH = Path("data/imports/import_log.csv")


HEADERS = [
    "File_Hash",
    "File_Name",
    "File_Path",
    "File_Type",
    "Import_Date",
    "Status",
    "Workflow_ID",
    "Notes",
]


class ImportLog:
    def __init__(self, log_path=IMPORT_LOG_PATH):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_log()

    def _ensure_log(self):
        if self.log_path.exists():
            return

        with self.log_path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=HEADERS)
            writer.writeheader()

    def load_hashes(self):
        hashes = set()

        with self.log_path.open("r", newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                hashes.add(row["File_Hash"])

        return hashes

    def already_imported(self, file_path):
        file_hash = file_sha256(file_path)
        return file_hash in self.load_hashes()

    def record(self, file_path, file_type, status, workflow_id="", notes=""):
        file_path = Path(file_path)
        file_hash = file_sha256(file_path)

        with self.log_path.open("a", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=HEADERS)
            writer.writerow({
                "File_Hash": file_hash,
                "File_Name": file_path.name,
                "File_Path": str(file_path),
                "File_Type": file_type,
                "Import_Date": datetime.now().isoformat(timespec="seconds"),
                "Status": status,
                "Workflow_ID": workflow_id,
                "Notes": notes,
            })
''',

    ACQ_DIR / "review_queue.py": '''import csv
from datetime import datetime
from pathlib import Path


REVIEW_QUEUE_PATH = Path("review/review_queue.csv")


HEADERS = [
    "Created_At",
    "Source_File",
    "Workflow_ID",
    "Issue_Type",
    "Issue_Detail",
    "Status",
]


class ReviewQueue:
    def __init__(self, queue_path=REVIEW_QUEUE_PATH):
        self.queue_path = Path(queue_path)
        self.queue_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_queue()

    def _ensure_queue(self):
        if self.queue_path.exists():
            return

        with self.queue_path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=HEADERS)
            writer.writeheader()

    def add(self, source_file, issue_type, issue_detail, workflow_id=""):
        with self.queue_path.open("a", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=HEADERS)
            writer.writerow({
                "Created_At": datetime.now().isoformat(timespec="seconds"),
                "Source_File": str(source_file),
                "Workflow_ID": workflow_id,
                "Issue_Type": issue_type,
                "Issue_Detail": issue_detail,
                "Status": "Open",
            })
''',

    ACQ_DIR / "import_manager.py": '''from src.acquisition.scanner import MediaScanner
from src.acquisition.import_log import ImportLog
from src.acquisition.review_queue import ReviewQueue


class ImportManager:
    def __init__(self):
        self.scanner = MediaScanner()
        self.import_log = ImportLog()
        self.review_queue = ReviewQueue()

    def run(self):
        files = self.scanner.scan()

        results = {
            "found": len(files),
            "new": 0,
            "duplicates": 0,
            "queued_for_review": 0,
        }

        for item in files:
            path = item["path"]
            file_type = item["file_type"]

            if self.import_log.already_imported(path):
                results["duplicates"] += 1
                continue

            self.import_log.record(
                file_path=path,
                file_type=file_type,
                status="Queued",
                notes="Detected by acquisition scanner",
            )

            self.review_queue.add(
                source_file=path,
                issue_type="Needs Extraction",
                issue_detail="File detected and queued for workflow extraction.",
            )

            results["new"] += 1
            results["queued_for_review"] += 1

        return results
''',

    SCRIPTS_DIR / "acquisition_doctor.py": '''from pathlib import Path

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

    print("\\nPATH CHECKS")
    print("-" * 60)

    for path in REQUIRED_PATHS:
        exists = path.exists()
        path_results.append(exists)
        status = "PASS" if exists else "FAIL"
        print(f"{status:<6} {path}")

    print("\\nSCAN CHECK")
    print("-" * 60)

    manager = ImportManager()
    results = manager.run()

    print(f"Files found:        {results['found']}")
    print(f"New queued:         {results['new']}")
    print(f"Duplicates skipped: {results['duplicates']}")
    print(f"Review queued:      {results['queued_for_review']}")

    print("\\n" + "=" * 60)

    if all(path_results):
        print("ACQUISITION STATUS: PASS")
    else:
        print("ACQUISITION STATUS: FAIL")

    print("=" * 60)


if __name__ == "__main__":
    main()
'''
}


def write_file(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"WROTE: {path}")


def main():
    print("=" * 60)
    print("BUILDING ACQUISITION ENGINE")
    print("=" * 60)

    for folder in FOLDERS:
        folder.mkdir(parents=True, exist_ok=True)
        print(f"CREATED DIR: {folder}")

    for path, content in FILES.items():
        write_file(path, content)

    print("=" * 60)
    print("DONE")
    print("=" * 60)
    print("Run:")
    print("python -m src.scripts.acquisition_doctor")


if __name__ == "__main__":
    main()