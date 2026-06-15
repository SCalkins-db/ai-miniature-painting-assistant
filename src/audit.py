# Missing Hex Auditing
from src.paint_database import PaintDatabase


db = PaintDatabase("data/registries_csv")

print(db.master_df.shape)
print(db.master_df.columns)
print(db.master_df.head())

missing_hex = db.master_df[
    db.master_df["Hex"].isna() |
    (db.master_df["Hex"].astype(str).str.strip() == "")
]

print("\nMISSING HEX VALUES")
print(
    missing_hex[
        ["Paint_ID", "Company", "Product_Line", "Paint_Name", "Paint_Type", "Status"]
    ]
)

print(f"\nTotal missing Hex: {len(missing_hex)}")

print(db.master_df["Hex"].value_counts(dropna=False).head(20))

print(
    missing_hex["Company"].value_counts()
)

print(
    missing_hex["Product_Line"].value_counts()
)

print(
    missing_hex[
        missing_hex["Company"] == "Army Painter"
    ][
        ["Paint_Name", "Product_Line", "Company"]
    ].head(50)
)