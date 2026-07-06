from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ACQ_DIR = PROJECT_ROOT / "src" / "acquisition"
SCRIPTS_DIR = PROJECT_ROOT / "src" / "scripts"

FOLDERS = [
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


FILES = {
    ACQ_DIR / "zip_handler.py": '''from pathlib import Path
import zipfile


class ZipHandler:
    def __init__(self, zip_dir="incoming/zips", extract_dir="incoming/extracted"):
        self.zip_dir = Path(zip_dir)
        self.extract_dir = Path(extract_dir)

    def find_zips(self):
        if not self.zip_dir.exists():
            return []

        return sorted(self.zip_dir.glob("*.zip"))

    def extract_zip(self, zip_path):
        zip_path = Path(zip_path)
        target_dir = self.extract_dir / zip_path.stem
        target_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(target_dir)

        return target_dir

    def extract_all(self):
        extracted = []

        for zip_path in self.find_zips():
            target_dir = self.extract_zip(zip_path)
            extracted.append({
                "zip_path": zip_path,
                "extract_dir": target_dir,
            })

        return extracted
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

        return sorted(files, key=lambda item: str(item["path"]).lower())
''',

    ACQ_DIR / "file_router.py": '''from pathlib import Path
import shutil


class FileRouter:
    def __init__(self):
        self.archive_video_dir = Path("archive/videos")
        self.archive_image_dir = Path("archive/screenshots")
        self.archive_zip_dir = Path("archive/zips")
        self.failed_dir = Path("failed")

        for folder in [
            self.archive_video_dir,
            self.archive_image_dir,
            self.archive_zip_dir,
            self.failed_dir,
        ]:
            folder.mkdir(parents=True, exist_ok=True)

    def archive_media(self, file_path, file_type):
        file_path = Path(file_path)

        if not file_path.exists():
            return None

        if file_type == "video":
            target_dir = self.archive_video_dir
        elif file_type == "image":
            target_dir = self.archive_image_dir
        else:
            target_dir = self.failed_dir

        target_path = target_dir / file_path.name

        if target_path.exists():
            target_path = self._dedupe_target(target_path)

        shutil.copy2(file_path, target_path)
        return target_path

    def archive_zip(self, zip_path):
        zip_path = Path(zip_path)

        if not zip_path.exists():
            return None

        target_path = self.archive_zip_dir / zip_path.name

        if target_path.exists():
            target_path = self._dedupe_target(target_path)

        shutil.copy2(zip_path, target_path)
        return target_path

    def _dedupe_target(self, target_path):
        stem = target_path.stem
        suffix = target_path.suffix
        parent = target_path.parent

        counter = 1

        while True:
            candidate = parent / f"{stem}_{counter}{suffix}"

            if not candidate.exists():
                return candidate

            counter += 1
''',

    ACQ_DIR / "import_manager.py": '''from src.acquisition.scanner import MediaScanner
from src.acquisition.import_log import ImportLog
from src.acquisition.review_queue import ReviewQueue
from src.acquisition.zip_handler import ZipHandler
from src.acquisition.file_router import FileRouter


class ImportManager:
    def __init__(self):
        self.zip_handler = ZipHandler()
        self.scanner = MediaScanner()
        self.import_log = ImportLog()
        self.review_queue = ReviewQueue()
        self.router = FileRouter()

    def extract_zips(self):
        extracted = self.zip_handler.extract_all()

        for item in extracted:
            zip_path = item["zip_path"]

            if self.import_log.already_imported(zip_path):
                continue

            archived_path = self.router.archive_zip(zip_path)

            self.import_log.record(
                file_path=zip_path,
                file_type="zip",
                status="Extracted",
                notes=f"Extracted to {item['extract_dir']}; archived to {archived_path}",
            )

        return extracted

    def run(self):
        extracted = self.extract_zips()
        files = self.scanner.scan()

        results = {
            "zips_extracted": len(extracted),
            "found": len(files),
            "new": 0,
            "duplicates": 0,
            "queued_for_review": 0,
            "archived": 0,
        }

        for item in files:
            path = item["path"]
            file_type = item["file_type"]

            if self.import_log.already_imported(path):
                results["duplicates"] += 1
                continue

            archived_path = self.router.archive_media(path, file_type)

            self.import_log.record(
                file_path=path,
                file_type=file_type,
                status="Queued",
                notes=f"Detected by acquisition scanner; archived copy: {archived_path}",
            )

            self.review_queue.add(
                source_file=archived_path or path,
                issue_type="Needs Extraction",
                issue_detail="File detected and queued for workflow extraction.",
            )

            results["new"] += 1
            results["queued_for_review"] += 1

            if archived_path:
                results["archived"] += 1

        return results
''',

    SCRIPTS_DIR / "acquisition_doctor.py": '''from pathlib import Path

from src.acquisition.import_manager import ImportManager


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

    print("\\nINGESTION CHECK")
    print("-" * 60)

    manager = ImportManager()
    results = manager.run()

    print(f"ZIPs extracted:      {results['zips_extracted']}")
    print(f"Media files found:   {results['found']}")
    print(f"New queued:          {results['new']}")
    print(f"Duplicates skipped:  {results['duplicates']}")
    print(f"Review queued:       {results['queued_for_review']}")
    print(f"Archived copies:     {results['archived']}")

    print("\\n" + "=" * 60)

    if all(path_results):
        print("ACQUISITION STATUS: PASS")
    else:
        print("ACQUISITION STATUS: FAIL")

    print("=" * 60)


if __name__ == "__main__":
    main()
''',
}


def write_file(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"WROTE: {path}")


def main():
    print("=" * 60)
    print("BUILDING ACQUISITION ENGINE V2")
    print("=" * 60)

    for folder in FOLDERS:
        folder.mkdir(parents=True, exist_ok=True)
        print(f"ENSURED DIR: {folder}")

    for path, content in FILES.items():
        write_file(path, content)

    print("=" * 60)
    print("DONE")
    print("=" * 60)
    print("Put ZIP files into:")
    print("incoming/zips")
    print("")
    print("Put loose videos into:")
    print("incoming/videos")
    print("")
    print("Put loose screenshots into:")
    print("incoming/screenshots")
    print("")
    print("Then run:")
    print("python -m src.scripts.acquisition_doctor")


if __name__ == "__main__":
    main()