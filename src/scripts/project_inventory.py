from pathlib import Path
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]


SECTIONS = {
    "Core Modules": PROJECT_ROOT / "src" / "core",
    "Debug Tests": PROJECT_ROOT / "src" / "debug",
    "Scripts": PROJECT_ROOT / "src" / "scripts",
    "Architecture Docs": PROJECT_ROOT / "docs" / "architecture",
    "Data Directory": PROJECT_ROOT / "data",
}


EXPECTED_CORE_MODULES = [
    "inventory.py",
    "workflow_loader.py",
    "workflow_validator.py",
    "workflow_manager.py",
    "recommendation_engine.py",
    "shopping_list.py",
    "substitution_engine.py",
    "inventory_checker.py",
    "workflow_selector.py",
    "recommendation_formatter.py",
    "paint_matcher.py",
]


def list_files(label, path):
    print(f"\n{label}")
    print("-" * 60)

    if not path.exists():
        print(f"MISSING DIRECTORY: {path}")
        return []

    files = sorted([item.name for item in path.iterdir() if item.is_file()])

    if not files:
        print("No files found.")
        return []

    for filename in files:
        print(filename)

    return files


def workflow_counts():
    print("\nWorkflow Inventory")
    print("-" * 60)

    catalog_path = PROJECT_ROOT / "data" / "workflow_catalog" / "workflow_catalog.csv"
    workflows_dir = PROJECT_ROOT / "data" / "workflows"

    if catalog_path.exists():
        try:
            catalog = pd.read_csv(catalog_path).dropna(how="all")
            print(f"Catalog workflows: {len(catalog)}")
        except Exception as error:
            print(f"Catalog workflows: ERROR reading catalog -> {error}")
    else:
        print("Catalog workflows: catalog missing")

    if workflows_dir.exists():
        workflow_files = list(workflows_dir.rglob("*.csv"))
        print(f"Workflow CSV files: {len(workflow_files)}")
    else:
        print("Workflow CSV files: workflow directory missing")


def missing_components():
    print("\nMissing / Planned Components")
    print("-" * 60)

    core_dir = PROJECT_ROOT / "src" / "core"
    existing = set()

    if core_dir.exists():
        existing = {item.name for item in core_dir.iterdir() if item.is_file()}

    missing = [module for module in EXPECTED_CORE_MODULES if module not in existing]

    if not missing:
        print("No expected core modules missing.")
    else:
        for module in missing:
            print(module)

    print("\nFuture planned work:")
    print("- GUI integration")
    print("- Workflow editor")
    print("- SQLite backend")
    print("- Real paint substitution logic")
    print("- Cross-brand color matching")
    print("- AI recommendation layer")


def main():
    print("=" * 60)
    print("PROJECT INVENTORY")
    print("=" * 60)

    for label, path in SECTIONS.items():
        list_files(label, path)

    workflow_counts()
    missing_components()

    print("\n" + "=" * 60)
    print("PROJECT INVENTORY COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
