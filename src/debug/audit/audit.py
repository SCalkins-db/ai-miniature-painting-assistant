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

# Missing Hex/RGB auditing
from src.core.paint_database import PaintDatabase


db = PaintDatabase("data/registries_csv")

print(db.master_df.shape)
print(db.master_df.columns)
print(db.master_df.head())

missing_color = db.get_missing_color_data()

print("\nMISSING HEX/RGB VALUES")
print(
    missing_color[
        ["Paint_ID", "Company", "Product_Line", "Paint_Name", "Paint_Type", "Status", "Hex", "RGB"]
    ]
)

print(f"\nTotal missing Hex: {db.get_missing_hex_count()}")
print(f"Total missing RGB: {db.get_missing_rgb_count()}")
print(f"Total missing Hex or RGB: {db.get_missing_color_data_count()}")

print("\nTop Hex values:")
print(db.master_df["Hex"].value_counts(dropna=False).head(20))

print("\nMissing by company:")
print(missing_color["Company"].value_counts())

print("\nMissing by product line:")
print(missing_color["Product_Line"].value_counts())

print("\nArmy Painter missing examples:")
print(
    missing_color[
        missing_color["Company"].astype(str).str.contains("Army Painter", case=False, na=False)
    ][
        ["Paint_Name", "Product_Line", "Company", "Hex", "RGB"]
    ].head(50)
)
