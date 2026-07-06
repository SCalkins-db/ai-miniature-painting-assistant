from src.acquisition.scanner import MediaScanner
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
