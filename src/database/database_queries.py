from src.database.database_manager import DatabaseManager


class DatabaseQueries:
    def __init__(self):
        self.manager = DatabaseManager()

    def count_paints(self):
        row = self.manager.fetch_one("SELECT COUNT(*) FROM paints")
        return row[0]

    def count_inventory(self):
        row = self.manager.fetch_one("SELECT COUNT(*) FROM inventory")
        return row[0]

    def count_workflows(self):
        row = self.manager.fetch_one("SELECT COUNT(*) FROM workflows")
        return row[0]

    def find_paint_by_name(self, paint_name):
        return self.manager.fetch_all(
            """
            SELECT paint_id, company, product_line, paint_name, paint_type
            FROM paints
            WHERE paint_name LIKE ?
            ORDER BY company, product_line, paint_name
            """,
            (f"%{paint_name}%",),
        )

    def find_workflows_by_unit(self, unit):
        return self.manager.fetch_all(
            """
            SELECT workflow_id, superfaction, faction, unit, workflow_file, status
            FROM workflows
            WHERE unit LIKE ?
            ORDER BY faction, unit
            """,
            (f"%{unit}%",),
        )
