import difflib
import pandas as pd

from src.gui.database.database_paths import PROJECT_ROOT


REGISTRY_CSV_DIR = PROJECT_ROOT / "data" / "registries_csv"


class PaintNormalizer:
    def __init__(self):
        self.paint_lookup = self._load_paints()

    def _load_paints(self):
        paints = []

        if not REGISTRY_CSV_DIR.exists():
            return paints

        for csv_path in REGISTRY_CSV_DIR.glob("*.csv"):
            df = pd.read_csv(csv_path).fillna("")

            for _, row in df.iterrows():
                paint_name = row.get("Paint_Name", "")
                paint_id = row.get("Paint_ID", "")

                if not paint_name or not paint_id:
                    continue

                paints.append({
                    "paint_id": paint_id,
                    "paint_name": paint_name,
                    "company": row.get("Company", ""),
                    "product_line": row.get("Product_Line", ""),
                    "paint_type": row.get("Paint_Type", ""),
                })

        return paints

    def find_best_match(self, raw_name, cutoff=0.82):
        if not raw_name:
            return None

        names = [paint["paint_name"] for paint in self.paint_lookup]
        matches = difflib.get_close_matches(raw_name, names, n=1, cutoff=cutoff)

        if not matches:
            return None

        matched_name = matches[0]

        for paint in self.paint_lookup:
            if paint["paint_name"] == matched_name:
                return {
                    "raw_name": raw_name,
                    "paint_id": paint["paint_id"],
                    "paint_name": paint["paint_name"],
                    "company": paint["company"],
                    "product_line": paint["product_line"],
                    "paint_type": paint["paint_type"],
                    "confidence": "fuzzy",
                }

        return None
