from pathlib import Path


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
