from src.knowledge.workflow_similarity import WorkflowSimilarity, normalize_title


# ============================================================
# WORKFLOW MERGE ENGINE
# ============================================================
#
# PURPOSE
# -------
# Decides whether a new OCR/extraction result should create a new
# workflow candidate, merge into an existing one, or be sent to
# review.
#
# WHY THIS EXISTS
# ---------------
# The Citadel app truncates titles, OCR misreads text, and multiple
# screenshots may describe the same workflow.
#
# Without a merge engine, the project would quickly create duplicate
# workflows such as:
#
#     White Scars Tactical Sq
#     White Scars Tactical Squad
#     White Scars Tactical Sqd
#
# This module prevents that bullshit.
#
# ============================================================


class WorkflowMergeEngine:
    def __init__(self):
        self.similarity = WorkflowSimilarity()

    def workflow_key(self, title):
        normalized = normalize_title(title)
        return normalized.replace(" ", "_").upper() or "UNKNOWN_WORKFLOW"

    def decide(self, raw_title, existing_rows):
        best = None
        best_score = 0

        for row in existing_rows:
            candidate_title = row.get("Best_Title", "")
            score = self.similarity.score(raw_title, candidate_title)

            if score > best_score:
                best = row
                best_score = score

        if best and best_score >= 90:
            return {
                "decision": "Merge",
                "matched_workflow_key": best["Workflow_Key"],
                "score": best_score,
                "reason": "Very high title similarity.",
            }

        if best and best_score >= 75:
            return {
                "decision": "Review Merge",
                "matched_workflow_key": best["Workflow_Key"],
                "score": best_score,
                "reason": "Possible duplicate; needs human review.",
            }

        return {
            "decision": "Create",
            "matched_workflow_key": "",
            "score": best_score,
            "reason": "No strong existing match found.",
        }
