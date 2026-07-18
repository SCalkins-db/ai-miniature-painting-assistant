"""Import curated workflow workbooks into the project SQLite database.

Expected workbook sheets:
    Workflows
    Workflow Steps
    Paint Audit

Character Notes is ignored when present.
Step_Count, Area_Order, Superfaction, Faction, and blank Notes may be derived automatically.

Run from the project root:
    python -m src.utils.importers.workflow_workbook_importer \
        data/workflows_xlsx/death_guard_box_art_workflows_v1.xlsx

Folder import:
    python -m src.utils.importers.workflow_workbook_importer \
        data/workflows_xlsx --recursive

Dry run:
    python -m src.utils.importers.workflow_workbook_importer \
        data/workflows_xlsx/death_guard_box_art_workflows_v1.xlsx --dry-run
"""

from __future__ import annotations

import argparse
import hashlib
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

from openpyxl import load_workbook

try:
    from src.database.database_manager import DatabaseManager
except ImportError:  # Allows direct execution during isolated testing.
    DatabaseManager = None  # type: ignore[assignment,misc]


REQUIRED_SHEETS = {
    # Step_Count is derived from Workflow Steps and is not required in Excel.
    "Workflows": {"Workflow_ID"},
    "Workflow Steps": {
        "Workflow_ID", "Unit", "Model_Area", "Step_Order",
        "Technique", "Paint_ID", "Paint_Name", "Purpose", "Optional",
    },
    # Character Notes is intentionally ignored by the importer.
    "Paint Audit": {"Paint_ID", "Paint_Name", "Usage_Count", "Brand"},
}


@dataclass(slots=True)
class ImportReport:
    source_file: str
    workbook_hash: str = ""
    workflows: int = 0
    workflow_steps: int = 0
    character_notes: int = 0
    paint_audit_rows: int = 0
    unmatched_paint_ids: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    dry_run: bool = False

    @property
    def total_rows(self) -> int:
        return (
            self.workflows
            + self.workflow_steps
            + self.character_notes
            + self.paint_audit_rows
        )


class WorkbookValidationError(ValueError):
    """Raised when a workbook does not match the curated workbook contract."""


