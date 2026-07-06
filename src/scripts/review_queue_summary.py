from pathlib import Path
import pandas as pd


REVIEW_QUEUE_PATH = Path("review/review_queue.csv")
IMPORT_LOG_PATH = Path("data/imports/import_log.csv")


def print_file(path, label):
    print("=" * 60)
    print(label)
    print("=" * 60)

    if not path.exists():
        print(f"Missing: {path}")
        return

    df = pd.read_csv(path).fillna("")

    print(f"Rows: {len(df)}")

    if df.empty:
        return

    print("\nStatus counts:")
    if "Status" in df.columns:
        print(df["Status"].value_counts())

    print("\nIssue/file type counts:")
    if "Issue_Type" in df.columns:
        print(df["Issue_Type"].value_counts())
    elif "File_Type" in df.columns:
        print(df["File_Type"].value_counts())

    print("\nLatest 25 rows:")
    print(df.tail(25).to_string(index=False))


def main():
    print_file(REVIEW_QUEUE_PATH, "REVIEW QUEUE")
    print()
    print_file(IMPORT_LOG_PATH, "IMPORT LOG")


if __name__ == "__main__":
    main()