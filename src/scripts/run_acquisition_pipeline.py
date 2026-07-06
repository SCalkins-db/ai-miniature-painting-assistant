from pathlib import Path
import os
import shutil
import time
import pandas as pd

from src.acquisition.video_frame_extractor import VideoFrameExtractor
from src.acquisition.frame_deduplicator import FrameDeduplicator
from src.acquisition.batch_workflow_extractor import BatchWorkflowExtractor
from src.acquisition.workflow_importer import WorkflowImporter
from src.acquisition.video_processing_log import VideoProcessingLog
from src.acquisition.image_processing_log import ImageProcessingLog


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
VIDEO_SUFFIXES = {".mp4", ".mov", ".m4v"}


# ============================================================
# DASHBOARD HELPERS
# ============================================================

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def fmt_time(seconds):
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def progress_bar(current, total, width=40):
    if total <= 0:
        total = 1

    percent = current / total
    filled = int(width * percent)
    return "█" * filled + "░" * (width - filled), percent * 100


def render_dashboard(
    stage_status,
    current_stage="",
    current_file="",
    processed=0,
    total=0,
    rows_extracted=0,
    needs_review=0,
    start_time=None,
):
    if start_time is None:
        start_time = time.perf_counter()

    clear_screen()

    print("=" * 60)
    print("ACQUISITION PIPELINE V5")
    print("=" * 60)
    print()

    for stage_name, status in stage_status.items():
        if status == "PASS":
            print(f"{stage_name:<28} ✓ PASS")
        elif status == "COMPLETE":
            print(f"{stage_name:<28} ✓ COMPLETE")
        elif status == "RUNNING":
            bar, pct = progress_bar(processed, total)
            print(f"{stage_name:<28} {bar} {pct:5.1f}%")
        elif status == "FAILED":
            print(f"{stage_name:<28} ✗ FAILED")
        else:
            print(f"{stage_name:<28} Waiting...")

    if current_stage:
        print()
        print("-" * 60)
        print(f"Current Stage: {current_stage}")

    if current_file:
        print(f"Current File : {Path(current_file).name}")

    if total:
        print(f"Processed    : {processed} / {total}")

    if rows_extracted:
        print(f"Rows Extracted: {rows_extracted}")

    if needs_review:
        print(f"Needs Review : {needs_review}")

    print()
    print("-" * 60)
    print(f"Elapsed: {fmt_time(time.perf_counter() - start_time)}")
    print("=" * 60)


# ============================================================
# FILE HELPERS
# ============================================================

def is_media_video(path):
    return path.suffix.lower() in VIDEO_SUFFIXES


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


# ============================================================
# MAIN PIPELINE
# ============================================================

