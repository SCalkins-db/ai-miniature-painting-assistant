from src.core.paint_database import PaintDatabase


def main():
    db = PaintDatabase("data/registries_csv")

    df = db.master_df

    print("=" * 60)
    print("DATABASE AUDIT")
    print("=" * 60)

    print(f"\nTotal Paints: {len(df):,}")

    print("\nPaints by Company")
    print(df["Company"].value_counts())

    print("\nMissing Hex")
    print(df["Hex"].isna().sum())

    print("\nMissing RGB")
    print(df["RGB"].isna().sum())

    print("\nDuplicate Paint_ID")
    print(df["Paint_ID"].duplicated().sum())

    print("\nDuplicate Canonical_Paint_Key")
    print(df["Canonical_Paint_Key"].duplicated().sum())

    print("\nDuplicate Canonical_Search_Key")
    print(df["Canonical_Search_Key"].duplicated().sum())

    print("\nSample Duplicate Paint_ID Rows")
    duplicate_ids = df[df["Paint_ID"].duplicated(keep=False)]
    print(
        duplicate_ids[
            ["Paint_ID", "Company", "Brand", "Product_Line", "Paint_Name", "Registry_File"]
        ]
        .sort_values("Paint_ID")
        .head(40)
    )

    print("\nSample Duplicate Canonical_Paint_Key Rows")
    duplicate_keys = df[df["Canonical_Paint_Key"].duplicated(keep=False)]
    print(
        duplicate_keys[
            ["Canonical_Paint_Key", "Company", "Brand", "Product_Line", "Paint_Name", "Registry_File"]
        ]
        .sort_values("Canonical_Paint_Key")
        .head(40)
    )


if __name__ == "__main__":
    main()