class InventoryChecker:
    def get_owned_paint_ids(self, inventory_df):
        if inventory_df is None or inventory_df.empty:
            return set()

        owned = inventory_df[inventory_df["Owned"] == True]
        return set(owned["Paint_ID"].dropna())

    def check_workflow_inventory(self, workflow_df, inventory_df):
        owned_ids = self.get_owned_paint_ids(inventory_df)

        required = workflow_df[workflow_df["Optional"].str.lower() != "yes"]
        optional = workflow_df[workflow_df["Optional"].str.lower() == "yes"]

        required = required[["Paint_ID", "Paint_Name"]].drop_duplicates()
        optional = optional[["Paint_ID", "Paint_Name"]].drop_duplicates()

        missing_required = required[~required["Paint_ID"].isin(owned_ids)]
        owned_required = required[required["Paint_ID"].isin(owned_ids)]

        return {
            "owned_required": owned_required.reset_index(drop=True),
            "missing_required": missing_required.reset_index(drop=True),
            "optional": optional.reset_index(drop=True),
            "required_count": len(required),
            "owned_required_count": len(owned_required),
            "missing_required_count": len(missing_required),
            "is_paintable": len(missing_required) == 0,
        }
