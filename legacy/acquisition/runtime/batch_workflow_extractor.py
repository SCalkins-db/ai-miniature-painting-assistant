from pathlib import Path
import pandas as pd

from src.acquisition.workflow_extractor import WorkflowExtractor
from src.acquisition.workflow_csv_writer import WorkflowCSVWriter
from src.acquisition.workflow_resolver import WorkflowResolver
from src.knowledge.workflow_classifier import WorkflowClassifier

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


class BatchWorkflowExtractor:
    def __init__(self):
        self.extractor = WorkflowExtractor()
        self.writer = WorkflowCSVWriter()
        self.resolver = WorkflowResolver()
        self.classifier = WorkflowClassifier()

    def extract_folder(self, source_dir):
        source_dir = Path(source_dir)

        images = [
            path for path in source_dir.rglob("*")
            if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
        ]

        results = []

        for image_path in sorted(images):
            try:
                temp = self.extractor.extract_from_image(
                    image_path=image_path,
                    workflow_id="UNRESOLVED_WORKFLOW",
                )

                classification = self.classifier.classify(
                    raw_title=temp["title"],
                    raw_text=temp["raw_text"],
                    rows=len(temp["workflow_df"]),
                )

                if classification["action"] == "Ignore":
                    results.append({
                        "source_file": str(image_path),
                        "raw_title": temp["title"],
                        "workflow_id": "",
                        "resolved_title": "",
                        "resolver_status": "Ignored",
                        "page_type": classification["page_type"],
                        "confidence": classification["confidence"],
                        "score": 0,
                        "rows": len(temp["workflow_df"]),
                        "output_path": "",
                        "reason": classification["reason"],
                    })

                    continue

                if classification["action"] == "Needs Review":
                    results.append({
                        "source_file": str(image_path),
                        "raw_title": temp["title"],
                        "workflow_id": "",
                        "resolved_title": "",
                        "resolver_status": "Needs Review",
                        "page_type": classification["page_type"],
                        "confidence": classification["confidence"],
                        "score": 0,
                        "rows": len(temp["workflow_df"]),
                        "output_path": "",
                        "reason": classification["reason"],
                    })

                    continue

                resolved = self.resolver.resolve(
                    raw_title=temp["title"],
                    source_path=str(image_path),
                )

                workflow_id = resolved["workflow_id"] or f"UNRESOLVED_{image_path.stem.upper()}"
                temp["workflow_df"]["Workflow_ID"] = workflow_id
                temp["workflow_df"]["Unit"] = resolved["resolved_title"] or temp["title"]

                output_path = self.writer.write(
                    temp["workflow_df"],
                    workflow_id=workflow_id,
                    title=temp["title"],
                )

                results.append({
                    "source_file": str(image_path),
                    "raw_title": temp["title"],
                    "workflow_id": workflow_id,
                    "resolved_title": resolved["resolved_title"],
                    "resolver_status": resolved["status"],
                    "score": resolved["score"],
                    "rows": len(temp["workflow_df"]),
                    "output_path": str(output_path),
                })

            except Exception as error:
                results.append({
                    "source_file": str(image_path),
                    "raw_title": "",
                    "workflow_id": "",
                    "resolved_title": "",
                    "resolver_status": "Failed",
                    "score": 0,
                    "rows": 0,
                    "output_path": "",
                    "error": str(error),
                })

        return pd.DataFrame(results)
