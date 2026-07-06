from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = PROJECT_ROOT / "src" / "scripts"
REPORTS_DIR = PROJECT_ROOT / "exports" / "reports"


FILES = {
    SCRIPTS_DIR / "project_doctor.py": r'''from pathlib import Path
import subprocess
import sys
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]


REQUIRED_PATHS = {
    "Project Root": PROJECT_ROOT,
    "Data Directory": PROJECT_ROOT / "data",
    "Source Directory": PROJECT_ROOT / "src",
    "Core Directory": PROJECT_ROOT / "src" / "core",
    "Debug Directory": PROJECT_ROOT / "src" / "debug",
    "Scripts Directory": PROJECT_ROOT / "src" / "scripts",
    "Workflow Catalog": PROJECT_ROOT / "data" / "workflow_catalog" / "workflow_catalog.csv",
    "Workflow Templates": PROJECT_ROOT / "data" / "workflow_templates",
    "Workflow Directory": PROJECT_ROOT / "data" / "workflows",
    "Architecture Docs": PROJECT_ROOT / "docs" / "architecture",
    "Workflow Loader": PROJECT_ROOT / "src" / "core" / "workflow_loader.py",
    "Workflow Validator": PROJECT_ROOT / "src" / "core" / "workflow_validator.py",
    "Workflow Manager": PROJECT_ROOT / "src" / "core" / "workflow_manager.py",
    "Recommendation Engine": PROJECT_ROOT / "src" / "core" / "recommendation_engine.py",
    "Shopping List": PROJECT_ROOT / "src" / "core" / "shopping_list.py",
    "Substitution Engine": PROJECT_ROOT / "src" / "core" / "substitution_engine.py",
    "Inventory Checker": PROJECT_ROOT / "src" / "core" / "inventory_checker.py",
    "Workflow Selector": PROJECT_ROOT / "src" / "core" / "workflow_selector.py",
    "Recommendation Formatter": PROJECT_ROOT / "src" / "core" / "recommendation_formatter.py",
    "Paint Matcher": PROJECT_ROOT / "src" / "core" / "paint_matcher.py",
}


DIAGNOSTIC_COMMANDS = [
    ("Workflow Loader Test", ["python", "-m", "src.debug.workflow_loader_test"]),
    ("Workflow Validator Test", ["python", "-m", "src.debug.workflow_validator_test"]),
    ("Core Engine Test", ["python", "-m", "src.debug.core_engine_test"]),
    ("Intelligence Layer Test", ["python", "-m", "src.debug.intelligence_layer_test"]),
]


def status_line(label, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    print(f"{status:<6} {label:<35} {detail}")


def check_required_paths():
    print("\nPROJECT STRUCTURE")
    print("-" * 60)

    results = []

    for label, path in REQUIRED_PATHS.items():
        exists = path.exists()
        results.append(exists)
        status_line(label, exists, str(path))

    return results


def check_workflow_catalog():
    print("\nWORKFLOW CATALOG")
    print("-" * 60)

    catalog_path = PROJECT_ROOT / "data" / "workflow_catalog" / "workflow_catalog.csv"

    if not catalog_path.exists():
        status_line("Catalog Exists", False, str(catalog_path))
        return [False]

    try:
        df = pd.read_csv(catalog_path).dropna(how="all")
        status_line("Catalog Readable", True)
        status_line("Workflow Count", len(df) > 0, str(len(df)))
        return [True, len(df) > 0]
    except Exception as error:
        status_line("Catalog Readable", False, str(error))
        return [False]


def run_diagnostics():
    print("\nDIAGNOSTIC TESTS")
    print("-" * 60)

    results = []

    for label, command in DIAGNOSTIC_COMMANDS:
        try:
            completed = subprocess.run(
                command,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=60,
            )

            passed = completed.returncode == 0
            results.append(passed)

            status_line(label, passed)

            if not passed:
                print(completed.stdout)
                print(completed.stderr)

        except Exception as error:
            results.append(False)
            status_line(label, False, str(error))

    return results


def main():
    print("=" * 60)
    print("AI MINIATURE PAINTING ASSISTANT")
    print("PROJECT DOCTOR")
    print("=" * 60)

    results = []
    results.extend(check_required_paths())
    results.extend(check_workflow_catalog())
    results.extend(run_diagnostics())

    print("\n" + "=" * 60)

    if all(results):
        print("SYSTEM STATUS: PASS")
    else:
        print("SYSTEM STATUS: FAIL")

    print("=" * 60)


if __name__ == "__main__":
    main()
''',

    SCRIPTS_DIR / "project_inventory.py": r'''from pathlib import Path
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
''',

    SCRIPTS_DIR / "project_report.py": r'''from pathlib import Path
from datetime import datetime
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORTS_DIR = PROJECT_ROOT / "exports" / "reports"
REPORT_PATH = REPORTS_DIR / "project_status.md"


CORE_MODULES = [
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


def count_files(path, pattern="*"):
    if not path.exists():
        return 0

    return len(list(path.rglob(pattern)))


def get_workflow_count():
    catalog_path = PROJECT_ROOT / "data" / "workflow_catalog" / "workflow_catalog.csv"

    if not catalog_path.exists():
        return 0

    try:
        return len(pd.read_csv(catalog_path).dropna(how="all"))
    except Exception:
        return 0


def get_existing_core_modules():
    core_dir = PROJECT_ROOT / "src" / "core"

    if not core_dir.exists():
        return []

    existing = []

    for module in CORE_MODULES:
        if (core_dir / module).exists():
            existing.append(module)

    return existing


def build_report():
    existing_core = get_existing_core_modules()
    workflow_count = get_workflow_count()

    total_py_files = count_files(PROJECT_ROOT / "src", "*.py")
    total_csv_files = count_files(PROJECT_ROOT / "data", "*.csv")
    total_xlsx_files = count_files(PROJECT_ROOT / "data", "*.xlsx")
    total_md_files = count_files(PROJECT_ROOT / "docs", "*.md")

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = []

    lines.append("# AI-Assisted Miniature Painting Recommendation System")
    lines.append("")
    lines.append("## Project Status Report")
    lines.append("")
    lines.append(f"Generated: {now}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Current Architecture")
    lines.append("")
    lines.append("The project has moved beyond a paint database and now has the foundation of a recommendation engine.")
    lines.append("")
    lines.append("Current system chain:")
    lines.append("")
    lines.append("```text")
    lines.append("Paint Registries")
    lines.append("    ↓")
    lines.append("Registry Loader")
    lines.append("    ↓")
    lines.append("Inventory")
    lines.append("    ↓")
    lines.append("Workflow Catalog")
    lines.append("    ↓")
    lines.append("Workflow Loader")
    lines.append("    ↓")
    lines.append("Workflow Validator")
    lines.append("    ↓")
    lines.append("Workflow Manager")
    lines.append("    ↓")
    lines.append("Recommendation Engine")
    lines.append("    ↓")
    lines.append("Shopping List + Substitution Engine")
    lines.append("```")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Current Counts")
    lines.append("")
    lines.append(f"- Python files: {total_py_files}")
    lines.append(f"- CSV files in data: {total_csv_files}")
    lines.append(f"- Excel files in data: {total_xlsx_files}")
    lines.append(f"- Markdown docs: {total_md_files}")
    lines.append(f"- Workflows in catalog: {workflow_count}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Core Modules Present")
    lines.append("")

    for module in CORE_MODULES:
        marker = "✅" if module in existing_core else "❌"
        lines.append(f"- {marker} `{module}`")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Completed Milestones")
    lines.append("")
    lines.append("- Paint registry foundation")
    lines.append("- Inventory foundation")
    lines.append("- Workflow folder structure")
    lines.append("- Workflow catalog")
    lines.append("- Workflow template")
    lines.append("- Workflow loader")
    lines.append("- Workflow validator")
    lines.append("- Workflow manager")
    lines.append("- Recommendation engine foundation")
    lines.append("- Shopping list foundation")
    lines.append("- Substitution engine framework")
    lines.append("- Intelligence layer foundation")
    lines.append("- System health check tooling")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Next Planned Work")
    lines.append("")
    lines.append("- Connect recommendation engine to real inventory data")
    lines.append("- Add real substitution logic using paint registry data")
    lines.append("- Add workflow selector improvements")
    lines.append("- Add formatted CLI outputs")
    lines.append("- Start GUI integration")
    lines.append("- Add workflow editor")
    lines.append("- Add project-wide test automation")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Estimated MVP Status")
    lines.append("")
    lines.append("The project is in the transition from core application logic into usable recommendation features.")
    lines.append("")
    lines.append("Estimated MVP completion: **60–65%**")
    lines.append("")

    return "\n".join(lines)


def main():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    report = build_report()
    REPORT_PATH.write_text(report, encoding="utf-8")

    print("=" * 60)
    print("PROJECT REPORT")
    print("=" * 60)
    print(f"WROTE: {REPORT_PATH}")
    print("=" * 60)


if __name__ == "__main__":
    main()
''',

    SCRIPTS_DIR / "project_builder.py": r'''from pathlib import Path
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]


BUILDER_COMMANDS = [
    ("Architecture Docs", ["python", "-m", "src.scripts.create_architecture_docs"]),
    ("Core Engine Modules", ["python", "-m", "src.scripts.build_core_engine_modules"]),
    ("Intelligence Layer", ["python", "-m", "src.scripts.build_intelligence_layer"]),
    ("Shop Tools", ["python", "-m", "src.scripts.build_shop_tools"]),
]


def run_command(label, command):
    print(f"\nRUNNING: {label}")
    print("-" * 60)

    try:
        completed = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            timeout=120,
        )

        print(completed.stdout)

        if completed.returncode != 0:
            print(completed.stderr)
            print(f"FAILED: {label}")
            return False

        print(f"PASS: {label}")
        return True

    except Exception as error:
        print(f"FAILED: {label} -> {error}")
        return False


def main():
    print("=" * 60)
    print("PROJECT BUILDER")
    print("=" * 60)

    results = []

    for label, command in BUILDER_COMMANDS:
        results.append(run_command(label, command))

    print("\n" + "=" * 60)

    if all(results):
        print("PROJECT BUILDER STATUS: PASS")
    else:
        print("PROJECT BUILDER STATUS: FAIL")

    print("=" * 60)
    print("\nRecommended next commands:")
    print("python -m src.scripts.project_doctor")
    print("python -m src.scripts.project_inventory")
    print("python -m src.scripts.project_report")


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
    print("BUILDING SHOP TOOLS")
    print("=" * 60)

    for path, content in FILES.items():
        write_file(path, content)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("DONE")
    print("=" * 60)
    print("Now run:")
    print("python -m src.scripts.project_doctor")
    print("python -m src.scripts.project_inventory")
    print("python -m src.scripts.project_report")
    print("python -m src.scripts.project_builder")


if __name__ == "__main__":
    main()