import pandas as pd

from src.core.workflow_manager import WorkflowManager
from src.core.recommendation_engine import RecommendationEngine


print("=" * 60)
print("CORE ENGINE DIAGNOSTIC TEST")
print("=" * 60)

manager = WorkflowManager()

catalog = manager.get_catalog()

print("\nCATALOG:")
print(catalog)

if catalog.empty:
    print("\nFAILED: Catalog is empty.")
    raise SystemExit

workflow_id = catalog.iloc[0]["Workflow_ID"]

print(f"\nTESTING WORKFLOW ID: {workflow_id}")

workflow = manager.get_workflow_by_id(workflow_id)

print("\nWORKFLOW LOADED AND VALIDATED:")
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

print("\nMISSING PAINTS:")
print(result["missing_paints"])

print("\nSUBSTITUTION SUGGESTIONS:")
for suggestion in result["substitutes"]:
    print(suggestion)

print("\n" + "=" * 60)
print("CORE ENGINE TEST COMPLETE")
print("=" * 60)
