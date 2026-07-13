from src.database.database_manager import DatabaseManager
from src.database.database_queries import DatabaseQueries


print("=" * 60)
print("DATABASE TEST")
print("=" * 60)

manager = DatabaseManager()
manager.initialize()

queries = DatabaseQueries()

print(f"Paint count: {queries.count_paints()}")
print(f"Inventory count: {queries.count_inventory()}")
print(f"Workflow count: {queries.count_workflows()}")

print("\nFind paint: Macragge")
for row in queries.find_paint_by_name("Macragge"):
    print(row)

print("\nFind workflow: Intercessors")
for row in queries.find_workflows_by_unit("Intercessors"):
    print(row)

print("=" * 60)
print("DATABASE TEST COMPLETE")
print("=" * 60)
