# Debug Snippets

## audit_dup_naming_code.txt

```python
    problem_names = ["BLUE_GREEN", "EMPERORS_CHILDREN", "NURGLES_ROT"]

    print("\nSpecific Duplicate Investigation")
    for name in problem_names:
        print(f"\n{name}")
        print(
            df[df["Paint_ID"].str.contains(name, case=False, na=False)]
            [["Paint_ID", "Company", "Brand", "Product_Line", "Paint_Name", "Hex", "RGB", "Paint_Type", "Status",
              "Source", "Notes"]]
        )

    print(df[df["Canonical_Paint_Key"] == "games workshop|layer|emperors children"])
    print(df[df["Canonical_Paint_Key"] == "games workshop|technical|nurgles rot"])

    if df["Paint_ID"].duplicated().sum() > 0:
        # show duplicate investigation
        pass
```


## main_test.txt

```python
from src.core.paint_database import PaintDatabase


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
```

