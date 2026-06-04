from src.paint_database import PaintDatabase


db = PaintDatabase("data/paints.csv")

print("ALL PAINTS")
print(db.get_all_paints())

print("\nSEARCH: blue")
print(db.search_by_color_family("blue"))

print("\nSEARCH: Citadel")
print(db.search_by_brand("Citadel"))

print("\nSEARCH: Blue Color Family")
print(db.search_by_color_family("Blue"))

print("\nSEARCH: Base Paints")
print(db.search_by_paint_type("Base"))