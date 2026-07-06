import pandas as pd


class WorkflowValidator:
    REQUIRED_COLUMNS = [
        "Workflow_ID",
        "Superfaction",
        "Faction",
        "Unit",
        "Model_Area",
        "Area_Order",
        "Step_Order",
        "Technique",
        "Paint_ID",
        "Paint_Name",
        "Purpose",
        "Optional",
        "Notes",
    ]

    def validate_columns(self, workflow_df):
        missing = [c for c in self.REQUIRED_COLUMNS if c not in workflow_df.columns]
        return len(missing) == 0, missing

    def validate_required_values(self, workflow_df):
        required = [
            "Workflow_ID",
            "Faction",
            "Unit",
            "Model_Area",
            "Area_Order",
            "Step_Order",
            "Technique",
        ]

        errors = []

        for field in required:
            if workflow_df[field].isna().any():
                errors.append(f"Missing values in required field: {field}")

        return errors

    def validate_area_order(self, workflow_df):
        errors = []
        area_orders = workflow_df["Area_Order"].tolist()

        if area_orders != sorted(area_orders):
            errors.append("Area_Order is not sorted correctly.")

        return errors

    def validate_step_order(self, workflow_df):
        errors = []

        for model_area, group in workflow_df.groupby("Model_Area"):
            steps = group["Step_Order"].tolist()

            if steps != sorted(steps):
                errors.append(f"Step_Order is not sorted correctly for Model_Area: {model_area}")

        return errors

    def validate_workflow(self, workflow_df):
        errors = []

        columns_valid, missing_columns = self.validate_columns(workflow_df)

        if not columns_valid:
            return False, [f"Missing required columns: {missing_columns}"]

        errors.extend(self.validate_required_values(workflow_df))
        errors.extend(self.validate_area_order(workflow_df))
        errors.extend(self.validate_step_order(workflow_df))

        return len(errors) == 0, errors
