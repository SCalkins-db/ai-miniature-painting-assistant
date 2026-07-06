from pathlib import Path
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
