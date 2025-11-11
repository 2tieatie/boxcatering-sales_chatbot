#!/usr/bin/env python3
"""
Migration script: sync missing columns from AssortmentItem model to DB table.
- Adds any missing columns declared in the SQLAlchemy model.
- Optionally performs safe type widening (e.g., INTEGER -> NUMERIC(10,2) for `weight`).
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
from app.models import AssortmentItem


TABLE_NAME = AssortmentItem.__tablename__
DIALECT = engine.dialect


def _compile_type(col_type: TypeEngine) -> str:
    """Compile SQLAlchemy type to DB-specific DDL fragment."""
    return col_type.compile(dialect=DIALECT)


def _load_existing_columns(conn: Connection) -> Dict[str, Dict[str, Optional[str]]]:
    """
    Return existing columns info from information_schema.
    Keys: column_name -> dict with raw fields including a normalized type string.
    """
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
        # Build a human-ish normalized type label for comparison
        if r.data_type == "numeric" and r.numeric_precision is not None:
            typ = f"numeric({r.numeric_precision},{r.numeric_scale})"
        elif (
            r.data_type in ("character varying", "varchar")
            and r.character_maximum_length
        ):
            typ = f"varchar({r.character_maximum_length})"
        elif r.data_type == "timestamp with time zone":
            typ = "timestamp with time zone"
        elif r.data_type == "timestamp without time zone":
            typ = "timestamp without time zone"
        else:
            # Fallback: prefer udt_name when available (e.g., int4, text)
            typ = (r.udt_name or r.data_type or "").lower()

        existing[name] = {
            "type": str(typ).lower(),
            "is_nullable": r.is_nullable,
        }
    return existing


def _model_columns() -> Dict[str, Column]:
    """Return model columns excluding implicit SA internals."""
    return {c.name: c for c in AssortmentItem.__table__.columns}


def _nullability_clause(col: Column) -> str:
    # Добавлять NOT NULL опасно на уже заполненных таблицах.
    # Стратегия: создаём как NULLABLE, потом — при необходимости — заполняем и ужесточаем.
    return "NULL"


def _default_literal(col: Column) -> Optional[str]:
    """
    Try to produce a SQL literal for default filling step (Python defaults only).
    We DON'T set server defaults here; we just use a one-off UPDATE.
    """
    d = col.default.arg if col.default is not None else None
    if d is None:
        return None

    # Простые случаи — числа и строки
    if isinstance(d, (int, float)):
        return str(d)
    if isinstance(d, str):
        return f"'{d}'"
    # Date/time defaults like datetime.utcnow — выполним через NOW()
    from datetime import datetime

    if callable(d):
        # если это datetime.utcnow и тип — дата/время
        if col.type.__class__.__name__.lower().startswith("datetime"):
            return "NOW()"
    if isinstance(d, datetime):
        return "NOW()"
    return None


def _fallback_literal_for_type(col: Column) -> Optional[str]:
    """Fallback значение, если нет понятного default."""
    t = _compile_type(col.type).lower()
    if "int" in t or t.startswith("numeric"):
        return "0"
    if "timestamp" in t:
        return "NOW()"
    # text/varchar/etc.
    if "char" in t or "text" in t:
        return "''"
    return None


def _safe_widen_type_sql(
    col_name: str, model_type_sql: str, existing_type_sql: str
) -> Optional[str]:
    """
    Return ALTER TYPE SQL if we recognize a safe widening.
    Example: int4 -> numeric(10,2) for 'weight'
    """
    # integer -> numeric(precision,scale)
    if existing_type_sql in ("int4", "integer") and model_type_sql.startswith(
        "numeric"
    ):
        return f'ALTER TABLE "{TABLE_NAME}" ALTER COLUMN "{col_name}" TYPE {model_type_sql} USING "{col_name}"::{model_type_sql};'

    # varchar(n) -> text
    if existing_type_sql.startswith("varchar(") and model_type_sql == "text":
        return f'ALTER TABLE "{TABLE_NAME}" ALTER COLUMN "{col_name}" TYPE text;'

    # timestamp without tz -> with tz (НЕ всегда безопасно; пропустим по умолчанию)
    return None


def migrate():
    logger.info(f"🚀 Starting migration: table '{TABLE_NAME}'")
    with engine.connect() as conn:
        existing = _load_existing_columns(conn)
        model_cols = _model_columns()

        logger.info(f"Existing columns: {sorted(existing.keys())}")

        to_add: Dict[str, Tuple[Column, str]] = {}
        to_alter_type: Dict[str, Tuple[str, str]] = {}

        # 1) Определяем, что добавить / что можно «безопасно расширить»
        for name, col in model_cols.items():
            model_type_sql = _compile_type(col.type).lower()

            if name not in existing:
                to_add[name] = (col, model_type_sql)
            else:
                # Проверка расхождения типов
                ex_type_sql = (existing[name].get("type") or "").lower()
                if ex_type_sql and ex_type_sql != model_type_sql:
                    # Попытаться сформировать безопасное расширение типа
                    widen_sql = _safe_widen_type_sql(name, model_type_sql, ex_type_sql)
                    if widen_sql:
                        to_alter_type[name] = (ex_type_sql, model_type_sql)

        # 2) Добавляем отсутствующие колонки
        for name, (col, model_type_sql) in to_add.items():
            null_clause = _nullability_clause(col)
            add_sql = f'ALTER TABLE "{TABLE_NAME}" ADD COLUMN "{name}" {model_type_sql} {null_clause};'
            logger.info(f"➕ Adding column: {name} {model_type_sql}")
            conn.execute(text(add_sql))

            # 2.1) Если колонка NOT NULL в модели — заполним и усилим ограничение
            if col.nullable is False:
                literal = _default_literal(col) or _fallback_literal_for_type(col)
                if literal is None:
                    # если не можем придумать значение — оставим NULLABLE, чтобы не завалить миграцию
                    logger.warning(
                        f'Column "{name}" is NOT NULL in model, but no default found. Keeping as NULLABLE to avoid data errors.'
                    )
                else:
                    logger.info(f'   Filling NULLs in "{name}" with {literal}')
                    conn.execute(
                        text(
                            f'UPDATE "{TABLE_NAME}" SET "{name}" = {literal} WHERE "{name}" IS NULL;'
                        )
                    )
                    logger.info(f'   Setting NOT NULL on "{name}"')
                    conn.execute(
                        text(
                            f'ALTER TABLE "{TABLE_NAME}" ALTER COLUMN "{name}" SET NOT NULL;'
                        )
                    )

        # 3) Безопасные изменения типа (widening)
        for name, (old_t, new_t) in to_alter_type.items():
            widen_sql = _safe_widen_type_sql(name, new_t, old_t)
            if widen_sql:
                logger.info(f'🔧 Altering type: "{name}" {old_t} -> {new_t}')
                conn.execute(text(widen_sql))

        # 4) Специальный кейс: вес мог быть INTEGER в старой схеме, а в модели — NUMERIC(10,2)
        # (Уже покрыто логикой выше, но оставим явный лог на случай отсутствия information_schema меток)
        if "weight" in existing:
            want = _compile_type(model_cols["weight"].type).lower()
            have = (existing["weight"]["type"] or "").lower()
            if have != want:
                widen_sql = _safe_widen_type_sql("weight", want, have)
                if widen_sql:
                    logger.info(
                        f'🔧 Altering type (explicit): "weight" {have} -> {want}'
                    )
                    conn.execute(text(widen_sql))

        conn.commit()
        logger.info("✅ Migration completed.")


if __name__ == "__main__":
    migrate()
