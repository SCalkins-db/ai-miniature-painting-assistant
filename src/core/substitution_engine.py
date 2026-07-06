class SubstitutionEngine:
    def suggest_substitutes(self, missing_paints_df):
        suggestions = []

        for _, row in missing_paints_df.iterrows():
            suggestions.append({
                "Missing_Paint_ID": row["Paint_ID"],
                "Missing_Paint_Name": row["Paint_Name"],
                "Suggested_Substitute": "No substitute available yet",
            })

        return suggestions
