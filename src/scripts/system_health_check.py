import pandas as pd
from pathlib import Path

from src.core.workflow_manager import WorkflowManager
from src.core.recommendation_engine import RecommendationEngine


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def check_path(label, path):
    exists = path.exists()
    status = "PASS" if exists else "FAIL"
    print(f"{status}: {label} -> {path}")
    return exists


def main():
    print("=" * 60)
    print("SYSTEM HEALTH CHECK")
    print("=" * 60)

    checks = []

    checks.append(check_path("data directory", PROJECT_ROOT / "data"))
    checks.append(check_path("src/core directory", PROJECT_ROOT / "src" / "core"))
    checks.append(check_path("workflow catalog", PROJECT_ROOT / "data" / "workflow_catalog" / "workflow_catalog.csv"))
    checks.append(check_path("workflow directory", PROJECT_ROOT / "data" / "workflows"))
    checks.append(check_path("workflow loader", PROJECT_ROOT / "src" / "core" / "workflow_loader.py"))
    checks.append(check_path("workflow validator", PROJECT_ROOT / "src" / "core" / "workflow_validator.py"))
    checks.append(check_path("workflow manager", PROJECT_ROOT / "src" / "core" / "workflow_manager.py"))
    checks.append(check_path("recommendation engine", PROJECT_ROOT / "src" / "core" / "recommendation_engine.py"))
    checks.append(check_path("shopping list", PROJECT_ROOT / "src" / "core" / "shopping_list.py"))
    checks.append(check_path("substitution engine", PROJECT_ROOT / "src" / "core" / "substitution_engine.py"))
    checks.append(check_path("inventory checker", PROJECT_ROOT / "src" / "core" / "inventory_checker.py"))
    checks.append(check_path("workflow selector", PROJECT_ROOT / "src" / "core" / "workflow_selector.py"))
    checks.append(check_path("recommendation formatter", PROJECT_ROOT / "src" / "core" / "recommendation_formatter.py"))
    checks.append(check_path("paint matcher", PROJECT_ROOT / "src" / "core" / "paint_matcher.py"))

    print("\nWORKFLOW ENGINE CHECK:")

    try:
        manager = WorkflowManager()
        catalog = manager.get_catalog()
        print(f"PASS: workflows in catalog -> {len(catalog)}")

        if not catalog.empty:
            workflow_id = catalog.iloc[0]["Workflow_ID"]
            workflow = manager.get_workflow_by_id(workflow_id)
            print(f"PASS: workflow loaded and validated -> {workflow_id}")
            print(f"PASS: workflow rows -> {len(workflow)}")

        fake_inventory = pd.DataFrame([
            {"Paint_ID": "GW_BASE_MACRAGGE_BLUE", "Owned": True, "Wishlist": False, "Qty": 1}
        ])

        engine = RecommendationEngine()

        if not catalog.empty:
            result = engine.recommend_by_workflow_id(catalog.iloc[0]["Workflow_ID"], fake_inventory)
            print(f"PASS: recommendation engine executed")
            print(f"PASS: missing paints found -> {len(result['missing_paints'])}")

    except Exception as error:
        print(f"FAIL: workflow engine error -> {error}")
        checks.append(False)

    print("\n" + "=" * 60)

    if all(checks):
        print("SYSTEM STATUS: PASS")
    else:
        print("SYSTEM STATUS: FAIL")

    print("=" * 60)


if __name__ == "__main__":
    main()
