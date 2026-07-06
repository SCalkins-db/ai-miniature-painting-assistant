from pathlib import Path

from src.acquisition.workflow_extractor import WorkflowExtractor
from src.acquisition.workflow_csv_writer import WorkflowCSVWriter


IMAGE_DIRS = [
    Path("archive/screenshots"),
    Path("incoming/screenshots"),
    Path("incoming/extracted"),
]


def find_first_image():
    for image_dir in IMAGE_DIRS:
        if not image_dir.exists():
            continue

        for suffix in ["*.png", "*.jpg", "*.jpeg", "*.webp"]:
            matches = list(image_dir.rglob(suffix))
            if matches:
                return matches[0]

    return None


def main():
    print("=" * 60)
    print("WORKFLOW EXTRACTOR TEST")
    print("=" * 60)

    image_path = find_first_image()

    if image_path is None:
        print("No image found.")
        return

    print(f"Testing image: {image_path}")

    extractor = WorkflowExtractor()
    writer = WorkflowCSVWriter()

    result = extractor.extract_from_image(
        image_path=image_path,
        workflow_id="OCR_TEST_WORKFLOW",
    )

    print("\nTITLE:")
    print(result["title"])

    print("\nRAW OCR TEXT:")
    print("-" * 60)
    print(result["raw_text"][:2000])

    print("\nWORKFLOW DATAFRAME:")
    print("-" * 60)
    print(result["workflow_df"])

    output_path = writer.write(
        result["workflow_df"],
        result["workflow_id"],
        result["title"],
    )

    print("\nWROTE:")
    print(output_path)

    print("=" * 60)
    print("WORKFLOW EXTRACTOR TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
