from src.acquisition.workflow_resolver import WorkflowResolver


TEST_CASES = [
    {
        "raw_title": "White Scars Tactical Sq",
        "source_path": "archive/screenshots/imperials/image0.png",
    },
    {
        "raw_title": "Ultramarines Assault Inter...",
        "source_path": "archive/screenshots/imperium/ultramarines/image10.png",
    },
    {
        "raw_title": "Space Wolves Redemptor",
        "source_path": "archive/screenshots/space_wolves/image20.png",
    },
]


def main():
    print("=" * 60)
    print("WORKFLOW RESOLVER TEST")
    print("=" * 60)

    resolver = WorkflowResolver()

    print(f"Catalog rows: {len(resolver.catalog)}")

    for case in TEST_CASES:
        print("\nRAW TITLE:")
        print(case["raw_title"])

        result = resolver.resolve(
            raw_title=case["raw_title"],
            source_path=case["source_path"],
        )

        print("RESULT:")
        for key, value in result.items():
            print(f"{key}: {value}")

    print("=" * 60)
    print("WORKFLOW RESOLVER TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
