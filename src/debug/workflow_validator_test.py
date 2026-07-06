from src.core.workflow_loader import WorkflowLoader
from src.core.workflow_validator import WorkflowValidator


loader = WorkflowLoader()
validator = WorkflowValidator()

print("=" * 50)
print("WORKFLOW VALIDATOR TEST")
print("=" * 50)

catalog = loader.get_catalog().dropna(how="all")

print("\nCATALOG:")
print(catalog)

if catalog.empty:
    print("\nNo workflows found in catalog yet.")
else:
    first_workflow_id = catalog.iloc[0]["Workflow_ID"]

    print(f"\nTesting workflow: {first_workflow_id}")

    workflow = loader.load_workflow_by_id(first_workflow_id)

    print("\nLOADED WORKFLOW:")
    print(workflow)

    is_valid, errors = validator.validate_workflow(workflow)

    print("\nVALIDATION RESULT:")
    print(f"Valid: {is_valid}")

    if errors:
        print("\nERRORS:")
        for error in errors:
            print(f"- {error}")
    else:
        print("No validation errors found.")
