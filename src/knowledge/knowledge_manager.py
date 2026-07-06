from src.knowledge.workflow_catalog_builder import WorkflowCatalogBuilder
from src.knowledge.workflow_state import WorkflowState
from src.knowledge.workflow_history import WorkflowHistory
from src.knowledge.workflow_review import WorkflowReview
from src.knowledge.workflow_merge_engine import WorkflowMergeEngine


# ============================================================
# KNOWLEDGE MANAGER
# ============================================================
#
# PURPOSE
# -------
# Central coordinator for the knowledge acquisition system.
#
# WHY THIS EXISTS
# ---------------
# OCR extraction is messy. The system needs one place that decides:
#
#     Is this new?
#     Is this a duplicate?
#     Should it merge?
#     Should it go to review?
#     Should the known workflow state be updated?
#
# This manager connects the candidate catalog, workflow state,
# merge engine, history log, and review queue.
#
# ============================================================


class KnowledgeManager:
    def __init__(self):
        self.catalog_builder = WorkflowCatalogBuilder()
        self.state = WorkflowState()
        self.history = WorkflowHistory()
        self.review = WorkflowReview()
        self.merge_engine = WorkflowMergeEngine()

    def process_extraction_result(self, extraction_result):
        raw_title = extraction_result.get("raw_title", "")
        resolved_title = extraction_result.get("resolved_title", "")
        workflow_id = extraction_result.get("workflow_id", "")
        source_file = extraction_result.get("source_file", "")
        score = extraction_result.get("score", 0)
        reason = extraction_result.get("reason", "")

        existing_state = self.state.load()
        decision = self.merge_engine.decide(raw_title, existing_state)

        if decision["decision"] == "Merge":
            workflow_key = decision["matched_workflow_key"]

            updated = self.state.upsert(
                workflow_key=workflow_key,
                title=resolved_title or raw_title,
                workflow_id=workflow_id,
                source_file=source_file,
                confidence="High",
                status="Merged",
                notes=decision["reason"],
            )

            self.history.record(
                workflow_key=workflow_key,
                event_type="Merged Extraction",
                new_value=resolved_title or raw_title,
                source_file=source_file,
                notes=decision["reason"],
            )

            return {
                "action": "Merged",
                "workflow_key": workflow_key,
                "state": updated,
                "decision": decision,
            }

        if decision["decision"] == "Review Merge":
            workflow_key = decision["matched_workflow_key"]

            self.review.add(
                workflow_key=workflow_key,
                issue_type="Possible Duplicate",
                issue_detail=decision["reason"],
                source_file=source_file,
            )

            self.history.record(
                workflow_key=workflow_key,
                event_type="Merge Review Needed",
                new_value=raw_title,
                source_file=source_file,
                notes=decision["reason"],
            )

            return {
                "action": "Review Merge",
                "workflow_key": workflow_key,
                "decision": decision,
            }

        workflow_key = self.merge_engine.workflow_key(resolved_title or raw_title)

        candidate = self.catalog_builder.add_or_merge_candidate(
            raw_title=raw_title,
            resolved_title=resolved_title,
            workflow_id=workflow_id,
            source_file=source_file,
            resolver_score=score,
            reason=reason,
        )

        state_row = self.state.upsert(
            workflow_key=workflow_key,
            title=resolved_title or raw_title,
            workflow_id=workflow_id,
            source_file=source_file,
            confidence=candidate.get("confidence", "Very Low"),
            status=candidate.get("status", "Needs Review"),
            notes=reason,
        )

        self.history.record(
            workflow_key=workflow_key,
            event_type="Created Candidate",
            new_value=resolved_title or raw_title,
            source_file=source_file,
            notes=reason,
        )

        if candidate.get("status") in ["Manual Review", "Needs Quick Review"]:
            self.review.add(
                workflow_key=workflow_key,
                issue_type="Low Confidence Candidate",
                issue_detail=reason or "Candidate needs review before trusted import.",
                source_file=source_file,
            )

        return {
            "action": "Created",
            "workflow_key": workflow_key,
            "candidate": candidate,
            "state": state_row,
            "decision": decision,
        }
