from pathlib import Path
import pandas as pd

from src.knowledge.knowledge_paths import KNOWLEDGE_DIR


# ============================================================
# WORKFLOW METRICS
# ============================================================
#
# PURPOSE
# -------
# Prints a quick dashboard for the knowledge acquisition engine.
#
# WHY THIS EXISTS
# ---------------
# As this project grows, Steve needs one command that answers:
#
#     How many workflows do we know about?
#     How many need review?
#     How many duplicates were prevented?
#     How healthy is the knowledge layer?
#
# ============================================================


FILES = {
    "Workflow State": KNOWLEDGE_DIR / "workflow_state.csv",
    "Workflow History": KNOWLEDGE_DIR / "workflow_history.csv",
    "Workflow Review": KNOWLEDGE_DIR / "workflow_review.csv",
    "Workflow Candidates": KNOWLEDGE_DIR / "workflow_candidates.csv",
}


def count_rows(path):
    if not path.exists():
        return 0

    return len(pd.read_csv(path).fillna(""))


def main():
    print("=" * 60)
    print("KNOWLEDGE ENGINE METRICS")
    print("=" * 60)

    for label, path in FILES.items():
        print(f"{label:<25} {count_rows(path)}")

    review_path = FILES["Workflow Review"]

    if review_path.exists():
        df = pd.read_csv(review_path).fillna("")
        if not df.empty and "Status" in df.columns:
            print("\nReview Status Counts")
            print("-" * 60)
            print(df["Status"].value_counts())

    print("=" * 60)


if __name__ == "__main__":
    main()
