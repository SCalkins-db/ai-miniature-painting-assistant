from src.core.inventory import InventoryManager
from src.core.paint_database import PaintDatabase


def main():
    db = PaintDatabase("data/registries_csv")
    inventory = InventoryManager()

    print("ADDING PAINTS")
    inventory.add_paint("GW_BASE_ABADDON_BLACK", qty=3)
    inventory.add_paint("AP_SPEEDPAINT_BLOOD_RED", qty=1)
    inventory.add_paint("VAL_GAME_COLOR_IMPERIAL_BLUE", qty=2)
    inventory.add_paint("GW_BASE_KANTOR_BLUE", qty=3)

    print("\nADDING WISHLIST")
    inventory.add_to_wishlist("GW_SHADE_NULN_OIL")
    inventory.add_to_wishlist("AP_FANATIC_MATT_WHITE")

    print("\nHAS PAINT")
    print("Kantor Blue:", inventory.has_paint("GW_BASE_KANTOR_BLUE"))
    print("Nuln Oil:", inventory.has_paint("GW_SHADE_NULN_OIL"))

    print("\nREMOVE PAINT TEST")
    inventory.remove_paint("GW_BASE_KANTOR_BLUE")
    print("Kantor Blue after remove:", inventory.has_paint("GW_BASE_KANTOR_BLUE"))

    print("\nADD BACK TEST")
    inventory.add_paint("GW_BASE_KANTOR_BLUE", qty=3)
    print("Kantor Blue after add back:", inventory.has_paint("GW_BASE_KANTOR_BLUE"))

    print("\nREMOVE FROM WISHLIST TEST")
    inventory.remove_from_wishlist("AP_FANATIC_MATT_WHITE")
    print(inventory.inventory_df)

    print("\nADD BACK TO WISHLIST")
    inventory.add_to_wishlist("AP_FANATIC_MATT_WHITE")

    print("\nOWNED DETAILS")
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
    print(inventory.filter_inventory(db.master_df, "Paint_Type", "Speedpaint"))

    print("\nFILTER: Base")
    print(inventory.filter_inventory(db.master_df, "Product_Line", "Base"))

    print("\nINVALID INVENTORY IDS")
    print(inventory.validate_inventory_ids(db.master_df))

    print("\nMISSING PAINTS FROM RECIPE")
    recipe_paints = [
        "GW_BASE_ABADDON_BLACK",
        "GW_SHADE_NULN_OIL",
        "GW_LAYER_EVIL_SUNZ_SCARLET",
        "AP_SPEEDPAINT_BLOOD_RED",
    ]

    print(inventory.get_missing_paints(recipe_paints))


if __name__ == "__main__":
    main()