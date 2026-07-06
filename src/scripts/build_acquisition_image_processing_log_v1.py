from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ACQ_DIR = PROJECT_ROOT / "src" / "acquisition"
SCRIPTS_DIR = PROJECT_ROOT / "src" / "scripts"


FILES = {
    ACQ_DIR / "image_processing_log.py": r'''from pathlib import Path
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
''',

    SCRIPTS_DIR / "run_acquisition_pipeline.py": r'''from pathlib import Path
import os
import shutil
import pandas as pd

from src.acquisition.video_frame_extractor import VideoFrameExtractor
from src.acquisition.frame_deduplicator import FrameDeduplicator
from src.acquisition.batch_workflow_extractor import BatchWorkflowExtractor
from src.acquisition.workflow_importer import WorkflowImporter
from src.acquisition.video_processing_log import VideoProcessingLog
from src.acquisition.image_processing_log import ImageProcessingLog


# ============================================================
# ACQUISITION PIPELINE RUNNER - V5
# ============================================================
#
# PURPOSE
# -------
# Runs the acquisition pipeline.
#
# V5 FIXES
# --------
# 1. Does NOT process incoming/extracted_frames as one giant parent.
# 2. Only processes *_unique frame folders.
# 3. Uses image_processing_log.csv to skip screenshots/frames that
#    already completed workflow extraction.
# 4. Stages only NEW unprocessed images into a temporary folder.
#
# CLEANUP SAFETY
# --------------
# This version does not delete source media.
# It only recreates temporary staging folders under:
#
#     data/imports/staging/workflow_extraction/
#
# ============================================================


PROJECT_ROOT = Path(__file__).resolve().parents[2]

VIDEO_DIRS = [
    PROJECT_ROOT / "archive" / "videos",
    PROJECT_ROOT / "incoming" / "videos",
]

SCREENSHOT_DIRS = [
    PROJECT_ROOT / "archive" / "screenshots",
    PROJECT_ROOT / "incoming" / "screenshots",
    PROJECT_ROOT / "incoming" / "extracted",
]

EXTRACTED_FRAMES_DIR = PROJECT_ROOT / "incoming" / "extracted_frames"

STAGING_ROOT = PROJECT_ROOT / "data" / "imports" / "staging" / "workflow_extraction"

REPORT_PATH = PROJECT_ROOT / "exports" / "reports" / "acquisition_pipeline_report.csv"

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


def is_media_video(path):
    return path.suffix.lower() in [".mp4", ".mov", ".m4v"]


def safe_folder_name(path):
    text = str(path).replace(str(PROJECT_ROOT), "")
    text = text.replace("\\", "_").replace("/", "_").replace(":", "")
    text = text.strip("_")
    return text or "source"


def image_files_in(folder):
    if not folder.exists():
        return []

    return [
        path for path in sorted(folder.rglob("*"))
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    ]


def collect_existing_unique_frame_folders():
    if not EXTRACTED_FRAMES_DIR.exists():
        return []

    return [
        path for path in sorted(EXTRACTED_FRAMES_DIR.iterdir())
        if path.is_dir() and path.name.endswith("_unique")
    ]


def unique_folder_for_video_frames(frames):
    if not frames:
        return None

    frame_dir = frames[0].parent
    return frame_dir.parent / f"{frame_dir.name}_unique"


def add_source_once(source_list, folder):
    if folder is None:
        return

    folder = Path(folder)

    if not folder.exists():
        return

    if folder not in source_list:
        source_list.append(folder)


def hardlink_or_copy(source, destination):
    try:
        os.link(source, destination)
    except Exception:
        shutil.copy2(source, destination)


def stage_unprocessed_images(source_dir, image_log):
    source_dir = Path(source_dir)

    all_images = image_files_in(source_dir)

    if not all_images:
        return None, [], 0, 0

    completed = image_log.completed_hashes()
    seen_this_stage = set()

    staging_dir = STAGING_ROOT / safe_folder_name(source_dir)

    if staging_dir.exists():
        shutil.rmtree(staging_dir)

    staging_dir.mkdir(parents=True, exist_ok=True)

    staged_records = []
    skipped = 0
    duplicates_this_run = 0

    for image_path in all_images:
        image_hash = image_log.hash_image(image_path)

        if image_hash in completed:
            skipped += 1
            continue

        if image_hash in seen_this_stage:
            duplicates_this_run += 1
            continue

        seen_this_stage.add(image_hash)

        staged_name = f"{len(staged_records):06d}_{image_path.name}"
        staged_path = staging_dir / staged_name

        hardlink_or_copy(image_path, staged_path)

        staged_records.append({
            "original_path": image_path,
            "staged_path": staged_path,
            "image_hash": image_hash,
            "source_group": str(source_dir),
        })

    if not staged_records:
        shutil.rmtree(staging_dir, ignore_errors=True)
        return None, [], skipped, duplicates_this_run

    return staging_dir, staged_records, skipped, duplicates_this_run


def main():
    print("=" * 60)
    print("ACQUISITION PIPELINE V5")
    print("=" * 60)

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    STAGING_ROOT.mkdir(parents=True, exist_ok=True)

    frame_extractor = VideoFrameExtractor(seconds_between_frames=1.0)
    deduplicator = FrameDeduplicator()
    batch_extractor = BatchWorkflowExtractor()
    importer = WorkflowImporter()
    video_log = VideoProcessingLog()
    image_log = ImageProcessingLog()

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
            if not is_media_video(video_path):
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

                unique_folder = unique_folder_for_video_frames(frames)
                add_source_once(all_image_sources, unique_folder)

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

    print("\nCOLLECTING EXISTING UNIQUE FRAME FOLDERS")
    print("-" * 60)

    for folder in collect_existing_unique_frame_folders():
        add_source_once(all_image_sources, folder)

    unique_count = len([p for p in all_image_sources if p.name.endswith("_unique")])
    print(f"Unique frame folders queued: {unique_count}")

    print("\nCOLLECTING SCREENSHOT SOURCES")
    print("-" * 60)

    for folder in SCREENSHOT_DIRS:
        if folder.exists():
            add_source_once(all_image_sources, folder)
            print(f"Queued screenshot source: {folder}")

    print("\nBATCH WORKFLOW EXTRACTION")
    print("-" * 60)

    reports = []

    total_sources = len(all_image_sources)
    total_staged_images = 0
    total_skipped_images = 0
    total_duplicate_images = 0

    for source_index, source_dir in enumerate(all_image_sources, start=1):
        print(f"\nSOURCE {source_index}/{total_sources}")
        print(f"Source: {source_dir}")

        staging_dir, staged_records, skipped, duplicates = stage_unprocessed_images(
            source_dir=source_dir,
            image_log=image_log,
        )

        total_skipped_images += skipped
        total_duplicate_images += duplicates

        if staging_dir is None:
            print(f"Nothing new to process.")
            print(f"Skipped already processed: {skipped}")
            print(f"Duplicates this run:       {duplicates}")
            continue

        print(f"Images staged:             {len(staged_records)}")
        print(f"Skipped already processed: {skipped}")
        print(f"Duplicates this run:       {duplicates}")
        print(f"Staging folder:            {staging_dir}")

        df = batch_extractor.extract_folder(staging_dir)

        print(f"Images processed:          {len(df)}")

        total_staged_images += len(staged_records)

        for record in staged_records:
            image_log.record_complete(
                image_path=record["original_path"],
                image_hash=record["image_hash"],
                source_group=record["source_group"],
                notes="Workflow extraction completed through staged pipeline.",
            )

        if not df.empty:
            reports.append(df)

    print("\nIMAGE PROCESSING SUMMARY")
    print("-" * 60)
    print(f"New images staged:         {total_staged_images}")
    print(f"Skipped already processed: {total_skipped_images}")
    print(f"Duplicate images skipped:  {total_duplicate_images}")

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
    print("BUILDING ACQUISITION IMAGE PROCESSING LOG")
    print("=" * 60)

    for path, content in FILES.items():
        write_file(path, content)

    print("=" * 60)
    print("DONE")
    print("=" * 60)
    print("Run:")
    print("python -m src.scripts.run_acquisition_pipeline")


if __name__ == "__main__":
    main()