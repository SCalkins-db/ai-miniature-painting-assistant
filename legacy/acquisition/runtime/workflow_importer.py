from pathlib import Path
import pandas as pd

from src.database.database_manager import DatabaseManager


class WorkflowImporter:
    def __init__(self):
        self.manager = DatabaseManager()
        self.manager.initialize()

    def import_workflow_csv(self, workflow_csv_path):
        workflow_csv_path = Path(workflow_csv_path)

        if not workflow_csv_path.exists():
            raise FileNotFoundError(f"Workflow CSV not found: {workflow_csv_path}")

        df = pd.read_csv(workflow_csv_path).fillna("")

        if df.empty:
            return 0

        rows = []

        for _, row in df.iterrows():
            rows.append((
                row.get("Workflow_ID", ""),
                int(row.get("Area_Order", 0) or 0),
                int(row.get("Step_Order", 0) or 0),
                row.get("Model_Area", ""),
                row.get("Technique", ""),
                row.get("Paint_ID", ""),
                row.get("Paint_Name", ""),
                "",
                row.get("Purpose", ""),
                1 if str(row.get("Optional", "")).lower() in ["yes", "true", "1"] else 0,
                row.get("Notes", ""),
            ))

        with self.manager.connect() as conn:
            conn.executemany(
                """
                INSERT INTO workflow_steps (
                    workflow_id,
                    area_order,
                    step_order,
                    model_area,
                    technique,
                    paint_id,
                    paint_name,
                    paint_type,
                    purpose,
                    optional,
                    notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            conn.commit()

        return len(rows)

    def import_folder(self, workflow_dir="data/workflows/imported"):
        workflow_dir = Path(workflow_dir)
        results = []

        for csv_path in sorted(workflow_dir.glob("*.csv")):
            try:
                count = self.import_workflow_csv(csv_path)
                results.append((str(csv_path), count, "Imported"))
            except Exception as error:
                results.append((str(csv_path), 0, f"Failed: {error}"))

        return results
