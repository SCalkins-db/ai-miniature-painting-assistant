from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CORE_DIR = PROJECT_ROOT / "src" / "core"
DEBUG_DIR = PROJECT_ROOT / "src" / "debug"
SCRIPTS_DIR = PROJECT_ROOT / "src" / "scripts"


FILES = {
    CORE_DIR / "inventory_checker.py": '''class InventoryChecker:
    def get_owned_paint_ids(self, inventory_df):
        if inventory_df is None or inventory_df.empty:
            return set()

        owned = inventory_df[inventory_df["Owned"] == True]
        return set(owned["Paint_ID"].dropna())

    def check_workflow_inventory(self, workflow_df, inventory_df):
        owned_ids = self.get_owned_paint_ids(inventory_df)

        required = workflow_df[workflow_df["Optional"].str.lower() != "yes"]
        optional = workflow_df[workflow_df["Optional"].str.lower() == "yes"]

        required = required[["Paint_ID", "Paint_Name"]].drop_duplicates()
        optional = optional[["Paint_ID", "Paint_Name"]].drop_duplicates()

        missing_required = required[~required["Paint_ID"].isin(owned_ids)]
        owned_required = required[required["Paint_ID"].isin(owned_ids)]

        return {
            "owned_required": owned_required.reset_index(drop=True),
            "missing_required": missing_required.reset_index(drop=True),
            "optional": optional.reset_index(drop=True),
            "required_count": len(required),
            "owned_required_count": len(owned_required),
            "missing_required_count": len(missing_required),
            "is_paintable": len(missing_required) == 0,
        }
''',

    CORE_DIR / "workflow_selector.py": '''from src.core.workflow_manager import WorkflowManager


class WorkflowSelector:
    def __init__(self):
        self.manager = WorkflowManager()

    def find(self, superfaction=None, faction=None, unit=None):
        catalog = self.manager.get_catalog()

        if superfaction:
            catalog = catalog[
                catalog["Superfaction"].str.contains(superfaction, case=False, na=False)
            ]

        if faction:
            catalog = catalog[
                catalog["Faction"].str.contains(faction, case=False, na=False)
            ]

        if unit:
            catalog = catalog[
                catalog["Unit"].str.contains(unit, case=False, na=False)
            ]

        return catalog.reset_index(drop=True)

    def first_match(self, superfaction=None, faction=None, unit=None):
        matches = self.find(superfaction=superfaction, faction=faction, unit=unit)

        if matches.empty:
            return None

        return matches.iloc[0]
''',

    CORE_DIR / "recommendation_formatter.py": '''class RecommendationFormatter:
    def format_recommendation(self, result):
        workflow_id = result["workflow_id"]
        missing = result["missing_paints"]
        substitutes = result["substitutes"]

        lines = []
        lines.append(f"Workflow: {workflow_id}")
        lines.append("")

        if missing.empty:
            lines.append("Required paints: COMPLETE")
            lines.append("Shopping list: Nothing needed")
        else:
            lines.append("Missing required paints:")

            for _, row in missing.iterrows():
                lines.append(f"- {row['Paint_Name']} ({row['Paint_ID']})")

        lines.append("")

        if substitutes:
            lines.append("Substitution suggestions:")

            for suggestion in substitutes:
                lines.append(
                    f"- {suggestion['Missing_Paint_Name']}: "
                    f"{suggestion['Suggested_Substitute']}"
                )
        else:
            lines.append("Substitution suggestions: None needed")

        return "\\n".join(lines)
''',

    CORE_DIR / "paint_matcher.py": '''class PaintMatcher:
    def find_by_paint_id(self, paint_database_df, paint_id):
        matches = paint_database_df[paint_database_df["Paint_ID"] == paint_id]
        return matches.reset_index(drop=True)

    def find_by_name(self, paint_database_df, paint_name):
        matches = paint_database_df[
            paint_database_df["Paint_Name"].str.contains(
                paint_name,
                case=False,
                na=False
            )
        ]
        return matches.reset_index(drop=True)

    def find_same_company(self, paint_database_df, company):
        matches = paint_database_df[
            paint_database_df["Company"].str.contains(
                company,
                case=False,
                na=False
            )
        ]
        return matches.reset_index(drop=True)
''',

    DEBUG_DIR / "intelligence_layer_test.py": '''import pandas as pd

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

print("\\nWORKFLOW SELECTOR RESULTS:")
print(matches)

if matches.empty:
    print("\\nFAILED: No workflow matches found.")
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

print("\\nINVENTORY CHECK:")
print(f"Required paints: {inventory_result['required_count']}")
print(f"Owned required paints: {inventory_result['owned_required_count']}")
print(f"Missing required paints: {inventory_result['missing_required_count']}")
print(f"Paintable: {inventory_result['is_paintable']}")

recommendation = engine.recommend_by_workflow_id(workflow_id, fake_inventory)

print("\\nFORMATTED RECOMMENDATION:")
print(formatter.format_recommendation(recommendation))

print("\\n" + "=" * 60)
print("INTELLIGENCE LAYER TEST COMPLETE")
print("=" * 60)
''',

    SCRIPTS_DIR / "system_health_check.py": '''import pandas as pd
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

    print("\\nWORKFLOW ENGINE CHECK:")

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

    print("\\n" + "=" * 60)

    if all(checks):
        print("SYSTEM STATUS: PASS")
    else:
        print("SYSTEM STATUS: FAIL")

    print("=" * 60)


if __name__ == "__main__":
    main()
'''
}


def write_file(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"WROTE: {path}")


def main():
    print("=" * 60)
    print("BUILDING INTELLIGENCE LAYER")
    print("=" * 60)

    for path, content in FILES.items():
        write_file(path, content)

    print("=" * 60)
    print("DONE")
    print("=" * 60)
    print("Now run:")
    print("python -m src.debug.intelligence_layer_test")
    print("python -m src.scripts.system_health_check")


if __name__ == "__main__":
    main()