class WorkflowWorkbookImporter:
    """Validate and transactionally import one or more workflow workbooks."""

    def __init__(self, database_path: str | Path | None = None) -> None:
        self.database_path = Path(database_path) if database_path else None
        self.manager = None

        if self.database_path is None:
            if DatabaseManager is None:
                raise RuntimeError(
                    "DatabaseManager could not be imported. Pass --database explicitly "
                    "or run this module from the project root."
                )
            self.manager = DatabaseManager()
            self.manager.initialize()

    def _connect(self) -> sqlite3.Connection:
        if self.manager is not None:
            conn = self.manager.connect()
        else:
            assert self.database_path is not None
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(self.database_path)

        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def import_path(
        self,
        source: str | Path,
        *,
        recursive: bool = False,
        dry_run: bool = False,
    ) -> list[ImportReport]:
        source_path = Path(source)
        workbook_paths = self._discover_workbooks(source_path, recursive=recursive)
        return [self.import_workbook(path, dry_run=dry_run) for path in workbook_paths]

    def import_workbook(
        self,
        workbook_path: str | Path,
        *,
        dry_run: bool = False,
    ) -> ImportReport:
        path = Path(workbook_path)
        if not path.exists():
            raise FileNotFoundError(f"Workflow workbook not found: {path}")
        if path.suffix.lower() != ".xlsx":
            raise ValueError(f"Expected an .xlsx workbook: {path}")

        workbook_hash = self._sha256(path)
        sheets = self._load_and_validate(path)
        report = ImportReport(
            source_file=str(path), workbook_hash=workbook_hash, dry_run=dry_run
        )

        workflow_rows = sheets["Workflows"]
        step_rows = sheets["Workflow Steps"]
        audit_rows = sheets["Paint Audit"]

        self._deduplicate_identical_workflows(workflow_rows)
        self._deduplicate_identical_steps(step_rows)
        self._set_step_counts(workflow_rows, step_rows)

        self._validate_relationships(workflow_rows, step_rows)
        report.workflows = len(workflow_rows)
        report.workflow_steps = len(step_rows)
        report.character_notes = 0
        report.paint_audit_rows = len(audit_rows)

        if dry_run:
            return report

        with self._connect() as conn:
            self._ensure_schema(conn)
            report.unmatched_paint_ids = self._find_unmatched_paint_ids(conn, step_rows)
            if report.unmatched_paint_ids:
                report.warnings.append(
                    f"{len(report.unmatched_paint_ids)} workbook paint IDs do not match "
                    "the current paints table. Paint names were still preserved."
                )

            workflow_ids = [self._text(row["Workflow_ID"]) for row in workflow_rows]

            try:
                conn.execute("BEGIN")
                self._delete_existing_workflows(conn, workflow_ids)
                self._insert_workflows(conn, workflow_rows, path, workbook_hash)
                self._insert_steps(conn, step_rows)
                self._insert_paint_audit(conn, audit_rows, path, workbook_hash)
                self._record_import(conn, report)
                conn.commit()
            except Exception:
                conn.rollback()
                raise

        return report

    @staticmethod
    def _discover_workbooks(source: Path, *, recursive: bool) -> list[Path]:
        if source.is_file():
            return [source]
        if not source.exists():
            raise FileNotFoundError(f"Import source not found: {source}")
        pattern = "**/*.xlsx" if recursive else "*.xlsx"
        paths = sorted(
            path
            for path in source.glob(pattern)
            if not path.name.startswith("~$")
        )
        if not paths:
            raise FileNotFoundError(f"No .xlsx workbooks found under: {source}")
        return paths

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _load_and_validate(self, path: Path) -> dict[str, list[dict[str, Any]]]:
        workbook = load_workbook(path, read_only=True, data_only=True)
        missing_sheets = set(REQUIRED_SHEETS) - set(workbook.sheetnames)
        if missing_sheets:
            raise WorkbookValidationError(
                f"{path.name} is missing sheets: {', '.join(sorted(missing_sheets))}"
            )

        result: dict[str, list[dict[str, Any]]] = {}
        for sheet_name, required_columns in REQUIRED_SHEETS.items():
            worksheet = workbook[sheet_name]
            rows = worksheet.iter_rows(values_only=True)
            try:
                raw_header = next(rows)
            except StopIteration as exc:
                raise WorkbookValidationError(
                    f"{path.name} sheet '{sheet_name}' is empty."
                ) from exc

            raw_headers = [self._text(value) for value in raw_header]
            headers = self._normalize_headers(sheet_name, raw_headers)

            if len(headers) != len(set(headers)):
                duplicates = sorted(
                    header for header in set(headers) if headers.count(header) > 1
                )
                raise WorkbookValidationError(
                    f"{path.name} sheet '{sheet_name}' maps multiple columns to: "
                    f"{', '.join(duplicates)}. Headers were: {raw_headers}"
                )

            recoverable_columns = {
                "Workflow Steps": {"Superfaction", "Area_Order"},
            }
            missing_columns = (
                required_columns
                - set(headers)
                - recoverable_columns.get(sheet_name, set())
            )
            if missing_columns:
                raise WorkbookValidationError(
                    f"{path.name} sheet '{sheet_name}' is missing columns: "
                    f"{', '.join(sorted(missing_columns))}. "
                    f"Headers found: {raw_headers}"
                )

            parsed_rows: list[dict[str, Any]] = []
            for excel_row, values in enumerate(rows, start=2):
                row = dict(zip(headers, values, strict=False))
                if not any(value not in (None, "") for value in row.values()):
                    continue
                row["__excel_row__"] = excel_row
                parsed_rows.append(row)
            result[sheet_name] = parsed_rows

        workbook.close()
        self._normalize_workflow_steps(
            result["Workflow Steps"],
            path,
            result["Workflows"],
        )
        return result

    @classmethod
    def _normalize_headers(
        cls, sheet_name: str, headers: Sequence[str]
    ) -> list[str]:
        """Map legacy or loosely named headers to the canonical importer schema.

        Ordering rules for Workflow Steps:
        - Any header containing both "area" and "order" becomes Area_Order.
        - Any remaining header containing "order" becomes Step_Order.
        - Any remaining header containing "area" becomes Model_Area.
        """
        normalized: list[str] = []
        existing_exact = {header for header in headers if header}

        for header in headers:
            compact = cls._header_key(header)
            canonical = header

            exact_aliases = {
                "workflowid": "Workflow_ID",
                "paintid": "Paint_ID",
                "paintname": "Paint_Name",
                "workflowtype": "Workflow_Type",
                "stepcount": "Step_Count",
                "generalnotes": "General_Notes",
                "sourcebasis": "Source_Basis",
                "paintbrand": "Paint_Brand",
                "usagecount": "Usage_Count",
            }
            canonical = exact_aliases.get(compact, canonical)

            if sheet_name == "Workflow Steps":
                step_aliases = {
                    "modelarea": "Model_Area",
                    "paintarea": "Model_Area",
                    "modelpart": "Model_Area",
                    "section": "Model_Area",
                    "part": "Model_Area",
                    "stepsequence": "Step_Order",
                    "workfloworder": "Step_Order",
                    "paintorder": "Step_Order",
                    "sequence": "Step_Order",
                    "stepnumber": "Step_Order",
                    "stepno": "Step_Order",
                    "modelareaorder": "Area_Order",
                    "areasequence": "Area_Order",
                    "sectionorder": "Area_Order",
                }
                canonical = step_aliases.get(compact, canonical)

                words = set(cls._header_words(header))
                if "area" in words and "order" in words:
                    canonical = "Area_Order"
                elif "order" in words and canonical == header:
                    canonical = "Step_Order"
                elif "area" in words and canonical == header:
                    canonical = "Model_Area"
                elif compact == "order":
                    # A plain Order column is the step sequence unless an exact
                    # Step_Order column already exists; then it fills Area_Order.
                    canonical = (
                        "Area_Order" if "Step_Order" in existing_exact else "Step_Order"
                    )
                elif compact == "area":
                    canonical = "Model_Area"

            normalized.append(canonical)

        return normalized

    @staticmethod
    def _header_key(value: str) -> str:
        return "".join(character.lower() for character in value if character.isalnum())

    @staticmethod
    def _header_words(value: str) -> list[str]:
        cleaned = "".join(
            character.lower() if character.isalnum() else " " for character in value
        )
        return [word for word in cleaned.split() if word]

    def _normalize_workflow_steps(
        self,
        rows: list[dict[str, Any]],
        path: Path,
        workflows: Sequence[dict[str, Any]],
    ) -> None:
        """Fill recoverable legacy columns in Workflow Steps."""
        inferred_superfaction = self._infer_superfaction_from_path(path)
        workflow_lookup = {
            self._text(row.get("Workflow_ID")): row
            for row in workflows
            if self._text(row.get("Workflow_ID"))
        }
        inferred_faction = self._infer_faction_from_path(path)
        area_orders: dict[tuple[str, str], int] = {}
        next_area_order: dict[str, int] = {}

        for row in rows:
            workflow_id = self._text(row.get("Workflow_ID"))
            parent = workflow_lookup.get(workflow_id, {})

            if not self._text(row.get("Faction")):
                row["Faction"] = self._text(parent.get("Faction")) or inferred_faction

            if not self._text(row.get("Unit")):
                row["Unit"] = self._text(parent.get("Unit"))

            if "Notes" not in row or row.get("Notes") is None:
                row["Notes"] = ""

            model_area = self._text(row.get("Model_Area"))

            if not self._text(row.get("Superfaction")):
                row["Superfaction"] = (
                    self._text(parent.get("Superfaction")) or inferred_superfaction
                )

            key = (workflow_id, model_area)
            existing_area_order = row.get("Area_Order")
            if existing_area_order not in (None, ""):
                area_order = self._int(existing_area_order)
                area_orders.setdefault(key, area_order)
                next_area_order[workflow_id] = max(
                    next_area_order.get(workflow_id, 1), area_order + 1
                )
                continue

            if key not in area_orders:
                area_orders[key] = next_area_order.get(workflow_id, 1)
                next_area_order[workflow_id] = area_orders[key] + 1

            row["Area_Order"] = area_orders[key]

    @staticmethod
    def _infer_superfaction_from_path(path: Path) -> str:
        parts = {part.lower() for part in path.parts}
        if "chaos" in parts:
            return "Chaos"
        if "imperium" in parts:
            return "Imperium"
        if "xenos" in parts:
            return "Xenos"
        return ""

    @staticmethod
    def _infer_faction_from_path(path: Path) -> str:
        """Infer a readable faction name from the workbook's parent folder."""
        name = path.parent.name.replace("_", " ").strip()
        return " ".join(word.capitalize() for word in name.split())

    def _deduplicate_identical_workflows(
        self, rows: list[dict[str, Any]]
    ) -> None:
        """Remove exact duplicate workflow rows while rejecting conflicting duplicates."""
        first_by_id: dict[str, dict[str, Any]] = {}
        duplicate_indexes: list[int] = []

        for index, row in enumerate(rows):
            workflow_id = self._required_text(row, "Workflow_ID", "Workflows")
            first = first_by_id.get(workflow_id)
            if first is None:
                first_by_id[workflow_id] = row
                continue

            comparable_first = {
                key: value for key, value in first.items() if key != "__excel_row__"
            }
            comparable_current = {
                key: value for key, value in row.items() if key != "__excel_row__"
            }

            if comparable_first != comparable_current:
                raise WorkbookValidationError(
                    f"Conflicting duplicate Workflow_ID '{workflow_id}' in Workflows "
                    f"rows {first.get('__excel_row__')} and {row.get('__excel_row__')}."
                )

            duplicate_indexes.append(index)

        for index in reversed(duplicate_indexes):
            del rows[index]

    def _deduplicate_identical_steps(
        self, rows: list[dict[str, Any]]
    ) -> None:
        """Remove exact duplicate step rows while rejecting conflicting duplicates."""
        first_by_key: dict[tuple[str, int, int], dict[str, Any]] = {}
        duplicate_indexes: list[int] = []

        for index, row in enumerate(rows):
            workflow_id = self._required_text(row, "Workflow_ID", "Workflow Steps")
            area_order = self._required_int(row, "Area_Order", "Workflow Steps")
            step_order = self._required_int(row, "Step_Order", "Workflow Steps")
            key = (workflow_id, area_order, step_order)
            first = first_by_key.get(key)
            if first is None:
                first_by_key[key] = row
                continue

            comparable_first = {
                name: value for name, value in first.items() if name != "__excel_row__"
            }
            comparable_current = {
                name: value for name, value in row.items() if name != "__excel_row__"
            }

            if comparable_first != comparable_current:
                raise WorkbookValidationError(
                    f"Conflicting duplicate step order {step_order} in area "
                    f"{area_order} for workflow '{workflow_id}' in Workflow Steps rows "
                    f"{first.get('__excel_row__')} and {row.get('__excel_row__')}."
                )

            duplicate_indexes.append(index)

        for index in reversed(duplicate_indexes):
            del rows[index]

    def _set_step_counts(
        self,
        workflows: Sequence[dict[str, Any]],
        steps: Sequence[dict[str, Any]],
    ) -> None:
        """Derive Step_Count from normalized Workflow Steps for every workflow."""
        counts: dict[str, int] = {}
        for row in steps:
            workflow_id = self._required_text(row, "Workflow_ID", "Workflow Steps")
            counts[workflow_id] = counts.get(workflow_id, 0) + 1

        for row in workflows:
            workflow_id = self._required_text(row, "Workflow_ID", "Workflows")
            row["Step_Count"] = counts.get(workflow_id, 0)

    def _validate_relationships(
        self,
        workflows: Sequence[dict[str, Any]],
        steps: Sequence[dict[str, Any]],
    ) -> None:
        workflow_ids: list[str] = []
        for row in workflows:
            workflow_id = self._required_text(row, "Workflow_ID", "Workflows")
            workflow_ids.append(workflow_id)

        duplicates = sorted(
            workflow_id
            for workflow_id in set(workflow_ids)
            if workflow_ids.count(workflow_id) > 1
        )
        if duplicates:
            raise WorkbookValidationError(
                "Duplicate Workflow_ID values in Workflows: " + ", ".join(duplicates[:10])
            )

        valid_ids = set(workflow_ids)
        seen_step_keys: set[tuple[str, int, int]] = set()
        step_counts: dict[str, int] = {workflow_id: 0 for workflow_id in valid_ids}

        for row in steps:
            workflow_id = self._required_text(row, "Workflow_ID", "Workflow Steps")
            if workflow_id not in valid_ids:
                raise WorkbookValidationError(
                    f"Workflow Steps row {row['__excel_row__']} references unknown "
                    f"Workflow_ID '{workflow_id}'."
                )
            area_order = self._required_int(row, "Area_Order", "Workflow Steps")
            step_order = self._required_int(row, "Step_Order", "Workflow Steps")
            key = (workflow_id, area_order, step_order)
            if key in seen_step_keys:
                raise WorkbookValidationError(
                    f"Duplicate step order {step_order} in area {area_order} "
                    f"for workflow '{workflow_id}'."
                )
            seen_step_keys.add(key)
            step_counts[workflow_id] += 1

    def _ensure_schema(self, conn: sqlite3.Connection) -> None:
        # Preserve the project's existing tables, then expand them with workbook fields.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS workflows (
                workflow_id TEXT PRIMARY KEY,
                superfaction TEXT,
                faction TEXT,
                unit TEXT,
                source_file TEXT,
                status TEXT
            )
            """
        )
        self._ensure_columns(
            conn,
            "workflows",
            {
                "subfaction": "TEXT",
                "workflow_type": "TEXT",
                "paint_brand": "TEXT",
                "source_basis": "TEXT",
                "step_count": "INTEGER NOT NULL DEFAULT 0",
                "general_notes": "TEXT",
                "source_hash": "TEXT",
                "imported_at": "TEXT",
            },
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS workflow_steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_id TEXT NOT NULL,
                area_order INTEGER NOT NULL DEFAULT 0,
                step_order INTEGER NOT NULL,
                model_area TEXT,
                technique TEXT,
                paint_id TEXT,
                paint_name TEXT,
                paint_type TEXT,
                purpose TEXT,
                optional INTEGER NOT NULL DEFAULT 0,
                notes TEXT,
                FOREIGN KEY (workflow_id) REFERENCES workflows(workflow_id)
                    ON DELETE CASCADE
            )
            """
        )
        self._ensure_columns(
            conn,
            "workflow_steps",
            {
                "superfaction": "TEXT",
                "faction": "TEXT",
                "unit": "TEXT",
            },
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS character_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_id TEXT NOT NULL,
                unit TEXT,
                note_order INTEGER NOT NULL,
                note TEXT NOT NULL,
                FOREIGN KEY (workflow_id) REFERENCES workflows(workflow_id)
                    ON DELETE CASCADE,
                UNIQUE(workflow_id, note_order)
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS workflow_paint_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_file TEXT NOT NULL,
                source_hash TEXT NOT NULL,
                paint_id TEXT,
                paint_name TEXT NOT NULL,
                usage_count INTEGER NOT NULL DEFAULT 0,
                brand TEXT,
                notes TEXT,
                UNIQUE(source_hash, paint_id, paint_name)
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS workflow_workbook_imports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_file TEXT NOT NULL,
                source_hash TEXT NOT NULL,
                imported_at TEXT NOT NULL,
                workflow_count INTEGER NOT NULL,
                step_count INTEGER NOT NULL,
                note_count INTEGER NOT NULL,
                audit_count INTEGER NOT NULL,
                unmatched_paint_count INTEGER NOT NULL,
                UNIQUE(source_hash)
            )
            """
        )

        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_workflow_steps_order "
            "ON workflow_steps(workflow_id, step_order)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_workflows_faction_unit "
            "ON workflows(faction, unit)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_workflow_steps_workflow "
            "ON workflow_steps(workflow_id, area_order, step_order)"
        )

    @staticmethod
    def _ensure_columns(
        conn: sqlite3.Connection, table_name: str, columns: dict[str, str]
    ) -> None:
        existing = {
            row[1] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        }
        for column_name, column_type in columns.items():
            if column_name not in existing:
                conn.execute(
                    f'ALTER TABLE "{table_name}" ADD COLUMN "{column_name}" {column_type}'
                )

    @staticmethod
    def _delete_existing_workflows(
        conn: sqlite3.Connection, workflow_ids: Sequence[str]
    ) -> None:
        if not workflow_ids:
            return
        placeholders = ",".join("?" for _ in workflow_ids)
        # Explicit deletes support older databases whose FK was not created with CASCADE.
        conn.execute(
            f"DELETE FROM character_notes WHERE workflow_id IN ({placeholders})",
            workflow_ids,
        )
        conn.execute(
            f"DELETE FROM workflow_steps WHERE workflow_id IN ({placeholders})",
            workflow_ids,
        )
        conn.execute(
            f"DELETE FROM workflows WHERE workflow_id IN ({placeholders})",
            workflow_ids,
        )

    def _insert_workflows(
        self,
        conn: sqlite3.Connection,
        rows: Sequence[dict[str, Any]],
        source_path: Path,
        source_hash: str,
    ) -> None:
        imported_at = self._utc_now()
        values = [
            (
                self._text(row.get("Workflow_ID")),
                self._text(row.get("Superfaction")),
                self._text(row.get("Faction")),
                self._text(row.get("Subfaction")),
                self._text(row.get("Unit")),
                self._text(row.get("Workflow_Type")),
                self._text(row.get("Paint_Brand")),
                self._text(row.get("Source_Basis")),
                self._text(row.get("Status")),
                self._int(row.get("Step_Count")),
                self._text(row.get("General_Notes")),
                str(source_path),
                source_hash,
                imported_at,
            )
            for row in rows
        ]
        conn.executemany(
            """
            INSERT INTO workflows (
                workflow_id, superfaction, faction, subfaction, unit,
                workflow_type, paint_brand, source_basis, status, step_count,
                general_notes, source_file, source_hash, imported_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            values,
        )

    def _insert_steps(
        self, conn: sqlite3.Connection, rows: Sequence[dict[str, Any]]
    ) -> None:
        values = [
            (
                self._text(row.get("Workflow_ID")),
                self._text(row.get("Superfaction")),
                self._text(row.get("Faction")),
                self._text(row.get("Unit")),
                self._int(row.get("Area_Order")),
                self._int(row.get("Step_Order")),
                self._text(row.get("Model_Area")),
                self._text(row.get("Technique")),
                self._text(row.get("Paint_ID")),
                self._text(row.get("Paint_Name")),
                "",
                self._text(row.get("Purpose")),
                self._bool_int(row.get("Optional")),
                self._text(row.get("Notes")),
            )
            for row in rows
        ]
        conn.executemany(
            """
            INSERT INTO workflow_steps (
                workflow_id, superfaction, faction, unit, area_order,
                step_order, model_area, technique, paint_id, paint_name,
                paint_type, purpose, optional, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            values,
        )

    def _insert_paint_audit(
        self,
        conn: sqlite3.Connection,
        rows: Sequence[dict[str, Any]],
        source_path: Path,
        source_hash: str,
    ) -> None:
        conn.execute(
            "DELETE FROM workflow_paint_audit WHERE source_hash = ?", (source_hash,)
        )
        conn.executemany(
            """
            INSERT INTO workflow_paint_audit (
                source_file, source_hash, paint_id, paint_name,
                usage_count, brand, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    str(source_path),
                    source_hash,
                    self._text(row.get("Paint_ID")),
                    self._text(row.get("Paint_Name")),
                    self._int(row.get("Usage_Count")),
                    self._text(row.get("Brand")),
                    self._text(row.get("Notes")),
                )
                for row in rows
            ],
        )

    @staticmethod
    def _record_import(conn: sqlite3.Connection, report: ImportReport) -> None:
        conn.execute(
            """
            INSERT INTO workflow_workbook_imports (
                source_file, source_hash, imported_at, workflow_count,
                step_count, note_count, audit_count, unmatched_paint_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_hash) DO UPDATE SET
                source_file = excluded.source_file,
                imported_at = excluded.imported_at,
                workflow_count = excluded.workflow_count,
                step_count = excluded.step_count,
                note_count = excluded.note_count,
                audit_count = excluded.audit_count,
                unmatched_paint_count = excluded.unmatched_paint_count
            """,
            (
                report.source_file,
                report.workbook_hash,
                WorkflowWorkbookImporter._utc_now(),
                report.workflows,
                report.workflow_steps,
                report.character_notes,
                report.paint_audit_rows,
                len(report.unmatched_paint_ids),
            ),
        )

    def _find_unmatched_paint_ids(
        self, conn: sqlite3.Connection, rows: Sequence[dict[str, Any]]
    ) -> list[str]:
        table_names = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        if "paints" not in table_names:
            return []

        paint_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(paints)").fetchall()
        }
        if "paint_id" not in paint_columns:
            return []

        workbook_ids = sorted(
            {
                self._text(row.get("Paint_ID"))
                for row in rows
                if self._text(row.get("Paint_ID"))
            }
        )
        if not workbook_ids:
            return []

        existing: set[str] = set()
        batch_size = 500
        for start in range(0, len(workbook_ids), batch_size):
            batch = workbook_ids[start : start + batch_size]
            placeholders = ",".join("?" for _ in batch)
            existing.update(
                row[0]
                for row in conn.execute(
                    f"SELECT paint_id FROM paints WHERE paint_id IN ({placeholders})",
                    batch,
                ).fetchall()
            )
        return [paint_id for paint_id in workbook_ids if paint_id not in existing]

    @staticmethod
    def _required_text(row: dict[str, Any], key: str, sheet: str) -> str:
        value = WorkflowWorkbookImporter._text(row.get(key))
        if not value:
            raise WorkbookValidationError(
                f"{sheet} row {row.get('__excel_row__')} has no {key}."
            )
        return value

    @staticmethod
    def _required_int(row: dict[str, Any], key: str, sheet: str) -> int:
        value = row.get(key)
        try:
            if value is None or str(value).strip() == "":
                raise ValueError
            return int(value)
        except (TypeError, ValueError) as exc:
            raise WorkbookValidationError(
                f"{sheet} row {row.get('__excel_row__')} has invalid {key}: {value!r}."
            ) from exc

    @staticmethod
    def _text(value: Any) -> str:
        return "" if value is None else str(value).strip()

    @staticmethod
    def _int(value: Any) -> int:
        if value is None or str(value).strip() == "":
            return 0
        return int(value)

    @staticmethod
    def _bool_int(value: Any) -> int:
        if isinstance(value, bool):
            return int(value)
        return int(str(value).strip().lower() in {"1", "true", "yes", "y"})

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _print_report(report: ImportReport) -> None:
    mode = "VALIDATED" if report.dry_run else "IMPORTED"
    print("=" * 72)
    print(f"{mode}: {report.source_file}")
    print(f"Workflows:       {report.workflows:,}")
    print(f"Workflow steps:  {report.workflow_steps:,}")
    print(f"Character notes: {report.character_notes:,}")
    print(f"Paint audit:     {report.paint_audit_rows:,}")
    print(f"Total rows:      {report.total_rows:,}")
    if report.unmatched_paint_ids:
        print(f"Unmatched paint IDs: {len(report.unmatched_paint_ids):,}")
        for paint_id in report.unmatched_paint_ids[:20]:
            print(f"  - {paint_id}")
        if len(report.unmatched_paint_ids) > 20:
            print(f"  ... and {len(report.unmatched_paint_ids) - 20} more")
    for warning in report.warnings:
        print(f"WARNING: {warning}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import curated workflow XLSX workbooks into SQLite."
    )
    parser.add_argument("source", help="Workbook path or directory containing workbooks")
    parser.add_argument(
        "--database",
        help="Optional SQLite path. Omit to use the project's DatabaseManager.",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Recursively import .xlsx files below a directory.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and count rows without changing SQLite.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    importer = WorkflowWorkbookImporter(database_path=args.database)
    reports = importer.import_path(
        args.source, recursive=args.recursive, dry_run=args.dry_run
    )
    for report in reports:
        _print_report(report)
    print("=" * 72)
    print(f"Workbooks processed: {len(reports):,}")
    print(f"Rows processed:      {sum(report.total_rows for report in reports):,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
