from src.core.workflow_loader import WorkflowLoader


loader = WorkflowLoader()

print("WORKFLOW CATALOG")
print(loader.get_catalog())

print("\nSEARCH FACTION: Ultramarines")
print(loader.search_by_faction("Ultramarines"))

print("\nSEARCH UNIT: Intercessors")
print(loader.search_by_unit("Intercessors"))