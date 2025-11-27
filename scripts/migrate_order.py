#!/usr/bin/env python3
"""
Migration script: sync missing columns from Order model to DB table.
- Adds any missing columns declared in the SQLAlchemy model.
- Safe type widening when applicable.
"""

import sys
from pathlib import Path

# Ensure project root on path BEFORE importing app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from typing import Dict, Tuple, Optional

from loguru import logger
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.sql.schema import Column
from sqlalchemy.sql.type_api import TypeEngine

from app.database import engine
from app.models import Order


TABLE_NAME = Order.__tablename__
DIALECT = engine.dialect


def _compile_type(col_type: TypeEngine) -> str:
    return col_type.compile(dialect=DIALECT)


def _load_existing_columns(conn: Connection) -> Dict[str, Dict[str, Optional[str]]]:
    rows = conn.execute(
        text(
            """
            SELECT
                column_name,
                data_type,
                udt_name,
                is_nullable,
                character_maximum_length,
                numeric_precision,
                numeric_scale
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = :t
            """
        ),
        {"t": TABLE_NAME},
    ).fetchall()

    existing: Dict[str, Dict[str, Optional[str]]] = {}
    for r in rows:
        name = r.column_name

        if r.data_type == "numeric" and r.numeric_precision:
            typ = f"numeric({r.numeric_precision},{r.numeric_scale})"
        elif r.data_type in ("character varying", "varchar") and r.character_maximum_length:
            typ = f"varchar({r.character_maximum_length})"
        elif r.data_type == "timestamp with time zone":
            typ = "timestamp with time zone"
        elif r.data_type == "timestamp without time zone":
            typ = "timestamp without time zone"
        else:
            typ = (r.udt_name or r.data_type or "").lower()

        existing[name] = {"type": typ.lower(), "is_nullable": r.is_nullable}

    return existing


def _model_columns() -> Dict[str, Column]:
    return {c.name: c for c in Order.__table__.columns}


def _nullability_clause(col: Column) -> str:
    return "NULL"


def _default_literal(col: Column) -> Optional[str]:
    d = col.default.arg if col.default is not None else None
    if d is None:
        return None

    if isinstance(d, (int, float)):
        return str(d)
    if isinstance(d, str):
        return f"'{d}'"

    from datetime import datetime

    if callable(d):
        if col.type.__class__.__name__.lower().startswith("datetime"):
            return "NOW()"

    if isinstance(d, datetime):
        return "NOW()"

    return None


def _fallback_literal_for_type(col: Column) -> Optional[str]:
    t = _compile_type(col.type).lower()
    if "int" in t or t.startswith("numeric"):
        return "0"
    if "timestamp" in t:
        return "NOW()"
    if "char" in t or "text" in t:
        return "''"
    return None


def _safe_widen_type_sql(col_name: str, model_type_sql: str, existing_type_sql: str) -> Optional[str]:
    if existing_type_sql in ("int4", "integer") and model_type_sql.startswith("numeric"):
        return (
            f'ALTER TABLE "{TABLE_NAME}" ALTER COLUMN "{col_name}" '
            f'TYPE {model_type_sql} USING "{col_name}"::{model_type_sql};'
        )

    if existing_type_sql.startswith("varchar(") and model_type_sql == "text":
        return (
            f'ALTER TABLE "{TABLE_NAME}" ALTER COLUMN "{col_name}" TYPE text;'
        )

    return None


def migrate():
    logger.info(f"🚀 Starting migration: table '{TABLE_NAME}'")

    with engine.connect() as conn:
        existing = _load_existing_columns(conn)
        model_cols = _model_columns()

        logger.info(f"Existing columns: {sorted(existing.keys())}")

        to_add: Dict[str, Tuple[Column, str]] = {}
        to_alter_type: Dict[str, Tuple[str, str]] = {}

        for name, col in model_cols.items():
            model_type_sql = _compile_type(col.type).lower()

            if name not in existing:
                to_add[name] = (col, model_type_sql)
            else:
                ex_type_sql = (existing[name].get("type") or "").lower()

                if ex_type_sql and ex_type_sql != model_type_sql:
                    widen_sql = _safe_widen_type_sql(name, model_type_sql, ex_type_sql)
                    if widen_sql:
                        to_alter_type[name] = (ex_type_sql, model_type_sql)

        for name, (col, model_type_sql) in to_add.items():
            logger.info(f"➕ Adding column: {name} {model_type_sql}")

            add_sql = (
                f'ALTER TABLE "{TABLE_NAME}" ADD COLUMN "{name}" '
                f"{model_type_sql} {_nullability_clause(col)};"
            )
            conn.execute(text(add_sql))

            if col.nullable is False:
                literal = _default_literal(col) or _fallback_literal_for_type(col)

                if literal is None:
                    logger.warning(
                        f'Column "{name}" is NOT NULL but no default found. Keeping NULLABLE.'
                    )
                else:
                    logger.info(f'   Filling NULLs in "{name}" with {literal}')
                    conn.execute(
                        text(
                            f'UPDATE "{TABLE_NAME}" SET "{name}" = {literal} '
                            f'WHERE "{name}" IS NULL;'
                        )
                    )
                    logger.info(f'   Setting NOT NULL on "{name}"')
                    conn.execute(
                        text(
                            f'ALTER TABLE "{TABLE_NAME}" ALTER COLUMN "{name}" SET NOT NULL;'
                        )
                    )

        for name, (old_t, new_t) in to_alter_type.items():
            widen_sql = _safe_widen_type_sql(name, new_t, old_t)
            if widen_sql:
                logger.info(f'🔧 Altering type: "{name}" {old_t} -> {new_t}')
                conn.execute(text(widen_sql))

        conn.commit()

    logger.info("✅ Migration completed.")


if __name__ == "__main__":
    migrate()
