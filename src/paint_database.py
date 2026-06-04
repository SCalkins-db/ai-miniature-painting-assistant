import pandas as pd

class PaintDatabase:
    """
    Handles loading and searching paint data.
    """

    def __init__(self, file_path):
        self.file_path = file_path
        self.paints = None

    def load_paints(self):
        """
        Loads paint data from CSV.
        """
        self.paints = pd.read_csv(self.file_path)
        return self.paints

    def get_all_paints(self):
        """
        Returns all paints.
        """
        if self.paints is None:
            self.load_paints()

        return self.paints

    def search_by_name(self, search_term):
        """
        Search paint names.
        """
        if self.paints is None:
            self.load_paints()

        return self.paints[
            self.paints["paint_name"]
            .str.contains(search_term, case=False, na=False)
        ]

    def search_by_brand(self, brand):
        """
        Search paints by brand.
        """
        if self.paints is None:
            self.load_paints()

        return self.paints[
            self.paints["brand"]
            .str.lower() == brand.lower()
        ]

    def search_by_color_family(self, color_family):
        """
        Search paints by color family.
        """
        if self.paints is None:
            self.load_paints()

        return self.paints[
            self.paints["color_family"]
            .str.lower() == color_family.lower()
            ]

    def search_by_paint_type(self, paint_type):
        """
        Search paints by paint type.
        """
        if self.paints is None:
            self.load_paints()

        return self.paints[
            self.paints["paint_type"]
            .str.lower() == paint_type.lower()
            ]