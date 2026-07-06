from pathlib import Path
import pandas as pd


class WorkflowLoader:
    def __init__(self, catalog_path="data/workflow_catalog/workflow_catalog.csv"):
        self.project_root = Path(__file__).resolve().parents[2]
        self.catalog_path = self.project_root / catalog_path
        self.catalog = self._load_catalog()

    def _load_catalog(self):
        if not self.catalog_path.exists():
            raise FileNotFoundError(f"Workflow catalog not found: {self.catalog_path}")

        return pd.read_csv(self.catalog_path)

    def get_catalog(self):
        return self.catalog

    def find_workflow(self, workflow_id):
        matches = self.catalog[self.catalog["Workflow_ID"] == workflow_id]

        if matches.empty:
            raise ValueError(f"No workflow found for Workflow_ID: {workflow_id}")

        return matches.iloc[0]

    def load_workflow_by_id(self, workflow_id):
        workflow_row = self.find_workflow(workflow_id)

        relative_path = workflow_row["Workflow_File"]
        workflow_path = self.project_root / relative_path

        if not workflow_path.exists():
            raise FileNotFoundError(f"Workflow file not found: {workflow_path}")

        return pd.read_csv(workflow_path)

    def search_by_faction(self, faction):
        return self.catalog[
            self.catalog["Faction"].str.contains(faction, case=False, na=False)
        ]

    def search_by_unit(self, unit):
        return self.catalog[
            self.catalog["Unit"].str.contains(unit, case=False, na=False)
        ]