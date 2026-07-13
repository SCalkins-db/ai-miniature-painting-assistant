from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = PROJECT_ROOT / "src" / "scripts"


FILES = {
    SCRIPTS_DIR / "run_acquisition_pipeline.py": r'''from pathlib import Path
import pandas as pd

from src.acquisition.video_frame_extractor import VideoFrameExtractor
from src.acquisition.frame_deduplicator import FrameDeduplicator
from src.acquisition.batch_workflow_extractor import BatchWorkflowExtractor
from src.acquisition.workflow_importer import WorkflowImporter
from src.acquisition.video_processing_log import VideoProcessingLog


# ============================================================
# ACQUISITION PIPELINE RUNNER - V4
# ============================================================
#
# PURPOSE
# -------
# Runs the acquisition pipeline after media has already been
# collected into incoming/archive folders.
#
# WHAT THIS VERSION FIXES
# -----------------------
# V3 accidentally processed each *_unique frame folder and then
# processed the entire incoming/extracted_frames parent folder
# again.
#
# That caused thousands of duplicate OCR/workflow extraction passes.
#
# V4 only sends specific image source folders to the workflow
# extractor:
#
#   - *_unique frame folders
#   - archive/screenshots
#   - incoming/screenshots
#   - incoming/extracted
#
# It does NOT recursively process incoming/extracted_frames as a
# whole parent folder.
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

REPORT_PATH = PROJECT_ROOT / "exports" / "reports" / "acquisition_pipeline_report.csv"


def is_media_video(path):
    return path.suffix.lower() in [".mp4", ".mov", ".m4v"]


def collect_existing_unique_frame_folders():
    """
    Collects only existing *_unique folders.

    This lets the pipeline reuse previously extracted/deduplicated
    frames without reprocessing raw frame folders.
    """

    if not EXTRACTED_FRAMES_DIR.exists():
        return []

    folders = []

    for path in sorted(EXTRACTED_FRAMES_DIR.iterdir()):
        if path.is_dir() and path.name.endswith("_unique"):
            folders.append(path)

    return folders


def unique_folder_for_video_frames(frames):
    """
    The frame deduplicator creates a sibling folder ending in _unique.
    This helper returns that folder from a list of extracted frame paths.
    """

    if not frames:
        return None

    frame_dir = frames[0].parent
    return frame_dir.parent / f"{frame_dir.name}_unique"


def add_unique_source_once(source_list, folder):
    """
    Adds a folder to the source list only once.

    This prevents the same unique folder from being processed twice
    during the same run.
    """

    if folder is None:
        return

    folder = Path(folder)

    if not folder.exists():
        return

    if folder not in source_list:
        source_list.append(folder)


def main():
    print("=" * 60)
    print("ACQUISITION PIPELINE V4")
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
                add_unique_source_once(all_image_sources, unique_folder)

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
        add_unique_source_once(all_image_sources, folder)

    print(f"Unique frame folders queued: {len([p for p in all_image_sources if str(p).endswith('_unique')])}")

    print("\nCOLLECTING SCREENSHOT SOURCES")
    print("-" * 60)

    for folder in SCREENSHOT_DIRS:
        if folder.exists():
            add_unique_source_once(all_image_sources, folder)
            print(f"Queued screenshot source: {folder}")

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
    print("BUILDING ACQUISITION PIPELINE V4")
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