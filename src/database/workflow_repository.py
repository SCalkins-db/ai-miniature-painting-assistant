from __future__ import annotations

import math
import sqlite3
import sys
from pathlib import Path
from typing import Any

####################################
#pathblock
####################################

if getattr(sys, "frozen", False):
    # PyInstaller bundle location:
    # dist\AI Miniature Painting Assistant\_internal
    PROJECT_ROOT = Path(sys._MEIPASS)
else:
    # Normal source-project location
    PROJECT_ROOT = Path(__file__).resolve().parents[2]

WORKFLOW_DATABASE_PATH = (
    PROJECT_ROOT / "data" / "database" / "painting_assistant.db"
)

PAINT_DATABASE_PATH = (
    PROJECT_ROOT / "database" / "miniature_painting.db"
)



class WorkflowRepository:
    """Read-only access layer for workflow and paint data stored in SQLite."""

    def __init__(
            self,
            workflow_database_path: str | Path = WORKFLOW_DATABASE_PATH,
            paint_database_path: str | Path = PAINT_DATABASE_PATH,
    ) -> None:
        self.workflow_database_path = Path(workflow_database_path)
        self.paint_database_path = Path(paint_database_path)

        if not self.workflow_database_path.exists():
            raise FileNotFoundError(
                f"Workflow database not found: "
                f"{self.workflow_database_path.resolve()}"
            )

        if not self.paint_database_path.exists():
            raise FileNotFoundError(
                f"Paint database not found: "
                f"{self.paint_database_path.resolve()}"
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.workflow_database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _connect_paints(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.paint_database_path)
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
        workflow_sql = """
                       SELECT *
                       FROM workflow_steps
                       WHERE workflow_id = ?
                       ORDER BY area_order, step_order \
                       """

        with self._connect() as connection:
            rows = connection.execute(
                workflow_sql,
                (workflow_id,),
            ).fetchall()

        steps = [dict(row) for row in rows]

        if not steps:
            return []

        paint_sql = """
                    SELECT *
                    FROM paints
                    WHERE LOWER(TRIM(paint_name)) = LOWER(TRIM(?))
                    ORDER BY CASE \
                                 WHEN LOWER(TRIM(status)) = 'active' THEN 0 \
                                 ELSE 1 \
                                 END, \
                             CASE LOWER(TRIM(product_line)) \
                                 WHEN 'base' THEN 0 \
                                 WHEN 'layer' THEN 1 \
                                 WHEN 'shade' THEN 2 \
                                 WHEN 'contrast' THEN 3 \
                                 WHEN 'dry' THEN 4 \
                                 WHEN 'technical' THEN 5 \
                                 WHEN 'spray' THEN 6 \
                                 WHEN 'air' THEN 7 \
                                 ELSE 8 \
                                 END, \
                             paint_id LIMIT 1 \
                    """

        with self._connect_paints() as connection:
            for step in steps:
                paint_name = str(step.get("paint_name") or "").strip()

                step["paint_id"] = ""
                step["paint_hex"] = ""
                step["paint_rgb"] = ""
                step["paint_company"] = ""
                step["paint_brand"] = ""
                step["paint_product_line"] = ""
                step["registry_paint_type"] = ""
                step["paint_status"] = ""
                step["paint_source"] = ""
                step["paint_registry_notes"] = ""

                if not paint_name:
                    continue

                paint_row = connection.execute(
                    paint_sql,
                    (paint_name,),
                ).fetchone()

                if not paint_row:
                    continue

                paint = dict(paint_row)

                step["paint_id"] = paint.get("paint_id", "")
                step["paint_hex"] = paint.get("hex", "")
                step["paint_rgb"] = paint.get("rgb", "")
                step["paint_company"] = paint.get("company", "")
                step["paint_brand"] = paint.get("brand", "")
                step["paint_product_line"] = paint.get("product_line", "")
                step["registry_paint_type"] = paint.get("paint_type", "")
                step["paint_status"] = paint.get("status", "")
                step["paint_source"] = paint.get("source", "")
                step["paint_registry_notes"] = paint.get("notes", "")

        return steps

    def get_paint_details(
        self,
        *,
        paint_id: Any = None,
        paint_name: str | None = None,
    ) -> dict[str, Any] | None:
        with self._connect_paints() as connection:
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
        with self._connect_paints() as connection:
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


    def get_paint_brands(self) -> list[str]:
        """Return distinct paint companies/brands for the paint browser."""
        with self._connect_paints() as connection:
            table_name = self._paint_table_name(connection)
            if not table_name:
                return []
            columns = self._column_map(connection, table_name)
            brand_column = self._first_column(columns, "company", "manufacturer", "brand")
            if not brand_column:
                return []
            quoted_table = self._quote_identifier(table_name)
            quoted_brand = self._quote_identifier(brand_column)
            rows = connection.execute(
                f"""
                SELECT DISTINCT TRIM({quoted_brand}) AS brand
                FROM {quoted_table}
                WHERE {quoted_brand} IS NOT NULL
                  AND TRIM({quoted_brand}) <> ''
                ORDER BY brand COLLATE NOCASE
                """
            ).fetchall()
        return [str(row["brand"]) for row in rows]

    def get_paint_types(self, *, brand: str | None = None) -> list[str]:
        """Return distinct paint types, optionally filtered by company/brand."""
        with self._connect_paints() as connection:
            table_name = self._paint_table_name(connection)
            if not table_name:
                return []
            columns = self._column_map(connection, table_name)
            type_column = self._first_column(columns, "paint_type", "product_line", "type")
            brand_column = self._first_column(columns, "company", "manufacturer", "brand")
            if not type_column:
                return []
            quoted_table = self._quote_identifier(table_name)
            quoted_type = self._quote_identifier(type_column)
            parameters: tuple[Any, ...] = ()
            where = f"{quoted_type} IS NOT NULL AND TRIM({quoted_type}) <> ''"
            if brand and brand_column:
                quoted_brand = self._quote_identifier(brand_column)
                where += f" AND LOWER(TRIM({quoted_brand})) = LOWER(TRIM(?))"
                parameters = (brand,)
            rows = connection.execute(
                f"""
                SELECT DISTINCT TRIM({quoted_type}) AS paint_type
                FROM {quoted_table}
                WHERE {where}
                ORDER BY paint_type COLLATE NOCASE
                """,
                parameters,
            ).fetchall()
        return [str(row["paint_type"]) for row in rows]

    def search_paints(
        self,
        *,
        brand: str | None = None,
        paint_type: str | None = None,
        name_text: str | None = None,
        limit: int = 1500,
    ) -> list[dict[str, Any]]:
        """Return paints for the cascading paint browser."""
        with self._connect_paints() as connection:
            table_name = self._paint_table_name(connection)
            if not table_name:
                return []
            columns = self._column_map(connection, table_name)
            name_column = self._first_column(columns, "paint_name", "name")
            brand_column = self._first_column(columns, "company", "manufacturer", "brand")
            type_column = self._first_column(columns, "paint_type", "product_line", "type")
            if not name_column:
                return []
            quoted_table = self._quote_identifier(table_name)
            quoted_name = self._quote_identifier(name_column)
            clauses = [f"{quoted_name} IS NOT NULL", f"TRIM({quoted_name}) <> ''"]
            parameters: list[Any] = []
            if brand and brand_column:
                quoted_brand = self._quote_identifier(brand_column)
                clauses.append(f"LOWER(TRIM({quoted_brand})) = LOWER(TRIM(?))")
                parameters.append(brand)
            if paint_type and type_column:
                quoted_type = self._quote_identifier(type_column)
                clauses.append(f"LOWER(TRIM({quoted_type})) = LOWER(TRIM(?))")
                parameters.append(paint_type)
            if name_text:
                clauses.append(f"LOWER({quoted_name}) LIKE LOWER(?)")
                parameters.append(f"%{name_text.strip()}%")
            parameters.append(max(1, int(limit)))
            rows = connection.execute(
                f"SELECT * FROM {quoted_table} WHERE {' AND '.join(clauses)} ORDER BY {quoted_name} COLLATE NOCASE LIMIT ?",
                tuple(parameters),
            ).fetchall()
            return [self._normalize_paint_record(dict(row), columns) for row in rows]

    def get_inventory_paints(self) -> list[dict[str, Any]]:
        """Return paints with an owned quantity greater than zero."""
        with self._connect_paints() as connection:
            table_names = self._table_names(connection)
            inventory_tables = [name for name in table_names if "inventory" in name.casefold()]
            if not inventory_tables:
                return []
            table_name = inventory_tables[0]
            columns = self._column_map(connection, table_name)
            paint_id_column = self._first_column(columns, "paint_id")
            paint_name_column = self._first_column(columns, "paint_name", "name")
            quantity_column = self._first_column(columns, "quantity", "inventory_quantity", "owned_quantity", "qty")
            if not quantity_column or (not paint_id_column and not paint_name_column):
                return []
            quoted_table = self._quote_identifier(table_name)
            quoted_quantity = self._quote_identifier(quantity_column)
            rows = connection.execute(
                f"SELECT * FROM {quoted_table} WHERE COALESCE({quoted_quantity}, 0) > 0 ORDER BY {quoted_quantity} DESC"
            ).fetchall()
            results: list[dict[str, Any]] = []
            for row in rows:
                inventory = dict(row)
                paint = self._find_paint_in_connection(
                    connection,
                    paint_id=inventory.get(paint_id_column) if paint_id_column else None,
                    paint_name=inventory.get(paint_name_column) if paint_name_column else None,
                )
                if not paint:
                    continue
                paint["quantity"] = inventory.get(quantity_column)
                results.append(paint)
            results.sort(key=lambda item: str(item.get("paint_name") or "").casefold())
            return results

    def get_near_matches(
        self,
        *,
        paint_id: Any = None,
        paint_name: str | None = None,
        brand: str | None = None,
        limit: int = 12,
    ) -> list[dict[str, Any]]:
        """Calculate closest registry colours and include a readable match percentage."""
        with self._connect_paints() as connection:
            source = self._find_paint_in_connection(
                connection,
                paint_id=paint_id,
                paint_name=paint_name,
            )
            if not source:
                return []
            source_rgb = self._hex_to_rgb(source.get("hex"))
            if source_rgb is None:
                return []

            table_name = self._paint_table_name(connection)
            if not table_name:
                return []
            columns = self._column_map(connection, table_name)
            name_column = self._first_column(columns, "paint_name", "name")
            hex_column = self._first_column(columns, "hex", "hex_value", "hex_code", "colour_hex", "color_hex")
            brand_column = self._first_column(columns, "company", "manufacturer", "brand")
            if not name_column or not hex_column:
                return []

            quoted_table = self._quote_identifier(table_name)
            quoted_hex = self._quote_identifier(hex_column)
            clauses = [f"{quoted_hex} IS NOT NULL", f"TRIM({quoted_hex}) <> ''"]
            parameters: list[Any] = []
            if brand and brand_column:
                quoted_brand = self._quote_identifier(brand_column)
                clauses.append(f"LOWER(TRIM({quoted_brand})) = LOWER(TRIM(?))")
                parameters.append(brand)
            rows = connection.execute(
                f"SELECT * FROM {quoted_table} WHERE {' AND '.join(clauses)}",
                tuple(parameters),
            ).fetchall()

            source_key = str(source.get("paint_id") or "").strip().casefold()
            source_name_key = str(source.get("paint_name") or "").strip().casefold()
            maximum_distance = math.sqrt(3 * (255 ** 2))
            matches: list[dict[str, Any]] = []
            for row in rows:
                record = self._normalize_paint_record(dict(row), columns)
                record_id = str(record.get("paint_id") or "").strip().casefold()
                record_name = str(record.get("paint_name") or "").strip().casefold()
                if (source_key and record_id == source_key) or (not source_key and record_name == source_name_key):
                    continue
                target_rgb = self._hex_to_rgb(record.get("hex"))
                if target_rgb is None:
                    continue
                distance = math.sqrt(sum((a - b) ** 2 for a, b in zip(source_rgb, target_rgb)))
                record["colour_distance"] = distance
                record["match_percentage"] = max(0.0, 100.0 * (1.0 - distance / maximum_distance))
                matches.append(record)

            matches.sort(key=lambda item: (float(item["colour_distance"]), str(item.get("paint_name") or "").casefold()))
            return matches[: max(1, int(limit))]

    def set_inventory_quantity(
        self,
        *,
        paint_id: Any = None,
        paint_name: str | None = None,
        quantity: int,
    ) -> int:
        """Set owned quantity using the existing inventory schema, creating a simple table only if absent."""
        quantity = max(0, int(quantity))
        with self._connect_paints() as connection:
            paint = self._find_paint_in_connection(connection, paint_id=paint_id, paint_name=paint_name)
            if not paint:
                raise ValueError("Paint could not be found in the paint registry.")

            table_names = self._table_names(connection)
            candidates = [name for name in table_names if "inventory" in name.casefold()]
            table_name = candidates[0] if candidates else "inventory"
            if not candidates:
                connection.execute(
                    """CREATE TABLE inventory (
                           paint_id TEXT PRIMARY KEY,
                           paint_name TEXT,
                           quantity INTEGER NOT NULL DEFAULT 0,
                           wishlist INTEGER NOT NULL DEFAULT 0
                       )"""
                )

            columns = self._column_map(connection, table_name)
            paint_id_column = self._first_column(columns, "paint_id")
            paint_name_column = self._first_column(columns, "paint_name", "name")
            quantity_column = self._first_column(columns, "quantity", "inventory_quantity", "owned_quantity", "qty")
            if not quantity_column:
                raise RuntimeError(f"Inventory table '{table_name}' has no supported quantity column.")

            where_column: str | None = None
            where_value: Any = None
            if paint_id_column and paint.get("paint_id") is not None:
                where_column = paint_id_column
                where_value = paint.get("paint_id")
            elif paint_name_column and paint.get("paint_name"):
                where_column = paint_name_column
                where_value = paint.get("paint_name")
            if not where_column:
                raise RuntimeError("Inventory table cannot identify paints by ID or name.")

            quoted_table = self._quote_identifier(table_name)
            quoted_where = self._quote_identifier(where_column)
            quoted_quantity = self._quote_identifier(quantity_column)
            updated = connection.execute(
                f"UPDATE {quoted_table} SET {quoted_quantity} = ? WHERE {quoted_where} = ?",
                (quantity, where_value),
            ).rowcount
            if not updated:
                insert_columns = [where_column, quantity_column]
                insert_values: list[Any] = [where_value, quantity]
                if paint_name_column and paint_name_column != where_column:
                    insert_columns.append(paint_name_column)
                    insert_values.append(paint.get("paint_name"))
                quoted_columns = ", ".join(self._quote_identifier(column) for column in insert_columns)
                placeholders = ", ".join("?" for _ in insert_columns)
                connection.execute(
                    f"INSERT INTO {quoted_table} ({quoted_columns}) VALUES ({placeholders})",
                    tuple(insert_values),
                )
            connection.commit()
        return quantity

    def set_wishlist_quantity(
        self,
        *,
        paint_id: Any = None,
        paint_name: str | None = None,
        quantity: int,
    ) -> int:
        """Set the wishlist quantity using the discovered inventory schema."""
        quantity = max(0, int(quantity))
        with self._connect_paints() as connection:
            paint = self._find_paint_in_connection(connection, paint_id=paint_id, paint_name=paint_name)
            if not paint:
                raise ValueError("Paint could not be found in the paint registry.")

            table_names = self._table_names(connection)
            candidates = [name for name in table_names if "inventory" in name.casefold()]
            table_name = candidates[0] if candidates else "inventory"
            if not candidates:
                connection.execute(
                    """CREATE TABLE inventory (
                           paint_id TEXT PRIMARY KEY,
                           paint_name TEXT,
                           quantity INTEGER NOT NULL DEFAULT 0,
                           wishlist INTEGER NOT NULL DEFAULT 0
                       )"""
                )

            columns = self._column_map(connection, table_name)
            paint_id_column = self._first_column(columns, "paint_id")
            paint_name_column = self._first_column(columns, "paint_name", "name")
            wishlist_column = self._first_column(columns, "wishlist", "on_wishlist", "wishlist_status")
            if not wishlist_column:
                quoted_table = self._quote_identifier(table_name)
                connection.execute(f"ALTER TABLE {quoted_table} ADD COLUMN wishlist INTEGER NOT NULL DEFAULT 0")
                columns = self._column_map(connection, table_name)
                wishlist_column = self._first_column(columns, "wishlist")
            if not wishlist_column:
                raise RuntimeError(f"Inventory table '{table_name}' has no supported wishlist column.")

            where_column: str | None = None
            where_value: Any = None
            if paint_id_column and paint.get("paint_id") is not None:
                where_column = paint_id_column
                where_value = paint.get("paint_id")
            elif paint_name_column and paint.get("paint_name"):
                where_column = paint_name_column
                where_value = paint.get("paint_name")
            if not where_column:
                raise RuntimeError("Inventory table cannot identify paints by ID or name.")

            quoted_table = self._quote_identifier(table_name)
            quoted_where = self._quote_identifier(where_column)
            quoted_wishlist = self._quote_identifier(wishlist_column)
            updated = connection.execute(
                f"UPDATE {quoted_table} SET {quoted_wishlist} = ? WHERE {quoted_where} = ?",
                (quantity, where_value),
            ).rowcount
            if not updated:
                insert_columns = [where_column, wishlist_column]
                insert_values: list[Any] = [where_value, quantity]
                if paint_name_column and paint_name_column != where_column:
                    insert_columns.append(paint_name_column)
                    insert_values.append(paint.get("paint_name"))
                quoted_columns = ", ".join(self._quote_identifier(column) for column in insert_columns)
                placeholders = ", ".join("?" for _ in insert_columns)
                connection.execute(
                    f"INSERT INTO {quoted_table} ({quoted_columns}) VALUES ({placeholders})",
                    tuple(insert_values),
                )
            connection.commit()
        return quantity

    @staticmethod
    def _hex_to_rgb(value: Any) -> tuple[int, int, int] | None:
        if value is None:
            return None
        text = str(value).strip().lstrip("#")
        if len(text) == 3:
            text = "".join(character * 2 for character in text)
        if len(text) != 6:
            return None
        try:
            return tuple(int(text[index:index + 2], 16) for index in (0, 2, 4))  # type: ignore[return-value]
        except ValueError:
            return None

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
