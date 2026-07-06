from src.acquisition.batch_workflow_extractor import BatchWorkflowExtractor


def main():
    print("=" * 60)
    print("ACQUISITION PIPELINE TEST")
    print("=" * 60)

    extractor = BatchWorkflowExtractor()
    df = extractor.extract_folder("archive/screenshots")

    print(df.head(20).to_string(index=False))
    print(f"\nRows: {len(df)}")

    print("=" * 60)
    print("ACQUISITION PIPELINE TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
