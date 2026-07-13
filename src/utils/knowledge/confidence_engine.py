class ConfidenceEngine:
    def title_confidence(self, raw_title, resolved_title, score):
        if not raw_title:
            return "Very Low"

        if score >= 90:
            return "High"

        if score >= 70:
            return "Medium"

        if score >= 45:
            return "Low"

        return "Very Low"

    def import_status(self, confidence):
        if confidence == "High":
            return "Auto Import"

        if confidence == "Medium":
            return "Needs Quick Review"

        return "Manual Review"
