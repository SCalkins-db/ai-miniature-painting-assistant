from pathlib import Path
import pandas as pd

from src.utils.normalization import canonicalize


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
REGISTRY_XLSX_DIR = DATA_DIR / "registries_xlsx"
REPORTS_DIR = DATA_DIR / "reports"

ARMY_FILE = REGISTRY_XLSX_DIR / "Army_Painter_registry_26.0.11_aligned.xlsx"
AUDIT_FILE = REPORTS_DIR / "army_painter_missing_hex_crossref_audit.csv"
OUTPUT_FILE = REGISTRY_XLSX_DIR / "Army_Painter_registry_26.0.12_hex_enriched.xlsx"


def is_blank(value):
    if pd.isna(value):
        return True

    value = str(value).strip()
    return value == "" or value.lower() in {"nan", "none", "null"}


def main():
    if not ARMY_FILE.exists():
        raise FileNotFoundError(f"Army Painter workbook not found: {ARMY_FILE}")

    if not AUDIT_FILE.exists():
        raise FileNotFoundError(f"Audit file not found: {AUDIT_FILE}")

    army_df = pd.read_excel(ARMY_FILE, sheet_name=0)
    audit_df = pd.read_csv(AUDIT_FILE)

    usable_matches = audit_df[
        (audit_df["Match_Source"].astype(str).apply(canonicalize) != canonicalize("No Match Found"))
        & (audit_df["Match_Hex"].notna())
        & (audit_df["Match_RGB"].notna())
    ].copy()

    best_matches = usable_matches.drop_duplicates(subset=["Paint_ID"], keep="first")

    updated_count = 0

    for _, match in best_matches.iterrows():
        paint_id = match["Paint_ID"]

        army_mask = army_df["Paint_ID"].astype(str).str.strip() == str(paint_id).strip()

        if not army_mask.any():
            continue

        current_hex = army_df.loc[army_mask, "Hex"].iloc[0]
        current_rgb = army_df.loc[army_mask, "RGB"].iloc[0]

        if is_blank(current_hex) or is_blank(current_rgb):
            army_df.loc[army_mask, "Hex"] = match["Match_Hex"]
            army_df.loc[army_mask, "RGB"] = match["Match_RGB"]

            note = (
                f"Hex/RGB inferred from {match['Match_Company']} "
                f"{match['Match_Paint_Name']} using {match['Match_Source']}."
            )

            if "Notes" in army_df.columns:
                existing_note = army_df.loc[army_mask, "Notes"].iloc[0]

                if is_blank(existing_note):
                    army_df.loc[army_mask, "Notes"] = note
                else:
                    army_df.loc[army_mask, "Notes"] = str(existing_note) + " | " + note

            updated_count += 1

    summary_df = pd.DataFrame([
        {"Metric": "Army Painter rows", "Value": len(army_df)},
        {"Metric": "Audit rows", "Value": len(audit_df)},
        {"Metric": "Usable matches", "Value": len(usable_matches)},
        {"Metric": "Unique Paint_ID matches used", "Value": len(best_matches)},
        {"Metric": "Rows updated with Hex/RGB", "Value": updated_count},
        {
            "Metric": "Rows still missing Hex/RGB",
            "Value": len(
                army_df[
                    army_df["Hex"].apply(is_blank)
                    | army_df["RGB"].apply(is_blank)
                ]
            ),
        },
    ])

    with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:
        army_df.to_excel(writer, sheet_name="ArmyPainter_All", index=False)
        audit_df.to_excel(writer, sheet_name="Crossref_Audit", index=False)
        summary_df.to_excel(writer, sheet_name="Update_Summary", index=False)

    print("ARMY PAINTER HEX/RGB ENRICHMENT")
    print("--------------------------------")
    print(f"Rows updated: {updated_count}")
    print(f"Output saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
