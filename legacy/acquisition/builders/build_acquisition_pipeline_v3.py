from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ACQ_DIR = PROJECT_ROOT / "src" / "acquisition"
SCRIPTS_DIR = PROJECT_ROOT / "src" / "scripts"
DEBUG_DIR = PROJECT_ROOT / "src" / "debug"

FOLDERS = [
    PROJECT_ROOT / "incoming" / "extracted_frames",
    PROJECT_ROOT / "data" / "workflows" / "imported",
]

FILES = {
    ACQ_DIR / "video_frame_extractor.py": r'''from pathlib import Path


class VideoFrameExtractor:
    def __init__(self, output_dir="incoming/extracted_frames", seconds_between_frames=1.0):
        self.output_dir = Path(output_dir)
        self.seconds_between_frames = seconds_between_frames
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def extract_frames(self, video_path):
        try:
            import cv2
        except ImportError as error:
            raise ImportError("Install OpenCV with: pip install opencv-python") from error

        video_path = Path(video_path)

        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")

        capture = cv2.VideoCapture(str(video_path))

        fps = capture.get(cv2.CAP_PROP_FPS) or 30
        frame_interval = max(int(fps * self.seconds_between_frames), 1)

        video_output_dir = self.output_dir / video_path.stem
        video_output_dir.mkdir(parents=True, exist_ok=True)

        saved = []
        frame_index = 0
        saved_index = 0

        while True:
            success, frame = capture.read()

            if not success:
                break

            if frame_index % frame_interval == 0:
                output_path = video_output_dir / f"frame_{saved_index:05d}.png"
                cv2.imwrite(str(output_path), frame)
                saved.append(output_path)
                saved_index += 1

            frame_index += 1

        capture.release()
        return saved
''',

    ACQ_DIR / "frame_deduplicator.py": r'''from pathlib import Path
import shutil


class FrameDeduplicator:
    def __init__(self, output_suffix="_unique", threshold=6.0):
        self.output_suffix = output_suffix
        self.threshold = threshold

    def deduplicate_folder(self, frame_dir):
        try:
            import cv2
        except ImportError as error:
            raise ImportError("Install OpenCV with: pip install opencv-python") from error

        frame_dir = Path(frame_dir)
        output_dir = frame_dir.parent / f"{frame_dir.name}{self.output_suffix}"
        output_dir.mkdir(parents=True, exist_ok=True)

        frames = sorted(frame_dir.glob("*.png"))
        kept = []
        previous_gray = None

        for frame_path in frames:
            image = cv2.imread(str(frame_path))

            if image is None:
                continue

            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            keep = False

            if previous_gray is None:
                keep = True
            else:
                diff = cv2.absdiff(previous_gray, gray)
                score = diff.mean()

                if score >= self.threshold:
                    keep = True

            if keep:
                target = output_dir / frame_path.name
                shutil.copy2(frame_path, target)
                kept.append(target)
                previous_gray = gray

        return kept
''',

    ACQ_DIR / "batch_workflow_extractor.py": r'''from pathlib import Path
import pandas as pd

from src.acquisition.workflow_extractor import WorkflowExtractor
from src.acquisition.workflow_csv_writer import WorkflowCSVWriter
from src.acquisition.workflow_resolver import WorkflowResolver


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


class BatchWorkflowExtractor:
    def __init__(self):
        self.extractor = WorkflowExtractor()
        self.writer = WorkflowCSVWriter()
        self.resolver = WorkflowResolver()

    def extract_folder(self, source_dir):
        source_dir = Path(source_dir)

        images = [
            path for path in source_dir.rglob("*")
            if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
        ]

        results = []

        for image_path in sorted(images):
            try:
                temp = self.extractor.extract_from_image(
                    image_path=image_path,
                    workflow_id="UNRESOLVED_WORKFLOW",
                )

                resolved = self.resolver.resolve(
                    raw_title=temp["title"],
                    source_path=str(image_path),
                )

                workflow_id = resolved["workflow_id"] or f"UNRESOLVED_{image_path.stem.upper()}"
                temp["workflow_df"]["Workflow_ID"] = workflow_id
                temp["workflow_df"]["Unit"] = resolved["resolved_title"] or temp["title"]

                output_path = self.writer.write(
                    temp["workflow_df"],
                    workflow_id=workflow_id,
                    title=temp["title"],
                )

                results.append({
                    "source_file": str(image_path),
                    "raw_title": temp["title"],
                    "workflow_id": workflow_id,
                    "resolved_title": resolved["resolved_title"],
                    "resolver_status": resolved["status"],
                    "score": resolved["score"],
                    "rows": len(temp["workflow_df"]),
                    "output_path": str(output_path),
                })

            except Exception as error:
                results.append({
                    "source_file": str(image_path),
                    "raw_title": "",
                    "workflow_id": "",
                    "resolved_title": "",
                    "resolver_status": "Failed",
                    "score": 0,
                    "rows": 0,
                    "output_path": "",
                    "error": str(error),
                })

        return pd.DataFrame(results)
''',

    ACQ_DIR / "workflow_importer.py": r'''from pathlib import Path
import pandas as pd

from src.database.database_manager import DatabaseManager


class WorkflowImporter:
    def __init__(self):
        self.manager = DatabaseManager()
        self.manager.initialize()

    def import_workflow_csv(self, workflow_csv_path):
        workflow_csv_path = Path(workflow_csv_path)

        if not workflow_csv_path.exists():
            raise FileNotFoundError(f"Workflow CSV not found: {workflow_csv_path}")

        df = pd.read_csv(workflow_csv_path).fillna("")

        if df.empty:
            return 0

        rows = []

        for _, row in df.iterrows():
            rows.append((
                row.get("Workflow_ID", ""),
                int(row.get("Area_Order", 0) or 0),
                int(row.get("Step_Order", 0) or 0),
                row.get("Model_Area", ""),
                row.get("Technique", ""),
                row.get("Paint_ID", ""),
                row.get("Paint_Name", ""),
                "",
                row.get("Purpose", ""),
                1 if str(row.get("Optional", "")).lower() in ["yes", "true", "1"] else 0,
                row.get("Notes", ""),
            ))

        with self.manager.connect() as conn:
            conn.executemany(
                """
                INSERT INTO workflow_steps (
                    workflow_id,
                    area_order,
                    step_order,
                    model_area,
                    technique,
                    paint_id,
                    paint_name,
                    paint_type,
                    purpose,
                    optional,
                    notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            conn.commit()

        return len(rows)

    def import_folder(self, workflow_dir="data/workflows/imported"):
        workflow_dir = Path(workflow_dir)
        results = []

        for csv_path in sorted(workflow_dir.glob("*.csv")):
            try:
                count = self.import_workflow_csv(csv_path)
                results.append((str(csv_path), count, "Imported"))
            except Exception as error:
                results.append((str(csv_path), 0, f"Failed: {error}"))

        return results
''',

    SCRIPTS_DIR / "run_acquisition_pipeline.py": r'''from pathlib import Path
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
''',

    DEBUG_DIR / "acquisition_pipeline_test.py": r'''from src.acquisition.batch_workflow_extractor import BatchWorkflowExtractor


def main():
    print("=" * 60)
    print("ACQUISITION PIPELINE TEST")
    print("=" * 60)

    extractor = BatchWorkflowExtractor()
    df = extractor.extract_folder("archive/screenshots")

    print(df.head(20).to_string(index=False))
    print(f"\nRows: {len(df)}")

    print("=" * 60)
    print("ACQUISITION PIPELINE TEST COMPLETE")
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
    print("BUILDING ACQUISITION PIPELINE V3")
    print("=" * 60)

    for folder in FOLDERS:
        folder.mkdir(parents=True, exist_ok=True)
        print(f"ENSURED DIR: {folder}")

    for path, content in FILES.items():
        write_file(path, content)

    print("=" * 60)
    print("DONE")
    print("=" * 60)
    print("Install OpenCV:")
    print("pip install opencv-python")
    print("")
    print("Run quick test:")
    print("python -m src.debug.acquisition_pipeline_test")
    print("")
    print("Run full pipeline:")
    print("python -m src.scripts.run_acquisition_pipeline")


if __name__ == "__main__":
    main()