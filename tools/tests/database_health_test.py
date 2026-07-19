from src.gui.database.database_statistics import get_table_counts
from src.gui.database import run_integrity_checks


print("=" * 60)
print("DATABASE HEALTH TEST")
print("=" * 60)

counts = get_table_counts()

print("\nTABLE COUNTS:")
for table, count in counts.items():
    print(f"{table:<20} {count}")

print("\nINTEGRITY:")
results = run_integrity_checks()

for label, passed, detail in results:
    status = "PASS" if passed else "FAIL"
    print(f"{status:<6} {label:<30} {detail}")

print("=" * 60)

if all(passed for _, passed, _ in results):
    print("DATABASE HEALTH TEST: PASS")
else:
    print("DATABASE HEALTH TEST: FAIL")

print("=" * 60)
