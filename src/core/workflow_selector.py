from src.core.workflow_manager import WorkflowManager


class WorkflowSelector:
    def __init__(self):
        self.manager = WorkflowManager()

    def find(self, superfaction=None, faction=None, unit=None):
        catalog = self.manager.get_catalog()

        if superfaction:
            catalog = catalog[
                catalog["Superfaction"].str.contains(superfaction, case=False, na=False)
            ]

        if faction:
            catalog = catalog[
                catalog["Faction"].str.contains(faction, case=False, na=False)
            ]

        if unit:
            catalog = catalog[
                catalog["Unit"].str.contains(unit, case=False, na=False)
            ]

        return catalog.reset_index(drop=True)

    def first_match(self, superfaction=None, faction=None, unit=None):
        matches = self.find(superfaction=superfaction, faction=faction, unit=unit)

        if matches.empty:
            return None

        return matches.iloc[0]
