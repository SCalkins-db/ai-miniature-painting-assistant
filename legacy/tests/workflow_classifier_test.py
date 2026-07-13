from src.knowledge.workflow_classifier import WorkflowClassifier


def main():
    print("=" * 60)
    print("WORKFLOW CLASSIFIER TEST")
    print("=" * 60)

    classifier = WorkflowClassifier()

    samples = [
        {
            "raw_title": "White Scars Tactical Sq",
            "raw_text": """
            Step 1 - Undercoat
            White Scar
            Undercoat All areas
            Step 2 - Basecoat
            Leadbelcher
            Basecoat Gunmetal areas
            """,
            "rows": 7,
        },
        {
            "raw_title": "Colours On This Model",
            "raw_text": "Colours On This Model Macragge Blue Nuln Oil Calgar Blue",
            "rows": 0,
        },
        {
            "raw_title": "Stirland Mud",
            "raw_text": "Stirland Mud Technical Texture Basing",
            "rows": 6,
        },
        {
            "raw_title": "Projects Profile",
            "raw_text": "Projects Profile",
            "rows": 0,
        },
    ]

    for sample in samples:
        print("\nSAMPLE:")
        print(sample["raw_title"])

        result = classifier.classify(
            raw_title=sample["raw_title"],
            raw_text=sample["raw_text"],
            rows=sample["rows"],
        )

        print("RESULT:")
        for key, value in result.items():
            print(f"{key}: {value}")

    print("=" * 60)
    print("WORKFLOW CLASSIFIER TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
