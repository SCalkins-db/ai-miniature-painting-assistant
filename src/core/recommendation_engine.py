from src.core.workflow_manager import WorkflowManager
from src.core.shopping_list import ShoppingList
from src.core.substitution_engine import SubstitutionEngine


class RecommendationEngine:
    def __init__(self):
        self.workflow_manager = WorkflowManager()
        self.shopping_list = ShoppingList()
        self.substitution_engine = SubstitutionEngine()

    def recommend_by_workflow_id(self, workflow_id, inventory_df):
        workflow = self.workflow_manager.get_workflow_by_id(workflow_id)
        missing_paints = self.shopping_list.get_missing_paints(workflow, inventory_df)
        substitutes = self.substitution_engine.suggest_substitutes(missing_paints)

        return {
            "workflow_id": workflow_id,
            "workflow": workflow,
            "missing_paints": missing_paints,
            "substitutes": substitutes,
        }
