from pathlib import Path
import re


def slugify(value):
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value or "unknown"


class WorkflowCSVWriter:
    def __init__(self, workflow_root="data/workflows/imported"):
        self.workflow_root = Path(workflow_root)
        self.workflow_root.mkdir(parents=True, exist_ok=True)

    def write(self, workflow_df, workflow_id, title=""):
        filename = f"{slugify(workflow_id)}.csv"
        path = self.workflow_root / filename

        workflow_df.to_csv(path, index=False)

        return path
