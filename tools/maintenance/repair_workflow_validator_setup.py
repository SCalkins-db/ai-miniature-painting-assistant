from pathlib import Path
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

CORE_DIR = PROJECT_ROOT / "src" / "core"
DEBUG_DIR = PROJECT_ROOT / "src" / "debug"
CATALOG_PATH = PROJECT_ROOT / "data" / "workflow_catalog" / "workflow_catalog.csv"

VALIDATOR_PATH = CORE_DIR / "workflow_validator.py"
TEST_PATH = DEBUG_DIR / "workflow_validator_test.py"


VALIDATOR_CODE = '''import pandas as pd


class WorkflowValidator:
    REQUIRED_COLUMNS = [
        "Workflow_ID",
        "Superfaction",
        "Faction",
        "Unit",
        "Model_Area",
        "Area_Order",
        "Step_Order",
        "Technique",
        "Paint_ID",
        "Paint_Name",
        "Purpose",
        "Optional",
        "Notes",
    ]

    def validate_columns(self, workflow_df):
        missing = [c for c in self.REQUIRED_COLUMNS if c not in workflow_df.columns]
        return len(missing) == 0, missing

    def validate_required_values(self, workflow_df):
        required = [
            "Workflow_ID",
            "Faction",
            "Unit",
            "Model_Area",
            "Area_Order",
            "Step_Order",
            "Technique",
        ]

        errors = []

        for field in required:
            if workflow_df[field].isna().any():
                errors.append(f"Missing values in required field: {field}")

        return errors

    def validate_area_order(self, workflow_df):
        errors = []
        area_orders = workflow_df["Area_Order"].tolist()

        if area_orders != sorted(area_orders):
            errors.append("Area_Order is not sorted correctly.")

        return errors

    def validate_step_order(self, workflow_df):
        errors = []

        for model_area, group in workflow_df.groupby("Model_Area"):
            steps = group["Step_Order"].tolist()

            if steps != sorted(steps):
                errors.append(f"Step_Order is not sorted correctly for Model_Area: {model_area}")

        return errors

    def validate_workflow(self, workflow_df):
        errors = []

        columns_valid, missing_columns = self.validate_columns(workflow_df)

        if not columns_valid:
            return False, [f"Missing required columns: {missing_columns}"]

        errors.extend(self.validate_required_values(workflow_df))
        errors.extend(self.validate_area_order(workflow_df))
        errors.extend(self.validate_step_order(workflow_df))

        return len(errors) == 0, errors
'''


TEST_CODE = '''from src.core.workflow_loader import WorkflowLoader
from src.core.workflow_validator import WorkflowValidator


loader = WorkflowLoader()
validator = WorkflowValidator()

print("=" * 50)
print("WORKFLOW VALIDATOR TEST")
print("=" * 50)

catalog = loader.get_catalog().dropna(how="all")

print("\\nCATALOG:")
print(catalog)

if catalog.empty:
    print("\\nNo workflows found in catalog yet.")
else:
    first_workflow_id = catalog.iloc[0]["Workflow_ID"]

    print(f"\\nTesting workflow: {first_workflow_id}")

    workflow = loader.load_workflow_by_id(first_workflow_id)

    print("\\nLOADED WORKFLOW:")
    print(workflow)

    is_valid, errors = validator.validate_workflow(workflow)

    print("\\nVALIDATION RESULT:")
    print(f"Valid: {is_valid}")

    if errors:
        print("\\nERRORS:")
        for error in errors:
            print(f"- {error}")
    else:
        print("No validation errors found.")
'''


def write_file(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"WROTE: {path}")


def clean_catalog():
    if not CATALOG_PATH.exists():
        print(f"CATALOG NOT FOUND: {CATALOG_PATH}")
        return

    df = pd.read_csv(CATALOG_PATH)
    df = df.dropna(how="all")
    df.to_csv(CATALOG_PATH, index=False)
    print(f"CLEANED CATALOG: {CATALOG_PATH}")
    print(df)


def main():
    print("=" * 50)
    print("REPAIRING WORKFLOW VALIDATOR SETUP")
    print("=" * 50)

    write_file(VALIDATOR_PATH, VALIDATOR_CODE)
    write_file(TEST_PATH, TEST_CODE)
    clean_catalog()

    print("=" * 50)
    print("DONE")
    print("=" * 50)
    print("Now run:")
    print("python -m src.scripts.repair_workflow_validator_setup")
    print("python -m src.debug.workflow_validator_test")


if __name__ == "__main__":
    main()