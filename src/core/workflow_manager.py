from src.core.workflow_loader import WorkflowLoader
from src.core.workflow_validator import WorkflowValidator


class WorkflowManager:
    def __init__(self):
        self.loader = WorkflowLoader()
        self.validator = WorkflowValidator()

    def get_catalog(self):
        return self.loader.get_catalog().dropna(how="all")

    def get_workflow_by_id(self, workflow_id):
        workflow = self.loader.load_workflow_by_id(workflow_id)
        is_valid, errors = self.validator.validate_workflow(workflow)

        if not is_valid:
            raise ValueError(f"Workflow validation failed: {errors}")

        return workflow

    def search_by_faction(self, faction):
        return self.loader.search_by_faction(faction).dropna(how="all")

    def search_by_unit(self, unit):
        return self.loader.search_by_unit(unit).dropna(how="all")
