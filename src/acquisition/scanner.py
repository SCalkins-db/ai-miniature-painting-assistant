from pathlib import Path


SUPPORTED_VIDEO = {".mp4", ".mov", ".m4v"}
SUPPORTED_IMAGE = {".png", ".jpg", ".jpeg", ".webp"}


class MediaScanner:
    def __init__(self, incoming_dir="incoming"):
        self.incoming_dir = Path(incoming_dir)

    def scan(self):
        files = []

        if not self.incoming_dir.exists():
            return files

        for path in self.incoming_dir.rglob("*"):
            if not path.is_file():
                continue

            suffix = path.suffix.lower()

            if suffix in SUPPORTED_VIDEO:
                file_type = "video"
            elif suffix in SUPPORTED_IMAGE:
                file_type = "image"
            else:
                continue

            files.append({
                "path": path,
                "file_name": path.name,
                "file_type": file_type,
            })

        return files
