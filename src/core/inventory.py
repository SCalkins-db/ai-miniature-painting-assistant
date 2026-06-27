from pathlib import Path
import pandas as pd

from src.utils.normalization import canonicalize


class InventoryManager:
    def __init__(self, inventory_file="data/inventory.csv"):
        project_root = Path(__file__).resolve().parent.parent
        self.inventory_path = project_root / inventory_file

        self.columns = ["Paint_ID", "Owned", "Wishlist", "Qty"]
        self.inventory_df = self.load_inventory()

    def load_inventory(self):
        if self.inventory_path.exists():
            df = pd.read_csv(self.inventory_path)

            for column in self.columns:
                if column not in df.columns:
                    df[column] = False if column in ["Owned", "Wishlist"] else 0

            return df[self.columns]

        return pd.DataFrame(columns=self.columns)

    def save_inventory(self):
        self.inventory_path.parent.mkdir(parents=True, exist_ok=True)
        self.inventory_df.to_csv(self.inventory_path, index=False)

    def add_paint(self, paint_id, qty=1):
        paint_id = str(paint_id).strip()

        existing = self.inventory_df["Paint_ID"].astype(str).str.strip() == paint_id

        if existing.any():
            self.inventory_df.loc[existing, "Owned"] = True
            self.inventory_df.loc[existing, "Qty"] = qty
        else:
            new_row = {
                "Paint_ID": paint_id,
                "Owned": True,
                "Wishlist": False,
                "Qty": qty,
            }

            self.inventory_df = pd.concat(
                [self.inventory_df, pd.DataFrame([new_row])],
                ignore_index=True,
            )

        self.save_inventory()

    def update_quantity(self, paint_id, qty):
        paint_id = str(paint_id).strip()
        existing = self.inventory_df["Paint_ID"].astype(str).str.strip() == paint_id

        if existing.any():
            self.inventory_df.loc[existing, "Qty"] = qty
            self.inventory_df.loc[existing, "Owned"] = qty > 0

        self.save_inventory()

    def toggle_owned(self, paint_id):
        paint_id = str(paint_id).strip()
        existing = self.inventory_df["Paint_ID"].astype(str).str.strip() == paint_id

        if existing.any():
            current_value = bool(self.inventory_df.loc[existing, "Owned"].iloc[0])
            self.inventory_df.loc[existing, "Owned"] = not current_value
        else:
            new_row = {
                "Paint_ID": paint_id,
                "Owned": True,
                "Wishlist": False,
                "Qty": 1,
            }

            self.inventory_df = pd.concat(
                [self.inventory_df, pd.DataFrame([new_row])],
                ignore_index=True,
            )

        self.save_inventory()

    def toggle_wishlist(self, paint_id):
        paint_id = str(paint_id).strip()
        existing = self.inventory_df["Paint_ID"].astype(str).str.strip() == paint_id

        if existing.any():
            current_value = bool(self.inventory_df.loc[existing, "Wishlist"].iloc[0])
            self.inventory_df.loc[existing, "Wishlist"] = not current_value
        else:
            new_row = {
                "Paint_ID": paint_id,
                "Owned": False,
                "Wishlist": True,
                "Qty": 0,
            }

            self.inventory_df = pd.concat(
                [self.inventory_df, pd.DataFrame([new_row])],
                ignore_index=True,
            )

        self.save_inventory()

    def get_owned(self):
        return self.inventory_df[self.inventory_df["Owned"] == True]

    def get_wishlist(self):
        return self.inventory_df[self.inventory_df["Wishlist"] == True]

    def get_inventory_details(self, master_df):
        return self.inventory_df.merge(
            master_df,
            on="Paint_ID",
            how="left",
        )

    def get_display_type(self, product_line, paint_type):
        product_line = "" if pd.isna(product_line) else str(product_line).strip()
        paint_type = "" if pd.isna(paint_type) else str(paint_type).strip()

        if canonicalize(product_line) == canonicalize(paint_type):
            return paint_type

        if not product_line:
            return paint_type

        if not paint_type:
            return product_line

        return f"{product_line} | {paint_type}"

    def add_display_type_column(self, details_df):
        details_df = details_df.copy()

        details_df["Display_Type"] = details_df.apply(
            lambda row: self.get_display_type(
                row.get("Product_Line"),
                row.get("Paint_Type"),
            ),
            axis=1,
        )

        return details_df

    def get_display_columns(self):
        return [
            "Paint_Name",
            "Display_Type",
            "Company",
            "Brand",
            "Owned",
            "Wishlist",
            "Qty",
        ]

    def view_owned_details(self, master_df):
        details_df = self.get_inventory_details(master_df)
        details_df = self.add_display_type_column(details_df)

        return details_df[
            details_df["Owned"] == True
        ][self.get_display_columns()]

    def view_wishlist_details(self, master_df):
        details_df = self.get_inventory_details(master_df)
        details_df = self.add_display_type_column(details_df)

        return details_df[
            details_df["Wishlist"] == True
        ][self.get_display_columns()]

    def filter_inventory(self, master_df, column, value):
        allowed_columns = [
            "Company",
            "Brand",
            "Product_Line",
            "Paint_Type",
            "Paint_Name",
            "Owned",
            "Wishlist",
        ]

        if column not in allowed_columns:
            raise ValueError(f"Invalid filter column: {column}")

        details_df = self.get_inventory_details(master_df)
        details_df = self.add_display_type_column(details_df)

        if column in ["Owned", "Wishlist"]:
            filtered_df = details_df[details_df[column] == value]
        else:
            search_value = canonicalize(value)
            filtered_df = details_df[
                details_df[column]
                .fillna("")
                .astype(str)
                .apply(lambda cell: search_value in canonicalize(cell))
            ]

        return filtered_df[self.get_display_columns()]
