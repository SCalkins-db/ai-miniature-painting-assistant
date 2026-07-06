from pathlib import Path
import shutil


class FileRouter:
    def __init__(self):
        self.archive_video_dir = Path("archive/videos")
        self.archive_image_dir = Path("archive/screenshots")
        self.archive_zip_dir = Path("archive/zips")
        self.failed_dir = Path("failed")

        for folder in [
            self.archive_video_dir,
            self.archive_image_dir,
            self.archive_zip_dir,
            self.failed_dir,
        ]:
            folder.mkdir(parents=True, exist_ok=True)

    def archive_media(self, file_path, file_type):
        file_path = Path(file_path)

        if not file_path.exists():
            return None

        if file_type == "video":
            target_dir = self.archive_video_dir
        elif file_type == "image":
            target_dir = self.archive_image_dir
        else:
            target_dir = self.failed_dir

        target_path = target_dir / file_path.name

        if target_path.exists():
            target_path = self._dedupe_target(target_path)

        shutil.copy2(file_path, target_path)
        return target_path

    def archive_zip(self, zip_path):
        zip_path = Path(zip_path)

        if not zip_path.exists():
            return None

        target_path = self.archive_zip_dir / zip_path.name

        if target_path.exists():
            target_path = self._dedupe_target(target_path)

        shutil.copy2(zip_path, target_path)
        return target_path

    def _dedupe_target(self, target_path):
        stem = target_path.stem
        suffix = target_path.suffix
        parent = target_path.parent

        counter = 1

        while True:
            candidate = parent / f"{stem}_{counter}{suffix}"

            if not candidate.exists():
                return candidate

            counter += 1
