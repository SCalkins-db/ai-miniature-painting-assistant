from pathlib import Path
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

WORKFLOW_PATH = (
    PROJECT_ROOT
    / "data"
    / "workflows"
    / "imperium"
    / "ultramarines"
    / "intercessors_test.csv"
)

ROWS = [
    {
        "Workflow_ID": "UM_INTERCESSORS_TEST",
        "Superfaction": "Imperium",
        "Faction": "Ultramarines",
        "Unit": "Intercessors",
        "Model_Area": "Armor",
        "Area_Order": 1,
        "Step_Order": 1,
        "Technique": "Basecoat",
        "Paint_ID": "GW_BASE_MACRAGGE_BLUE",
        "Paint_Name": "Macragge Blue",
        "Purpose": "Main armor",
        "Optional": "No",
        "Notes": "Test",
    },
    {
        "Workflow_ID": "UM_INTERCESSORS_TEST",
        "Superfaction": "Imperium",
        "Faction": "Ultramarines",
        "Unit": "Intercessors",
        "Model_Area": "Armor",
        "Area_Order": 1,
        "Step_Order": 2,
        "Technique": "Shade",
        "Paint_ID": "GW_SHADE_NULN_OIL",
        "Paint_Name": "Nuln Oil",
        "Purpose": "Recess shade",
        "Optional": "No",
        "Notes": "Test",
    },
    {
        "Workflow_ID": "UM_INTERCESSORS_TEST",
        "Superfaction": "Imperium",
        "Faction": "Ultramarines",
        "Unit": "Intercessors",
        "Model_Area": "Armor",
        "Area_Order": 1,
        "Step_Order": 3,
        "Technique": "Highlight",
        "Paint_ID": "GW_LAYER_CALGAR_BLUE",
        "Paint_Name": "Calgar Blue",
        "Purpose": "Edge highlight",
        "Optional": "Yes",
        "Notes": "Test",
    },
]


def main():
    WORKFLOW_PATH.parent.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame(ROWS)
    df.to_csv(WORKFLOW_PATH, index=False)

    print(f"REPAIRED WORKFLOW CSV: {WORKFLOW_PATH}")
    print(df)


if __name__ == "__main__":
    main()