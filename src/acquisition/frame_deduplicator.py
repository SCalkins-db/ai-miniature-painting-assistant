from pathlib import Path
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
