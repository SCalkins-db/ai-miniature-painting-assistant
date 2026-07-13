from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CORE_DIR = PROJECT_ROOT / "src" / "core"
DEBUG_DIR = PROJECT_ROOT / "src" / "debug"


FILES = {
    CORE_DIR / "workflow_manager.py": '''from src.core.workflow_loader import WorkflowLoader
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
''',

    CORE_DIR / "shopping_list.py": '''class ShoppingList:
    def get_required_paints(self, workflow_df):
        required = workflow_df[workflow_df["Optional"].str.lower() != "yes"]
        return required[["Paint_ID", "Paint_Name"]].drop_duplicates()

    def get_missing_paints(self, workflow_df, inventory_df):
        required = self.get_required_paints(workflow_df)

        owned_ids = set(
            inventory_df[inventory_df["Owned"] == True]["Paint_ID"].dropna()
        )

        missing = required[~required["Paint_ID"].isin(owned_ids)]

        return missing.reset_index(drop=True)
''',

    CORE_DIR / "substitution_engine.py": '''class SubstitutionEngine:
    def suggest_substitutes(self, missing_paints_df):
        suggestions = []

        for _, row in missing_paints_df.iterrows():
            suggestions.append({
                "Missing_Paint_ID": row["Paint_ID"],
                "Missing_Paint_Name": row["Paint_Name"],
                "Suggested_Substitute": "No substitute available yet",
            })

        return suggestions
''',

    CORE_DIR / "recommendation_engine.py": '''from src.core.workflow_manager import WorkflowManager
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
''',

    DEBUG_DIR / "core_engine_test.py": '''import pandas as pd

from src.core.workflow_manager import WorkflowManager
from src.core.recommendation_engine import RecommendationEngine


print("=" * 60)
print("CORE ENGINE DIAGNOSTIC TEST")
print("=" * 60)

manager = WorkflowManager()

catalog = manager.get_catalog()

print("\\nCATALOG:")
print(catalog)

if catalog.empty:
    print("\\nFAILED: Catalog is empty.")
    raise SystemExit

workflow_id = catalog.iloc[0]["Workflow_ID"]

print(f"\\nTESTING WORKFLOW ID: {workflow_id}")

workflow = manager.get_workflow_by_id(workflow_id)

print("\\nWORKFLOW LOADED AND VALIDATED:")
print(workflow)

fake_inventory = pd.DataFrame([
    {
        "Paint_ID": "GW_BASE_MACRAGGE_BLUE",
        "Owned": True,
        "Wishlist": False,
        "Qty": 1,
    },
    {
        "Paint_ID": "GW_SHADE_NULN_OIL",
        "Owned": False,
        "Wishlist": True,
        "Qty": 0,
    },
])

engine = RecommendationEngine()

result = engine.recommend_by_workflow_id(workflow_id, fake_inventory)

print("\\nMISSING PAINTS:")
print(result["missing_paints"])

print("\\nSUBSTITUTION SUGGESTIONS:")
for suggestion in result["substitutes"]:
    print(suggestion)

print("\\n" + "=" * 60)
print("CORE ENGINE TEST COMPLETE")
print("=" * 60)
'''
}


def write_file(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"WROTE: {path}")


def main():
    print("=" * 60)
    print("BUILDING CORE ENGINE MODULES")
    print("=" * 60)

    for path, content in FILES.items():
        write_file(path, content)

    print("=" * 60)
    print("DONE")
    print("=" * 60)
    print("Now run:")
    print("python -m src.debug.core_engine_test")


if __name__ == "__main__":
    main()