from pathlib import Path
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
