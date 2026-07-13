from src.acquisition.scanner import MediaScanner
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
