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