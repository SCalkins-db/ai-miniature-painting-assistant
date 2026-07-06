import pandas as pd

from src.core.workflow_manager import WorkflowManager
from src.core.workflow_selector import WorkflowSelector
from src.core.inventory_checker import InventoryChecker
from src.core.recommendation_engine import RecommendationEngine
from src.core.recommendation_formatter import RecommendationFormatter


print("=" * 60)
print("INTELLIGENCE LAYER TEST")
print("=" * 60)

manager = WorkflowManager()
selector = WorkflowSelector()
checker = InventoryChecker()
engine = RecommendationEngine()
formatter = RecommendationFormatter()

matches = selector.find(faction="Ultramarines", unit="Intercessors")

print("\nWORKFLOW SELECTOR RESULTS:")
print(matches)

if matches.empty:
    print("\nFAILED: No workflow matches found.")
    raise SystemExit

workflow_id = matches.iloc[0]["Workflow_ID"]
workflow = manager.get_workflow_by_id(workflow_id)

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

inventory_result = checker.check_workflow_inventory(workflow, fake_inventory)

print("\nINVENTORY CHECK:")
print(f"Required paints: {inventory_result['required_count']}")
print(f"Owned required paints: {inventory_result['owned_required_count']}")
print(f"Missing required paints: {inventory_result['missing_required_count']}")
print(f"Paintable: {inventory_result['is_paintable']}")

recommendation = engine.recommend_by_workflow_id(workflow_id, fake_inventory)

print("\nFORMATTED RECOMMENDATION:")
print(formatter.format_recommendation(recommendation))

print("\n" + "=" * 60)
print("INTELLIGENCE LAYER TEST COMPLETE")
print("=" * 60)
