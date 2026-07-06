class RecommendationFormatter:
    def format_recommendation(self, result):
        workflow_id = result["workflow_id"]
        missing = result["missing_paints"]
        substitutes = result["substitutes"]

        lines = []
        lines.append(f"Workflow: {workflow_id}")
        lines.append("")

        if missing.empty:
            lines.append("Required paints: COMPLETE")
            lines.append("Shopping list: Nothing needed")
        else:
            lines.append("Missing required paints:")

            for _, row in missing.iterrows():
                lines.append(f"- {row['Paint_Name']} ({row['Paint_ID']})")

        lines.append("")

        if substitutes:
            lines.append("Substitution suggestions:")

            for suggestion in substitutes:
                lines.append(
                    f"- {suggestion['Missing_Paint_Name']}: "
                    f"{suggestion['Suggested_Substitute']}"
                )
        else:
            lines.append("Substitution suggestions: None needed")

        return "\n".join(lines)
