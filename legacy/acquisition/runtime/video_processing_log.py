from pathlib import Path
import csv
from datetime import datetime

from src.acquisition.hashing import file_sha256


# ============================================================
# VIDEO PROCESSING LOG
# ============================================================
#
# PURPOSE
# -------
# Tracks which videos have already had frames extracted and
# deduplicated.
#
# WHY THIS EXISTS
# ---------------
# Video processing is expensive. A single screen recording can
# generate hundreds of frames. Without this log, every full
# pipeline run reprocesses every video again like an idiot.
#
# This log lets the pipeline skip videos that were already
# successfully processed.
#
# ============================================================


LOG_PATH = Path("data/imports/video_processing_log.csv")
PROCESSING_VERSION = "v1"


HEADERS = [
    "Video_Hash",
    "Video_File",
    "Video_Path",
    "Processing_Version",
    "Frames_Extracted",
    "Unique_Frames",
    "Status",
    "Processed_At",
    "Notes",
]


class VideoProcessingLog:
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

    def is_processed(self, video_path):
        video_hash = file_sha256(video_path)

        for row in self.load_rows():
            if (
                row.get("Video_Hash") == video_hash
                and row.get("Processing_Version") == PROCESSING_VERSION
                and row.get("Status") == "Complete"
            ):
                return True

        return False

    def record_complete(self, video_path, frames_extracted, unique_frames, notes=""):
        video_path = Path(video_path)
        video_hash = file_sha256(video_path)

        if self.is_processed(video_path):
            return

        with self.log_path.open("a", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=HEADERS)
            writer.writerow({
                "Video_Hash": video_hash,
                "Video_File": video_path.name,
                "Video_Path": str(video_path),
                "Processing_Version": PROCESSING_VERSION,
                "Frames_Extracted": frames_extracted,
                "Unique_Frames": unique_frames,
                "Status": "Complete",
                "Processed_At": datetime.now().isoformat(timespec="seconds"),
                "Notes": notes,
            })