def main():
    start_time = time.perf_counter()

    stage_status = {
        "Video Extraction": "WAITING",
        "Frame Deduplication": "WAITING",
        "Workflow Extraction": "WAITING",
        "SQLite Import": "WAITING",
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    STAGING_ROOT.mkdir(parents=True, exist_ok=True)

    frame_extractor = VideoFrameExtractor(seconds_between_frames=1.0)
    deduplicator = FrameDeduplicator()
    batch_extractor = BatchWorkflowExtractor()
    importer = WorkflowImporter()
    video_log = VideoProcessingLog()
    image_log = ImageProcessingLog()

    all_image_sources = []

    videos_seen = 0
    videos_skipped = 0
    videos_processed = 0
    frames_extracted_total = 0
    unique_frames_total = 0

    stage_status["Video Extraction"] = "RUNNING"
    render_dashboard(stage_status, "Video Extraction", start_time=start_time)

    all_videos = []

    for video_dir in VIDEO_DIRS:
        if not video_dir.exists():
            continue

        for video_path in sorted(video_dir.rglob("*")):
            if is_media_video(video_path):
                all_videos.append(video_path)

    total_videos = len(all_videos)

    for idx, video_path in enumerate(all_videos, start=1):
        videos_seen += 1

        render_dashboard(
            stage_status,
            current_stage="Video Extraction",
            current_file=video_path,
            processed=idx,
            total=total_videos,
            start_time=start_time,
        )

        if video_log.is_processed(video_path):
            videos_skipped += 1
            continue

        frames = frame_extractor.extract_frames(video_path)
        frames_extracted_total += len(frames)

        unique_frames = []

        if frames:
            stage_status["Frame Deduplication"] = "RUNNING"

            render_dashboard(
                stage_status,
                current_stage="Frame Deduplication",
                current_file=video_path,
                processed=idx,
                total=total_videos,
                start_time=start_time,
            )

            frame_dir = frames[0].parent
            unique_frames = deduplicator.deduplicate_folder(frame_dir)
            unique_frames_total += len(unique_frames)

            unique_folder = unique_folder_for_video_frames(frames)
            add_source_once(all_image_sources, unique_folder)

        video_log.record_complete(
            video_path=video_path,
            frames_extracted=len(frames),
            unique_frames=len(unique_frames),
            notes="Video frame extraction and deduplication completed.",
        )

        videos_processed += 1

    stage_status["Video Extraction"] = "COMPLETE"
    stage_status["Frame Deduplication"] = "COMPLETE"

    render_dashboard(stage_status, "Video Extraction Complete", start_time=start_time)

    for folder in collect_existing_unique_frame_folders():
        add_source_once(all_image_sources, folder)

    for folder in SCREENSHOT_DIRS:
        if folder.exists():
            add_source_once(all_image_sources, folder)

    reports = []

    total_staged_images = 0
    total_skipped_images = 0
    total_duplicate_images = 0
    total_rows_extracted = 0
    total_needs_review = 0

    stage_status["Workflow Extraction"] = "RUNNING"

    total_sources = len(all_image_sources)

    for source_index, source_dir in enumerate(all_image_sources, start=1):
        staging_dir, staged_records, skipped, duplicates = stage_unprocessed_images(
            source_dir=source_dir,
            image_log=image_log,
        )

        total_skipped_images += skipped
        total_duplicate_images += duplicates

        if staging_dir is None:
            continue

        total_staged_images += len(staged_records)

        render_dashboard(
            stage_status,
            current_stage=f"Workflow Extraction Source {source_index}/{total_sources}",
            current_file=source_dir,
            processed=source_index,
            total=total_sources,
            rows_extracted=total_rows_extracted,
            needs_review=total_needs_review,
            start_time=start_time,
        )

        df = batch_extractor.extract_folder(staging_dir)

        if not df.empty:
            reports.append(df)
            total_rows_extracted += len(df)

            if "Resolver_Status" in df.columns:
                total_needs_review += len(df[df["Resolver_Status"] != "Resolved"])
            elif "Needs_Review" in df.columns:
                total_needs_review += len(df[df["Needs_Review"] == True])

        for record in staged_records:
            image_log.record_complete(
                image_path=record["original_path"],
                image_hash=record["image_hash"],
                source_group=record["source_group"],
                notes="Workflow extraction completed through staged pipeline.",
            )

    stage_status["Workflow Extraction"] = "COMPLETE"

    render_dashboard(stage_status, "Workflow Extraction Complete", start_time=start_time)

    if reports:
        report_df = pd.concat(reports, ignore_index=True)
    else:
        report_df = pd.DataFrame()

    report_df.to_csv(REPORT_PATH, index=False)

    stage_status["SQLite Import"] = "RUNNING"

    render_dashboard(stage_status, "SQLite Import", start_time=start_time)

    import_results = importer.import_folder()

    imported_rows = 0
    failed_imports = 0

    for path, count, status in import_results:
        if str(status).upper() in {"PASS", "SUCCESS", "IMPORTED"}:
            imported_rows += count
        elif str(status).upper() == "FAILED":
            failed_imports += 1

    stage_status["SQLite Import"] = "COMPLETE" if failed_imports == 0 else "FAILED"

    clear_screen()

    elapsed = time.perf_counter() - start_time

    print("=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)
    print()

    print("Videos")
    print("-" * 40)
    print(f"Seen:                 {videos_seen}")
    print(f"Skipped:              {videos_skipped}")
    print(f"Processed:            {videos_processed}")
    print()

    print("Frames")
    print("-" * 40)
    print(f"Extracted:            {frames_extracted_total}")
    print(f"Unique:               {unique_frames_total}")
    print()

    print("Workflow Extraction")
    print("-" * 40)
    print(f"Sources Queued:        {len(all_image_sources)}")
    print(f"Images Staged:         {total_staged_images}")
    print(f"Already Processed:     {total_skipped_images}")
    print(f"Duplicates Skipped:    {total_duplicate_images}")
    print(f"Workflow Rows:         {total_rows_extracted}")
    print(f"Needs Review:          {total_needs_review}")
    print(f"Report:                {REPORT_PATH}")
    print()

    print("SQLite")
    print("-" * 40)
    print(f"Imported Rows:         {imported_rows}")
    print(f"Failed Imports:        {failed_imports}")
    print()

    print("Elapsed Time")
    print("-" * 40)
    print(fmt_time(elapsed))
    print()

    print("=" * 60)

    if failed_imports == 0:
        print("SUCCESS")
    else:
        print("FAILED")

    print("=" * 60)


if __name__ == "__main__":
    main()