from pathlib import Path
import zipfile


class ZipHandler:
    def __init__(self, zip_dir="incoming/zips", extract_dir="incoming/extracted"):
        self.zip_dir = Path(zip_dir)
        self.extract_dir = Path(extract_dir)

    def find_zips(self):
        if not self.zip_dir.exists():
            return []

        return sorted(self.zip_dir.glob("*.zip"))

    def extract_zip(self, zip_path):
        zip_path = Path(zip_path)
        target_dir = self.extract_dir / zip_path.stem
        target_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(target_dir)

        return target_dir

    def extract_all(self):
        extracted = []

        for zip_path in self.find_zips():
            target_dir = self.extract_zip(zip_path)
            extracted.append({
                "zip_path": zip_path,
                "extract_dir": target_dir,
            })

        return extracted
