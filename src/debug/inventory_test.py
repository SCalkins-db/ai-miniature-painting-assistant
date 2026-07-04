# Allow direct execution from project root or with python -m
import sys
from pathlib import Path

_project_root = Path(__file__).resolve()
while _project_root.parent != _project_root:
    if (_project_root / "src").exists() and (_project_root / "data").exists():
        break
    _project_root = _project_root.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

# Allow direct execution from the project root, e.g. python src/debug/script.py
import sys
from pathlib import Path

_project_root = Path(__file__).resolve()
while _project_root.parent != _project_root:
    if (_project_root / "src").exists() and (_project_root / "data").exists():
        break
    _project_root = _project_root.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

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
