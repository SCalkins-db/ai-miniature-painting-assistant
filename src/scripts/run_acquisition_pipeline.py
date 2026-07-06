from pathlib import Path
import pandas as pd

from src.acquisition.video_frame_extractor import VideoFrameExtractor
from src.acquisition.frame_deduplicator import FrameDeduplicator
from src.acquisition.batch_workflow_extractor import BatchWorkflowExtractor
from src.acquisition.workflow_importer import WorkflowImporter


PROJECT_ROOT = Path(__file__).resolve().parents[2]

VIDEO_DIRS = [
    PROJECT_ROOT / "archive" / "videos",
    PROJECT_ROOT / "incoming" / "videos",
]

IMAGE_DIRS = [
    PROJECT_ROOT / "archive" / "screenshots",
    PROJECT_ROOT / "incoming" / "screenshots",
    PROJECT_ROOT / "incoming" / "extracted",
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

    all_image_sources = []

    print("\nVIDEO FRAME EXTRACTION")
    print("-" * 60)

    for video_dir in VIDEO_DIRS:
        if not video_dir.exists():
            continue

        for video_path in sorted(video_dir.rglob("*")):
            if video_path.suffix.lower() not in [".mp4", ".mov", ".m4v"]:
                continue

            print(f"Extracting frames: {video_path}")
            frames = frame_extractor.extract_frames(video_path)
            print(f"Frames saved: {len(frames)}")

            if frames:
                frame_dir = frames[0].parent
                unique_frames = deduplicator.deduplicate_folder(frame_dir)
                print(f"Unique frames kept: {len(unique_frames)}")
                all_image_sources.append(frame_dir.parent / f"{frame_dir.name}_unique")

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
