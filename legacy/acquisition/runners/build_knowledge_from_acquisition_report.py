from pathlib import Path
import pandas as pd

from src.knowledge.knowledge_manager import KnowledgeManager


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = PROJECT_ROOT / "exports" / "reports" / "acquisition_pipeline_report.csv"


def main():
    print("=" * 60)
    print("BUILDING KNOWLEDGE FROM ACQUISITION REPORT")
    print("=" * 60)

    if not REPORT_PATH.exists():
        print(f"Missing report: {REPORT_PATH}")
        print("Run acquisition pipeline or acquisition pipeline test first.")
        return

    df = pd.read_csv(REPORT_PATH).fillna("")
    manager = KnowledgeManager()

    added = 0
    duplicates = 0

    for _, row in df.iterrows():
        result = manager.process_extraction_result({
            "raw_title": row.get("raw_title", ""),
            "resolved_title": row.get("resolved_title", ""),
            "workflow_id": row.get("workflow_id", ""),
            "source_file": row.get("source_file", ""),
            "score": int(row.get("score", 0) or 0),
            "reason": row.get("resolver_status", ""),
        })

        if result["action"] == "Added Candidate":
            added += 1
        else:
            duplicates += 1

    print(f"Rows processed: {len(df)}")
    print(f"Candidates added: {added}")
    print(f"Duplicates skipped: {duplicates}")
    print("=" * 60)
    print("Wrote:")
    print("data/knowledge/workflow_candidates.csv")
    print("=" * 60)


if __name__ == "__main__":
    main()
