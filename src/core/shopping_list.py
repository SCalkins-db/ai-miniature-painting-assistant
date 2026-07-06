class ShoppingList:
    def get_required_paints(self, workflow_df):
        required = workflow_df[workflow_df["Optional"].str.lower() != "yes"]
        return required[["Paint_ID", "Paint_Name"]].drop_duplicates()

    def get_missing_paints(self, workflow_df, inventory_df):
        required = self.get_required_paints(workflow_df)

        owned_ids = set(
            inventory_df[inventory_df["Owned"] == True]["Paint_ID"].dropna()
        )

        missing = required[~required["Paint_ID"].isin(owned_ids)]

        return missing.reset_index(drop=True)
