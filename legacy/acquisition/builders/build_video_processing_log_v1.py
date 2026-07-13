from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ACQ_DIR = PROJECT_ROOT / "src" / "acquisition"
SCRIPTS_DIR = PROJECT_ROOT / "src" / "scripts"


FILES = {
    ACQ_DIR / "video_processing_log.py": r'''from pathlib import Path
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
''',

    SCRIPTS_DIR / "run_acquisition_pipeline.py": r'''from pathlib import Path
import pandas as pd

from src.acquisition.video_frame_extractor import VideoFrameExtractor
from src.acquisition.frame_deduplicator import FrameDeduplicator
from src.acquisition.batch_workflow_extractor import BatchWorkflowExtractor
from src.acquisition.workflow_importer import WorkflowImporter
from src.acquisition.video_processing_log import VideoProcessingLog


# ============================================================
# ACQUISITION PIPELINE RUNNER
# ============================================================
#
# PURPOSE
# -------
# Runs the acquisition pipeline after media has already been
# collected into incoming/archive folders.
#
# IMPORTANT
# ---------
# This script performs real work:
#
#   - Extracts video frames
#   - Deduplicates frames
#   - Runs batch workflow extraction
#   - Writes acquisition reports
#   - Imports generated workflow CSVs into SQLite
#
# WHY VIDEO LOGGING EXISTS
# ------------------------
# Videos are expensive to process. Before extracting frames, this
# script checks video_processing_log.csv. If a video hash is already
# marked Complete for the current processing version, the video is
# skipped.
#
# ============================================================


PROJECT_ROOT = Path(__file__).resolve().parents[2]

VIDEO_DIRS = [
    PROJECT_ROOT / "archive" / "videos",
    PROJECT_ROOT / "incoming" / "videos",
]

IMAGE_DIRS = [
    PROJECT_ROOT / "archive" / "screenshots",
    PROJECT_ROOT / "incoming" / "screenshots",
    PROJECT_ROOT / "incoming" / "extracted",
    PROJECT_ROOT / "incoming" / "extracted_frames",
]

REPORT_PATH = PROJECT_ROOT / "exports" / "reports" / "acquisition_pipeline_report.csv"


def main():
    print("=" * 60)
    print("ACQUISITION PIPELINE V3")
    print("=" * 60)

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    frame_extractor = VideoFrameExtractor(seconds_between_frames=1.0)
    deduplicator = FrameDeduplicator()
    batch_extractor = BatchWorkflowExtractor()
    importer = WorkflowImporter()
    video_log = VideoProcessingLog()

    all_image_sources = []

    print("\nVIDEO FRAME EXTRACTION")
    print("-" * 60)

    videos_seen = 0
    videos_skipped = 0
    videos_processed = 0

    for video_dir in VIDEO_DIRS:
        if not video_dir.exists():
            continue

        for video_path in sorted(video_dir.rglob("*")):
            if video_path.suffix.lower() not in [".mp4", ".mov", ".m4v"]:
                continue

            videos_seen += 1

            if video_log.is_processed(video_path):
                videos_skipped += 1
                print(f"SKIP already processed: {video_path}")
                continue

            print(f"Extracting frames: {video_path}")

            frames = frame_extractor.extract_frames(video_path)
            print(f"Frames saved: {len(frames)}")

            unique_frames = []

            if frames:
                frame_dir = frames[0].parent
                unique_frames = deduplicator.deduplicate_folder(frame_dir)
                print(f"Unique frames kept: {len(unique_frames)}")
                all_image_sources.append(frame_dir.parent / f"{frame_dir.name}_unique")

            video_log.record_complete(
                video_path=video_path,
                frames_extracted=len(frames),
                unique_frames=len(unique_frames),
                notes="Video frame extraction and deduplication completed.",
            )

            videos_processed += 1

    print("\nVIDEO SUMMARY")
    print("-" * 60)
    print(f"Videos seen:      {videos_seen}")
    print(f"Videos processed: {videos_processed}")
    print(f"Videos skipped:   {videos_skipped}")

    for image_dir in IMAGE_DIRS:
        if image_dir.exists():
            all_image_sources.append(image_dir)

    print("\nBATCH WORKFLOW EXTRACTION")
    print("-" * 60)

    reports = []

    for source_dir in all_image_sources:
        print(f"Extracting workflows from: {source_dir}")

        df = batch_extractor.extract_folder(source_dir)
        print(f"Images processed: {len(df)}")

        if not df.empty:
            reports.append(df)

    if reports:
        report_df = pd.concat(reports, ignore_index=True)
    else:
        report_df = pd.DataFrame()

    report_df.to_csv(REPORT_PATH, index=False)
    print(f"\nReport written: {REPORT_PATH}")

    print("\nSQLITE WORKFLOW IMPORT")
    print("-" * 60)

    import_results = importer.import_folder()

    for path, count, status in import_results:
        print(f"{status}: {count} rows <- {path}")

    print("=" * 60)
    print("ACQUISITION PIPELINE COMPLETE")
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
    print("BUILDING VIDEO PROCESSING LOG V1")
    print("=" * 60)

    for path, content in FILES.items():
        write_file(path, content)

    print("=" * 60)
    print("DONE")
    print("=" * 60)
    print("Run:")
    print("python -m src.scripts.run_full_pipeline")


if __name__ == "__main__":
    main()