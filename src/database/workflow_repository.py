from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


DEFAULT_DATABASE_PATH = Path("data/database/painting_assistant.db")


class WorkflowRepository:
    """Read-only access layer for workflow and paint data stored in SQLite."""

    def __init__(self, database_path: str | Path = DEFAULT_DATABASE_PATH) -> None:
        self.database_path = Path(database_path)
        if not self.database_path.exists():
            raise FileNotFoundError(
                f"Workflow database not found: {self.database_path.resolve()}"
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _quote_identifier(identifier: str) -> str:
        return '"' + identifier.replace('"', '""') + '"'

    def _table_names(self, connection: sqlite3.Connection) -> set[str]:
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
        return {str(row["name"]) for row in rows}

    def _column_map(
        self,
        connection: sqlite3.Connection,
        table_name: str,
    ) -> dict[str, str]:
        quoted_table = self._quote_identifier(table_name)
        rows = connection.execute(f"PRAGMA table_info({quoted_table})").fetchall()
        return {str(row["name"]).casefold(): str(row["name"]) for row in rows}

    @staticmethod
    def _first_column(columns: dict[str, str], *candidates: str) -> str | None:
        for candidate in candidates:
            actual = columns.get(candidate.casefold())
            if actual:
                return actual
        return None

    def get_superfactions(self) -> list[str]:
        sql = """
            SELECT DISTINCT superfaction
            FROM workflows
            WHERE superfaction IS NOT NULL
              AND TRIM(superfaction) <> ''
            ORDER BY superfaction
        """
        with self._connect() as connection:
            rows = connection.execute(sql).fetchall()
        return [row["superfaction"] for row in rows]

    def get_factions(self, superfaction: str) -> list[str]:
        sql = """
            SELECT DISTINCT faction
            FROM workflows
            WHERE superfaction = ?
              AND faction IS NOT NULL
              AND TRIM(faction) <> ''
            ORDER BY faction
        """
        with self._connect() as connection:
            rows = connection.execute(sql, (superfaction,)).fetchall()
        return [row["faction"] for row in rows]

    def get_subfactions(self, superfaction: str, faction: str) -> list[str]:
        sql = """
            SELECT DISTINCT subfaction
            FROM workflows
            WHERE superfaction = ?
              AND faction = ?
              AND subfaction IS NOT NULL
              AND TRIM(subfaction) <> ''
            ORDER BY subfaction
        """
        with self._connect() as connection:
            rows = connection.execute(sql, (superfaction, faction)).fetchall()
        return [row["subfaction"] for row in rows]

    def get_units(
        self,
        superfaction: str,
        faction: str,
        subfaction: str = "",
    ) -> list[str]:
        if subfaction:
            sql = """
                SELECT DISTINCT unit
                FROM workflows
                WHERE superfaction = ?
                  AND faction = ?
                  AND subfaction = ?
                  AND unit IS NOT NULL
                  AND TRIM(unit) <> ''
                ORDER BY unit COLLATE NOCASE
            """
            parameters = (superfaction, faction, subfaction)
        else:
            sql = """
                SELECT DISTINCT unit
                FROM workflows
                WHERE superfaction = ?
                  AND faction = ?
                  AND TRIM(COALESCE(subfaction, '')) = ''
                  AND unit IS NOT NULL
                  AND TRIM(unit) <> ''
                ORDER BY unit COLLATE NOCASE
            """
            parameters = (superfaction, faction)

        with self._connect() as connection:
            rows = connection.execute(sql, parameters).fetchall()
        return [row["unit"] for row in rows]

    def get_workflows(
        self,
        superfaction: str,
        faction: str,
        subfaction: str,
        unit: str,
    ) -> list[dict[str, Any]]:
        select_sql = """
            SELECT
                workflow_id,
                superfaction,
                faction,
                subfaction,
                unit,
                workflow_type,
                step_count
            FROM workflows
        """
        if subfaction:
            sql = select_sql + """
                WHERE superfaction = ?
                  AND faction = ?
                  AND subfaction = ?
                  AND unit = ?
                ORDER BY workflow_type, workflow_id
            """
            parameters = (superfaction, faction, subfaction, unit)
        else:
            sql = select_sql + """
                WHERE superfaction = ?
                  AND faction = ?
                  AND TRIM(COALESCE(subfaction, '')) = ''
                  AND unit = ?
                ORDER BY workflow_type, workflow_id
            """
            parameters = (superfaction, faction, unit)

        with self._connect() as connection:
            rows = connection.execute(sql, parameters).fetchall()
        return [dict(row) for row in rows]

    def get_workflow(self, workflow_id: str) -> dict[str, Any] | None:
        sql = "SELECT * FROM workflows WHERE workflow_id = ?"
        with self._connect() as connection:
            row = connection.execute(sql, (workflow_id,)).fetchone()
        return dict(row) if row else None

    def get_workflow_steps(self, workflow_id: str) -> list[dict[str, Any]]:
        """
        Return workflow steps and attach paint metadata when a compatible paint
        table is present. The method degrades cleanly when the schema differs.
        """
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM workflow_steps
                WHERE workflow_id = ?
                ORDER BY area_order, step_order
                """,
                (workflow_id,),
            ).fetchall()
            steps = [dict(row) for row in rows]

            for step in steps:
                paint = self._find_paint_in_connection(
                    connection,
                    paint_id=step.get("paint_id"),
                    paint_name=step.get("paint_name"),
                )
                if paint:
                    step.setdefault("paint_id", paint.get("paint_id"))
                    step["paint_hex"] = paint.get("hex") or paint.get("paint_hex") or ""
                    step["paint_company"] = paint.get("company") or ""
                    step["paint_brand"] = paint.get("brand") or ""
                    step["paint_product_line"] = paint.get("product_line") or ""
                else:
                    step.setdefault("paint_hex", "")

        return steps

    def get_paint_details(
        self,
        *,
        paint_id: Any = None,
        paint_name: str | None = None,
    ) -> dict[str, Any] | None:
        with self._connect() as connection:
            paint = self._find_paint_in_connection(
                connection,
                paint_id=paint_id,
                paint_name=paint_name,
            )
            if not paint:
                return None
            return self._attach_inventory(connection, paint)

    def get_paint_equivalents(
        self,
        *,
        paint_id: Any = None,
        paint_name: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return curated equivalents or near matches from compatible tables."""
        with self._connect() as connection:
            source_paint = self._find_paint_in_connection(
                connection,
                paint_id=paint_id,
                paint_name=paint_name,
            )
            source_id = paint_id or (source_paint or {}).get("paint_id")
            source_name = paint_name or (source_paint or {}).get("paint_name")

            table_names = self._table_names(connection)
            candidate_tables = [
                name
                for name in table_names
                if any(
                    token in name.casefold()
                    for token in ("equivalent", "equivalence", "near_match", "color_match")
                )
            ]

            for table_name in candidate_tables:
                results = self._query_equivalent_table(
                    connection,
                    table_name,
                    source_id=source_id,
                    source_name=source_name,
                )
                if results:
                    return results

        return []

    # ------------------------------------------------------------------
    # Dynamic schema helpers
    # ------------------------------------------------------------------

    def _paint_table_name(self, connection: sqlite3.Connection) -> str | None:
        table_names = self._table_names(connection)
        preferred = (
            "paints",
            "paint_registry",
            "paint_registries",
            "paint_catalog",
            "paint_library",
        )
        for name in preferred:
            if name in table_names:
                return name
        for name in table_names:
            if "paint" in name.casefold() and "workflow" not in name.casefold():
                columns = self._column_map(connection, name)
                if self._first_column(columns, "paint_name", "name"):
                    return name
        return None

    def _find_paint_in_connection(
        self,
        connection: sqlite3.Connection,
        *,
        paint_id: Any = None,
        paint_name: Any = None,
    ) -> dict[str, Any] | None:
        table_name = self._paint_table_name(connection)
        if not table_name:
            return None

        columns = self._column_map(connection, table_name)
        id_column = self._first_column(columns, "paint_id", "id")
        name_column = self._first_column(columns, "paint_name", "name")
        if not id_column and not name_column:
            return None

        quoted_table = self._quote_identifier(table_name)
        row: sqlite3.Row | None = None

        if paint_id is not None and str(paint_id).strip() and id_column:
            quoted_id = self._quote_identifier(id_column)
            row = connection.execute(
                f"SELECT * FROM {quoted_table} WHERE {quoted_id} = ? LIMIT 1",
                (paint_id,),
            ).fetchone()

        if row is None and paint_name and name_column:
            quoted_name = self._quote_identifier(name_column)
            row = connection.execute(
                f"""
                SELECT *
                FROM {quoted_table}
                WHERE LOWER(TRIM({quoted_name})) = LOWER(TRIM(?))
                LIMIT 1
                """,
                (str(paint_name),),
            ).fetchone()

        if row is None:
            return None
        return self._normalize_paint_record(dict(row), columns)

    def _normalize_paint_record(
        self,
        record: dict[str, Any],
        columns: dict[str, str],
    ) -> dict[str, Any]:
        normalized = dict(record)
        aliases = {
            "paint_id": ("paint_id", "id"),
            "company": ("company", "manufacturer"),
            "brand": ("brand",),
            "product_line": ("product_line", "line", "range"),
            "paint_name": ("paint_name", "name"),
            "hex": ("hex", "hex_value", "hex_code", "colour_hex", "color_hex"),
            "rgb": ("rgb", "rgb_value"),
            "paint_type": ("paint_type", "type"),
            "status": ("status",),
            "source": ("source",),
            "notes": ("notes", "note"),
        }
        for standard_name, candidates in aliases.items():
            actual = self._first_column(columns, *candidates)
            if actual:
                normalized[standard_name] = record.get(actual)
        return normalized

    def _attach_inventory(
        self,
        connection: sqlite3.Connection,
        paint: dict[str, Any],
    ) -> dict[str, Any]:
        result = dict(paint)
        table_names = self._table_names(connection)
        inventory_tables = [
            name
            for name in table_names
            if any(token in name.casefold() for token in ("inventory", "wishlist"))
        ]

        for table_name in inventory_tables:
            columns = self._column_map(connection, table_name)
            paint_id_column = self._first_column(columns, "paint_id")
            paint_name_column = self._first_column(columns, "paint_name", "name")
            quantity_column = self._first_column(
                columns,
                "quantity",
                "inventory_quantity",
                "owned_quantity",
                "qty",
            )
            wishlist_column = self._first_column(
                columns,
                "wishlist",
                "on_wishlist",
                "wishlist_status",
            )
            if not quantity_column and not wishlist_column:
                continue

            where_column = None
            where_value = None
            if paint_id_column and paint.get("paint_id") is not None:
                where_column = paint_id_column
                where_value = paint.get("paint_id")
            elif paint_name_column and paint.get("paint_name"):
                where_column = paint_name_column
                where_value = paint.get("paint_name")
            if not where_column:
                continue

            quoted_table = self._quote_identifier(table_name)
            quoted_where = self._quote_identifier(where_column)
            row = connection.execute(
                f"SELECT * FROM {quoted_table} WHERE {quoted_where} = ? LIMIT 1",
                (where_value,),
            ).fetchone()
            if row is None:
                continue

            inventory = dict(row)
            if quantity_column:
                result["quantity"] = inventory.get(quantity_column)
            if wishlist_column:
                result["wishlist"] = inventory.get(wishlist_column)

        return result

    def _query_equivalent_table(
        self,
        connection: sqlite3.Connection,
        table_name: str,
        *,
        source_id: Any,
        source_name: Any,
    ) -> list[dict[str, Any]]:
        columns = self._column_map(connection, table_name)
        source_id_column = self._first_column(
            columns,
            "source_paint_id",
            "paint_id",
            "from_paint_id",
            "base_paint_id",
        )
        source_name_column = self._first_column(
            columns,
            "source_paint_name",
            "paint_name",
            "from_paint_name",
            "base_paint_name",
        )

        target_id_column = self._first_column(
            columns,
            "equivalent_paint_id",
            "target_paint_id",
            "match_paint_id",
            "to_paint_id",
        )
        target_name_column = self._first_column(
            columns,
            "equivalent_paint_name",
            "target_paint_name",
            "match_paint_name",
            "to_paint_name",
        )

        where_column = None
        where_value = None
        if source_id_column and source_id is not None:
            where_column = source_id_column
            where_value = source_id
        elif source_name_column and source_name:
            where_column = source_name_column
            where_value = source_name
        if not where_column:
            return []

        quoted_table = self._quote_identifier(table_name)
        quoted_where = self._quote_identifier(where_column)
        rows = connection.execute(
            f"SELECT * FROM {quoted_table} WHERE {quoted_where} = ? LIMIT 25",
            (where_value,),
        ).fetchall()

        results: list[dict[str, Any]] = []
        for row in rows:
            record = dict(row)
            target_id = record.get(target_id_column) if target_id_column else None
            target_name = record.get(target_name_column) if target_name_column else None
            paint = self._find_paint_in_connection(
                connection,
                paint_id=target_id,
                paint_name=target_name,
            )
            combined = dict(record)
            if paint:
                combined.update(paint)
            elif target_name:
                combined["paint_name"] = target_name
            results.append(combined)
        return results


def main() -> None:
    repository = WorkflowRepository()
    print(repository.get_superfactions())


if __name__ == "__main__":
    main()
