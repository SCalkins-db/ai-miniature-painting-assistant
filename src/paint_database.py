from src.registry_loader import load_registries


class PaintDatabase:
    def __init__(self, registry_folder="data/registries_csv"):
        self.master_df = load_registries(registry_folder)

    def get_all_paints(self):
        return self.master_df

    def search_by_paint_name(self, paint_name):
        return self.master_df[
            self.master_df["Paint_Name"].str.contains(paint_name, case=False, na=False)
        ]

    def search_by_company(self, company):
        return self.master_df[
            self.master_df["Company"].str.contains(company, case=False, na=False)
        ]

    def search_by_brand(self, brand):
        return self.master_df[
            self.master_df["Brand"].str.contains(brand, case=False, na=False)
        ]

    def search_by_product_line(self, product_line):
        return self.master_df[
            self.master_df["Product_Line"].str.contains(product_line, case=False, na=False)
        ]

    def search_by_paint_type(self, paint_type):
        return self.master_df[
            self.master_df["Paint_Type"].str.contains(paint_type, case=False, na=False)
        ]

    def search_by_status(self, status):
        return self.master_df[
            self.master_df["Status"].str.contains(status, case=False, na=False)
        ]

    def get_total_paints(self):
        return len(self.master_df)

    def get_company_counts(self):
        return self.master_df["Company"].value_counts()

    def get_missing_hex(self):
        return self.master_df[
            self.master_df["Hex"].isna() |
            (self.master_df["Hex"].astype(str).str.strip() == "")
            ]

    def get_missing_hex_count(self):
        return len(
            self.master_df[
                self.master_df["Hex"].isna() |
                (self.master_df["Hex"].astype(str).str.strip() == "")
                ]
        )