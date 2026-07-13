from src.knowledge.knowledge_manager import KnowledgeManager


def main():
    print("=" * 60)
    print("KNOWLEDGE ENGINE V2 TEST")
    print("=" * 60)

    manager = KnowledgeManager()

    samples = [
        {
            "raw_title": "White Scars Tactical Sq",
            "resolved_title": "",
            "workflow_id": "UNRESOLVED_IMAGE0",
            "source_file": "archive/screenshots/image0.png",
            "score": 9,
            "reason": "Partial OCR title",
        },
        {
            "raw_title": "White Scars Tactical Squad",
            "resolved_title": "White Scars Tactical Squad",
            "workflow_id": "GW_WHITE_SCARS_TACTICAL_SQUAD",
            "source_file": "archive/screenshots/image999.png",
            "score": 95,
            "reason": "Full title found later",
        },
    ]

    for sample in samples:
        print("\nPROCESSING:")
        print(sample["raw_title"])

        result = manager.process_extraction_result(sample)
        print(result)

    print("=" * 60)
    print("KNOWLEDGE ENGINE V2 TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
