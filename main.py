from src.paint_database import PaintDatabase


db = PaintDatabase("data/paints.csv")

print("ALL PAINTS")
print(db.get_all_paints())

print("\nSEARCH: blue")
print(db.search_by_name("blue"))

print("\nSEARCH: Citadel")
print(db.search_by_brand("Citadel"))