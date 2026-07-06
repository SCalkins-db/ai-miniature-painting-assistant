

# -------------------------------------------------
# Project Root
# -------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

WORKFLOW_ROOT = PROJECT_ROOT / "data" / "workflows"

# -------------------------------------------------
# Folder Tree
# -------------------------------------------------

WORKFLOW_TREE = {

    "imperium": [

        "ultramarines",
        "white_scars",
        "imperial_fists",
        "dark_angels",
        "blood_angels",
        "space_wolves",
        "raven_guard",
        "black_templars",
        "salamanders",
        "iron_hands",
        "deathwatch",
        "grey_knights",
        "adeptus_custodes",
        "adeptus_mechanicus",
        "adepta_sororitas",
        "astra_militarum",
        "imperial_knights",
        "agents_of_the_imperium",
    ],

    "chaos": [

        "black_legion",
        "death_guard",
        "thousand_sons",
        "world_eaters",
        "emperors_children",
        "night_lords",
        "iron_warriors",
        "word_bearers",
        "alpha_legion",
        "chaos_daemons",
    ],

    "xenos": [

        "tyranids",
        "orks",
        "necrons",
        "aeldari",
        "drukhari",
        "tau_empire",
        "genestealer_cults",
        "leagues_of_votann",
    ]
}


# -------------------------------------------------
# Main
# -------------------------------------------------

def main():

    print("=" * 50)
    print("Creating Workflow Directory Structure")
    print("=" * 50)

    WORKFLOW_ROOT.mkdir(parents=True, exist_ok=True)

    folder_count = 0

    for superfaction, factions in WORKFLOW_TREE.items():

        superfaction_path = WORKFLOW_ROOT / superfaction
        superfaction_path.mkdir(exist_ok=True)

        print(f"\n[{superfaction.upper()}]")

        for faction in factions:

            faction_path = superfaction_path / faction
            faction_path.mkdir(exist_ok=True)

            print(f"  ✓ {faction}")

            folder_count += 1

    print("\n" + "=" * 50)
    print(f"Created {folder_count} faction folders.")
    print(f"Root: {WORKFLOW_ROOT}")
    print("=" * 50)


if __name__ == "__main__":
    main()