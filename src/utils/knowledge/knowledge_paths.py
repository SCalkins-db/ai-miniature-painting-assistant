from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

KNOWLEDGE_DIR = PROJECT_ROOT / "data" / "knowledge"

WORKFLOW_CANDIDATES_PATH = KNOWLEDGE_DIR / "workflow_candidates.csv"
WORKFLOW_MERGE_LOG_PATH = KNOWLEDGE_DIR / "workflow_merge_log.csv"
