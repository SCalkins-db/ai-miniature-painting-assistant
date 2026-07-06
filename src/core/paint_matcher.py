class PaintMatcher:
    def find_by_paint_id(self, paint_database_df, paint_id):
        matches = paint_database_df[paint_database_df["Paint_ID"] == paint_id]
        return matches.reset_index(drop=True)

    def find_by_name(self, paint_database_df, paint_name):
        matches = paint_database_df[
            paint_database_df["Paint_Name"].str.contains(
                paint_name,
                case=False,
                na=False
            )
        ]
        return matches.reset_index(drop=True)

    def find_same_company(self, paint_database_df, company):
        matches = paint_database_df[
            paint_database_df["Company"].str.contains(
                company,
                case=False,
                na=False
            )
        ]
        return matches.reset_index(drop=True)
