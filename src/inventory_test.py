from src.core.inventory import InventoryManager
from src.core.paint_database import PaintDatabase

db = PaintDatabase("data/registries_csv")
inventory = InventoryManager()

# Clear inventory for testing
inventory.inventory_df = inventory.inventory_df.iloc[0:0]

# Games Workshop
inventory.add_paint("GW_BASE_ABADDON_BLACK", 3)

# Army Painter
inventory.add_paint("AP_SPEED_BLOOD_RED", 1)

# Vallejo
inventory.add_paint("VAL_GAME_COLOR_IMPERIAL_BLUE", 2)

# Wishlist examples
inventory.toggle_wishlist("GW_SHADE_NULN_OIL")
inventory.toggle_wishlist("AP_FANATIC_MATT_WHITE")

print("OWNED DETAILS")
print(inventory.view_owned_details(db.master_df))

print("\nWISHLIST DETAILS")
print(inventory.view_wishlist_details(db.master_df))

print("\nFILTER: Games Workshop")
print(inventory.filter_inventory(db.master_df, "Company", "Games Workshop"))

print("\nFILTER: Army Painter")
print(inventory.filter_inventory(db.master_df, "Company", "Army Painter"))

print("\nFILTER: Vallejo")
print(inventory.filter_inventory(db.master_df, "Company", "Vallejo"))

print("\nFILTER: Speedpaint")
print(inventory.filter_inventory(db.master_df, "Product_Line", "Speed"))

print("\nFILTER: Base")
print(inventory.filter_inventory(db.master_df, "Paint_Type", "Base"))