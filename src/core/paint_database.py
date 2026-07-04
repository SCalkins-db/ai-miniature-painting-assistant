# Allow direct execution from project root or with python -m
import sys
from pathlib import Path

_project_root = Path(__file__).resolve()
while _project_root.parent != _project_root:
    if (_project_root / "src").exists() and (_project_root / "data").exists():
        break
    _project_root = _project_root.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.core.registry_loader import load_registries
from src.utils.normalization import canonicalize


class PaintDatabase:
    def __init__(self, registry_folder="data/registries_csv"):
        self.master_df = load_registries(registry_folder)

    def get_all_paints(self):
        return self.master_df

    def _contains_normalized(self, column, value):
        search_value = canonicalize(value)

        return self.master_df[
            self.master_df[column]
            .fillna("")
            .astype(str)
            .apply(lambda cell: search_value in canonicalize(cell))
        ]

    def search_by_paint_name(self, paint_name):
        return self._contains_normalized("Paint_Name", paint_name)

    def search_by_company(self, company):
        return self._contains_normalized("Company", company)

    def search_by_brand(self, brand):
        return self._contains_normalized("Brand", brand)

    def search_by_product_line(self, product_line):
        return self._contains_normalized("Product_Line", product_line)

    def search_by_paint_type(self, paint_type):
        return self._contains_normalized("Paint_Type", paint_type)

    def search_by_status(self, status):
        return self._contains_normalized("Status", status)

    def search_all(self, value):
        search_value = canonicalize(value)

        return self.master_df[
            self.master_df["Canonical_Search_Key"]
            .fillna("")
            .astype(str)
            .apply(lambda cell: search_value in canonicalize(cell))
        ]

    def get_total_paints(self):
        return len(self.master_df)

    def get_company_counts(self):
        return self.master_df["Company"].value_counts()

    def get_missing_hex(self):
        return self.master_df[
            self.master_df["Hex"].isna()
            | (self.master_df["Hex"].astype(str).str.strip() == "")
            | (self.master_df["Hex"].astype(str).str.lower().isin(["nan", "none", "null"]))
        ]

    def get_missing_rgb(self):
        return self.master_df[
            self.master_df["RGB"].isna()
            | (self.master_df["RGB"].astype(str).str.strip() == "")
            | (self.master_df["RGB"].astype(str).str.lower().isin(["nan", "none", "null"]))
        ]

    def get_missing_color_data(self):
        return self.master_df[
            self.master_df.index.isin(self.get_missing_hex().index)
            | self.master_df.index.isin(self.get_missing_rgb().index)
        ]

    def get_missing_hex_count(self):
        return len(self.get_missing_hex())

    def get_missing_rgb_count(self):
        return len(self.get_missing_rgb())

    def get_missing_color_data_count(self):
        return len(self.get_missing_color_data())
