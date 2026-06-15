from src.paint_database import PaintDatabase


db = PaintDatabase("data/registries_csv")

print(db.master_df.shape)
print(db.master_df.columns)
print(db.master_df.head())

print("\nALL PAINTS")
print(db.get_all_paints())

print("\nSEARCH PAINT NAME: blue")
print(db.search_by_paint_name("blue"))

print("\nSEARCH COMPANY: Games Workshop")
print(db.search_by_company("Games Workshop"))

print("\nSEARCH BRAND: Citadel")
print(db.search_by_brand("Citadel"))

print("\nSEARCH PRODUCT LINE: Base")
print(db.search_by_product_line("Base"))

print("\nSEARCH PAINT TYPE: Contrast")
print(db.search_by_paint_type("Contrast"))

print("\nSEARCH STATUS: Active")
print(db.search_by_status("Active"))

