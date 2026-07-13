from pathlib import Path
import csv
from datetime import datetime

from src.acquisition.hashing import file_sha256


# ============================================================
# IMAGE PROCESSING LOG
# ============================================================
#
# PURPOSE
# -------
# Tracks screenshots and extracted video frames that have already
# gone through workflow extraction.
#
# WHY THIS EXISTS
# ---------------
# OCR/workflow extraction is expensive. If the same 10,000 images
# get scanned every run, the pipeline becomes useless bullshit.
#
# This log lets the pipeline skip images that were already processed
# for the current processing version.
#
# ============================================================


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOG_PATH = PROJECT_ROOT / "data" / "imports" / "image_processing_log.csv"
PROCESSING_VERSION = "v1"


HEADERS = [
    "Image_Hash",
    "Image_File",
    "Image_Path",
    "Source_Group",
    "Processing_Version",
    "Workflow_Extraction_Status",
    "Processed_At",
    "Notes",
]


class ImageProcessingLog:
    def __init__(self, log_path=LOG_PATH):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_log()

    def _ensure_log(self):
        if self.log_path.exists():
            return

        with self.log_path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=HEADERS)
            writer.writeheader()

    def load_rows(self):
        with self.log_path.open("r", newline="", encoding="utf-8") as file:
            return list(csv.DictReader(file))

    def completed_hashes(self):
        hashes = set()

        for row in self.load_rows():
            if (
                row.get("Processing_Version") == PROCESSING_VERSION
                and row.get("Workflow_Extraction_Status") == "Complete"
            ):
                hashes.add(row.get("Image_Hash"))

        return hashes

    def is_processed_hash(self, image_hash):
        return image_hash in self.completed_hashes()

    def hash_image(self, image_path):
        return file_sha256(image_path)

    def record_complete(self, image_path, image_hash=None, source_group="", notes=""):
        image_path = Path(image_path)

        if image_hash is None:
            image_hash = self.hash_image(image_path)

        if self.is_processed_hash(image_hash):
            return

        with self.log_path.open("a", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=HEADERS)
            writer.writerow({
                "Image_Hash": image_hash,
                "Image_File": image_path.name,
                "Image_Path": str(image_path),
                "Source_Group": source_group,
                "Processing_Version": PROCESSING_VERSION,
                "Workflow_Extraction_Status": "Complete",
                "Processed_At": datetime.now().isoformat(timespec="seconds"),
                "Notes": notes,
            })
