r"""Load and inspect individual curated painting workflows from XLSX workbooks.

Place this file at:
    src/utils/loaders/workflow_loader.py

Examples from the project root:

Find matching workflows:
    python -m src.utils.loaders.workflow_loader \
        ".\data\workflows" --recursive --search "Primaris Captain"

Load one exact workflow:
    python -m src.utils.loaders.workflow_loader \
        ".\data\workflows" --recursive \
        --workflow-id "IMPERIUM_ULTRAMARINES_PRIMARIS_CAPTAIN"

Return machine-readable JSON:
    python -m src.utils.loaders.workflow_loader \
        ".\data\workflows" --recursive \
        --workflow-id "IMPERIUM_ULTRAMARINES_PRIMARIS_CAPTAIN" --json

This loader deliberately reuses the workbook importer's normalization and
validation rules so loading and importing cannot quietly interpret the same
workbook differently.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

from src.utils.importers.workflow_workbook_importer import (
    WorkflowWorkbookImporter,
    WorkbookValidationError,
)


@dataclass(slots=True, frozen=True)
class WorkflowStep:
    area_order: int
    step_order: int
    model_area: str
    technique: str
    paint_id: str
    paint_name: str
    purpose: str
    optional: bool
    notes: str = ""


@dataclass(slots=True)
class WorkflowArea:
    area_order: int
    model_area: str
    steps: list[WorkflowStep] = field(default_factory=list)


@dataclass(slots=True)
class Workflow:
    workflow_id: str
    superfaction: str
    faction: str
    subfaction: str
    unit: str
    workflow_type: str
    paint_brand: str
    source_basis: str
    status: str
    general_notes: str
    source_file: str
    areas: list[WorkflowArea] = field(default_factory=list)

    @property
    def steps(self) -> list[WorkflowStep]:
        return [step for area in self.areas for step in area.steps]

    @property
    def step_count(self) -> int:
        return len(self.steps)

    @property
    def area_count(self) -> int:
        return len(self.areas)

    @property
    def paints(self) -> list[dict[str, str]]:
        """Return unique paints in first-use order."""
        seen: set[tuple[str, str]] = set()
        paints: list[dict[str, str]] = []

        for step in self.steps:
            key = (step.paint_id.casefold(), step.paint_name.casefold())
            if not step.paint_id and not step.paint_name:
                continue
            if key in seen:
                continue
            seen.add(key)
            paints.append(
                {
                    "paint_id": step.paint_id,
                    "paint_name": step.paint_name,
                }
            )

        return paints

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["step_count"] = self.step_count
        data["area_count"] = self.area_count
        data["paints"] = self.paints
        return data


@dataclass(slots=True, frozen=True)
class WorkflowMatch:
    workflow_id: str
    superfaction: str
    faction: str
    subfaction: str
    unit: str
    workflow_type: str
    step_count: int
    source_file: str


class WorkflowNotFoundError(LookupError):
    """Raised when no workflow matches an exact Workflow_ID."""


class DuplicateWorkflowError(LookupError):
    """Raised when the same Workflow_ID exists in multiple workbooks."""


class WorkflowLoader:
    """Read normalized individual workflows directly from curated workbooks."""

    def __init__(self, source: str | Path, *, recursive: bool = False) -> None:
        self.source = Path(source)
        self.recursive = recursive

        # The normalization methods do not require a database connection.
        # __new__ avoids initializing DatabaseManager merely to read XLSX files.
        self._normalizer = WorkflowWorkbookImporter.__new__(
            WorkflowWorkbookImporter
        )

    def discover_workbooks(self) -> list[Path]:
        return self._normalizer._discover_workbooks(  # noqa: SLF001
            self.source,
            recursive=self.recursive,
        )

    def search(self, query: str = "") -> list[WorkflowMatch]:
        """Search workflow IDs and descriptive metadata across all workbooks."""
        needle = query.strip().casefold()
        matches: list[WorkflowMatch] = []

        for path in self.discover_workbooks():
            sheets = self._load_normalized_sheets(path)
            step_counts = self._count_steps(sheets["Workflow Steps"])

            for row in sheets["Workflows"]:
                searchable = " ".join(
                    self._text(row.get(key))
                    for key in (
                        "Workflow_ID",
                        "Superfaction",
                        "Faction",
                        "Subfaction",
                        "Unit",
                        "Workflow_Type",
                        "Paint_Brand",
                        "Status",
                    )
                ).casefold()

                if needle and needle not in searchable:
                    continue

                workflow_id = self._required(
                    row, "Workflow_ID", path.name, "Workflows"
                )
                matches.append(
                    WorkflowMatch(
                        workflow_id=workflow_id,
                        superfaction=self._text(row.get("Superfaction")),
                        faction=self._text(row.get("Faction")),
                        subfaction=self._text(row.get("Subfaction")),
                        unit=self._text(row.get("Unit")),
                        workflow_type=self._text(row.get("Workflow_Type")),
                        step_count=step_counts.get(workflow_id, 0),
                        source_file=str(path),
                    )
                )

        return sorted(
            matches,
            key=lambda item: (
                item.superfaction.casefold(),
                item.faction.casefold(),
                item.unit.casefold(),
                item.workflow_id.casefold(),
            ),
        )

    def get_workflow(self, workflow_id: str) -> Workflow:
        """Load one exact workflow by Workflow_ID from the source tree."""
        requested = workflow_id.strip()
        if not requested:
            raise ValueError("workflow_id cannot be blank.")

        found: list[Workflow] = []

        for path in self.discover_workbooks():
            sheets = self._load_normalized_sheets(path)
            workflow_rows = [
                row
                for row in sheets["Workflows"]
                if self._text(row.get("Workflow_ID")).casefold()
                == requested.casefold()
            ]

            if not workflow_rows:
                continue

            for row in workflow_rows:
                found.append(
                    self._build_workflow(
                        row,
                        sheets["Workflow Steps"],
                        path,
                    )
                )

        if not found:
            raise WorkflowNotFoundError(
                f"Workflow_ID not found: {requested}"
            )

        if len(found) > 1:
            locations = ", ".join(workflow.source_file for workflow in found)
            raise DuplicateWorkflowError(
                f"Workflow_ID '{requested}' exists in multiple workbooks: "
                f"{locations}"
            )

        return found[0]

    def _load_normalized_sheets(
        self, path: Path
    ) -> dict[str, list[dict[str, Any]]]:
        sheets = self._normalizer._load_and_validate(path)  # noqa: SLF001

        workflows = sheets["Workflows"]
        steps = sheets["Workflow Steps"]

        self._normalizer._deduplicate_identical_workflows(  # noqa: SLF001
            workflows
        )
        self._normalizer._deduplicate_identical_steps(steps)  # noqa: SLF001
        self._normalizer._set_step_counts(workflows, steps)  # noqa: SLF001
        self._normalizer._validate_relationships(workflows, steps)  # noqa: SLF001

        return sheets

    def _build_workflow(
        self,
        workflow_row: dict[str, Any],
        all_steps: Sequence[dict[str, Any]],
        source_path: Path,
    ) -> Workflow:
        workflow_id = self._required(
            workflow_row,
            "Workflow_ID",
            source_path.name,
            "Workflows",
        )

        matching_steps = [
            row
            for row in all_steps
            if self._text(row.get("Workflow_ID")).casefold()
            == workflow_id.casefold()
        ]
        matching_steps.sort(
            key=lambda row: (
                self._integer(row.get("Area_Order")),
                self._integer(row.get("Step_Order")),
                self._integer(row.get("__excel_row__")),
            )
        )

        areas_by_key: dict[tuple[int, str], WorkflowArea] = {}
        for row in matching_steps:
            area_order = self._integer(row.get("Area_Order"))
            model_area = self._required(
                row,
                "Model_Area",
                source_path.name,
                "Workflow Steps",
            )
            key = (area_order, model_area)

            if key not in areas_by_key:
                areas_by_key[key] = WorkflowArea(
                    area_order=area_order,
                    model_area=model_area,
                )

            areas_by_key[key].steps.append(
                WorkflowStep(
                    area_order=area_order,
                    step_order=self._integer(row.get("Step_Order")),
                    model_area=model_area,
                    technique=self._text(row.get("Technique")),
                    paint_id=self._text(row.get("Paint_ID")),
                    paint_name=self._text(row.get("Paint_Name")),
                    purpose=self._text(row.get("Purpose")),
                    optional=self._boolean(row.get("Optional")),
                    notes=self._text(row.get("Notes")),
                )
            )

        areas = sorted(
            areas_by_key.values(),
            key=lambda area: (area.area_order, area.model_area.casefold()),
        )

        return Workflow(
            workflow_id=workflow_id,
            superfaction=(
                self._text(workflow_row.get("Superfaction"))
                or (
                    matching_steps
                    and self._text(matching_steps[0].get("Superfaction"))
                )
                or ""
            ),
            faction=(
                self._text(workflow_row.get("Faction"))
                or (
                    matching_steps
                    and self._text(matching_steps[0].get("Faction"))
                )
                or ""
            ),
            subfaction=self._text(workflow_row.get("Subfaction")),
            unit=(
                self._text(workflow_row.get("Unit"))
                or (
                    matching_steps
                    and self._text(matching_steps[0].get("Unit"))
                )
                or ""
            ),
            workflow_type=self._text(workflow_row.get("Workflow_Type")),
            paint_brand=self._text(workflow_row.get("Paint_Brand")),
            source_basis=self._text(workflow_row.get("Source_Basis")),
            status=self._text(workflow_row.get("Status")),
            general_notes=self._text(workflow_row.get("General_Notes")),
            source_file=str(source_path),
            areas=areas,
        )

    @staticmethod
    def _count_steps(
        steps: Iterable[dict[str, Any]]
    ) -> dict[str, int]:
        counts: dict[str, int] = {}
        for row in steps:
            workflow_id = WorkflowLoader._text(row.get("Workflow_ID"))
            if workflow_id:
                counts[workflow_id] = counts.get(workflow_id, 0) + 1
        return counts

    @staticmethod
    def _required(
        row: dict[str, Any],
        key: str,
        filename: str,
        sheet: str,
    ) -> str:
        value = WorkflowLoader._text(row.get(key))
        if not value:
            raise WorkbookValidationError(
                f"{filename} sheet '{sheet}' row "
                f"{row.get('__excel_row__')} has no {key}."
            )
        return value

    @staticmethod
    def _text(value: Any) -> str:
        return "" if value is None else str(value).strip()

    @staticmethod
    def _integer(value: Any) -> int:
        if value is None or str(value).strip() == "":
            return 0
        return int(value)

    @staticmethod
    def _boolean(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        return str(value).strip().casefold() in {
            "1",
            "true",
            "yes",
            "y",
        }


def _print_search_results(matches: Sequence[WorkflowMatch]) -> None:
    if not matches:
        print("No matching workflows found.")
        return

    print("=" * 100)
    print(f"Matching workflows: {len(matches):,}")
    print("=" * 100)

    for match in matches:
        label = " / ".join(
            value
            for value in (
                match.superfaction,
                match.faction,
                match.subfaction,
                match.unit,
            )
            if value
        )
        print(match.workflow_id)
        print(f"  {label or '(no descriptive metadata)'}")
        print(
            f"  Type: {match.workflow_type or '-'} | "
            f"Steps: {match.step_count:,}"
        )
        print(f"  File: {match.source_file}")
        print("-" * 100)


def _print_workflow(workflow: Workflow) -> None:
    print("=" * 100)
    print(workflow.workflow_id)
    print("=" * 100)

    print(f"Superfaction: {workflow.superfaction or '-'}")
    print(f"Faction:      {workflow.faction or '-'}")
    print(f"Subfaction:   {workflow.subfaction or '-'}")
    print(f"Unit:         {workflow.unit or '-'}")
    print(f"Type:         {workflow.workflow_type or '-'}")
    print(f"Status:       {workflow.status or '-'}")
    print(f"Areas:        {workflow.area_count:,}")
    print(f"Steps:        {workflow.step_count:,}")
    print(f"Unique paints:{len(workflow.paints):,}")
    print(f"Source:       {workflow.source_file}")

    if workflow.general_notes:
        print(f"General notes: {workflow.general_notes}")

    print()
    for area in workflow.areas:
        print(
            f"[Area {area.area_order}] {area.model_area} "
            f"({len(area.steps)} steps)"
        )
        for step in area.steps:
            optional = " [OPTIONAL]" if step.optional else ""
            paint = step.paint_name or step.paint_id or "(no paint)"
            if step.paint_id and step.paint_name:
                paint = f"{step.paint_name} ({step.paint_id})"

            print(
                f"  {step.step_order:>2}. {step.technique or '-'} — "
                f"{paint}{optional}"
            )
            if step.purpose:
                print(f"      Purpose: {step.purpose}")
            if step.notes:
                print(f"      Notes:   {step.notes}")
        print()

    print("Unique paints")
    print("-" * 100)
    for number, paint in enumerate(workflow.paints, start=1):
        paint_name = paint["paint_name"] or "(unnamed paint)"
        paint_id = paint["paint_id"]
        suffix = f" [{paint_id}]" if paint_id else ""
        print(f"{number:>3}. {paint_name}{suffix}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Search for or load one normalized workflow directly from curated "
            "XLSX workbooks."
        )
    )
    parser.add_argument(
        "source",
        help="Workbook path or directory containing workflow workbooks.",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Search subdirectories for .xlsx workbooks.",
    )

    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument(
        "--workflow-id",
        help="Load one exact Workflow_ID, case-insensitively.",
    )
    action.add_argument(
        "--search",
        metavar="TEXT",
        help=(
            "Search Workflow_ID, faction, unit, workflow type, brand, and "
            "status. Use an empty string to list everything."
        ),
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Print JSON instead of the formatted console view.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    loader = WorkflowLoader(args.source, recursive=args.recursive)

    try:
        if args.workflow_id:
            workflow = loader.get_workflow(args.workflow_id)
            if args.json:
                print(json.dumps(workflow.to_dict(), indent=2))
            else:
                _print_workflow(workflow)
            return 0

        matches = loader.search(args.search or "")
        if args.json:
            print(
                json.dumps(
                    [asdict(match) for match in matches],
                    indent=2,
                )
            )
        else:
            _print_search_results(matches)
        return 0

    except (
        FileNotFoundError,
        ValueError,
        WorkbookValidationError,
        WorkflowNotFoundError,
        DuplicateWorkflowError,
    ) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
