from src.core.paint_database import PaintDatabase


def main():
    db = PaintDatabase("data/registries_csv")

    print("=" * 50)
    print("AI Miniature Painting Assistant")
    print("=" * 50)

    print(f"Paints Loaded: {len(db.master_df):,}")

    print("\nPaints by Company:")
    print(db.master_df["Company"].value_counts())

    print("\nSearch Example: Kantor Blue")
    print(db.search_by_paint_name("Kantor Blue"))


if __name__ == "__main__":
    main()
