class WorkflowClassifier:
    """
    Classifies OCR/extraction results before the system treats them as real workflows.

    This exists because the Citadel app screenshots include a lot of non-workflow pages:
    title pages, model preview pages, color list pages, basing pages, bottom navigation,
    and random UI screens.

    The extractor can read text from all of those, but not all of them should become
    workflow CSVs.

    This classifier helps decide whether a page is:
    - a usable workflow step page
    - a workflow title page
    - a paint/color list page
    - a basing/technical page
    - junk/navigation
    - needs review
    """

    def classify(self, raw_title="", raw_text="", rows=0):
        raw_title = str(raw_title or "").strip()
        raw_text = str(raw_text or "").lower()

        if not raw_text and rows == 0:
            return self._result("Empty OCR", "Ignore", 0, "No OCR text and no extracted rows.")

        if self._looks_like_navigation(raw_text):
            return self._result("Navigation/UI", "Ignore", 10, "Detected app navigation or UI junk.")

        if self._looks_like_paint_list(raw_text) and rows == 0:
            return self._result("Paint List / Color Page", "Needs Review", 45, "Detected paint/color page but no workflow rows.")

        if self._looks_like_basing(raw_text):
            return self._result("Basing / Technical", "Needs Review", 55, "Detected basing or technical material.")

        if rows >= 3 and self._has_step_language(raw_text):
            return self._result("Workflow Step Page", "Use", 90, "Has multiple extracted rows and step language.")

        if rows > 0:
            return self._result("Partial Workflow Page", "Needs Review", 65, "Has extracted rows but weak step evidence.")

        if raw_title and self._looks_like_title(raw_title):
            return self._result("Workflow Title Page", "Needs Review", 50, "Looks like a workflow title but no steps extracted.")

        return self._result("Unknown", "Needs Review", 25, "Could not confidently classify page.")

    def _has_step_language(self, text):
        return any(term in text for term in [
            "step 1",
            "step 2",
            "undercoat",
            "basecoat",
            "shade",
            "layer",
            "highlight",
            "drybrush",
            "contrast",
        ])

    def _looks_like_navigation(self, text):
        nav_terms = [
            "projects profile",
            "projects",
            "profile",
            "paint colour",
            "citadel colour",
        ]

        return any(term in text for term in nav_terms) and not self._has_step_language(text)

    def _looks_like_paint_list(self, text):
        return any(term in text for term in [
            "colours on this model",
            "colors on this model",
            "paints on this model",
            "recommended colours",
            "recommended colors",
        ])

    def _looks_like_basing(self, text):
        return any(term in text for term in [
            "stirland mud",
            "astrogranite",
            "texture",
            "technical",
            "basing",
            "base rim",
        ])

    def _looks_like_title(self, title):
        lowered = title.lower()

        bad_titles = [
            "unknown workflow",
            "colours on this model",
            "colors on this model",
            "projects profile",
        ]

        if lowered in bad_titles:
            return False

        return len(title) >= 5

    def _result(self, page_type, action, confidence, reason):
        return {
            "page_type": page_type,
            "action": action,
            "confidence": confidence,
            "reason": reason,
        }
