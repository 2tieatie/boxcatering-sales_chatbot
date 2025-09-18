"""Assortment API: list items and upload from Excel.

Accessible to MANAGER, ADMIN, SYSTEM_ADMIN.
"""

from __future__ import annotations

from typing import Dict, List
from decimal import Decimal
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, Form
import csv
from io import BytesIO, StringIO
from sqlalchemy.orm import Session
from loguru import logger

from app.database import get_db, SessionLocal
from app.models import AssortmentItem, User
from app.schemas.assortment_item import AssortmentItemResponse, AssortmentUploadResult
from app.dependencies import get_current_active_user_dependency, role_service

router = APIRouter(prefix="/assortment", tags=["assortment"])


@router.get("/items", response_model=List[AssortmentItemResponse])
async def list_assortment_items(
    skip: int = 0,
    limit: int = 500,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user_dependency),
):
    """Return assortment items. Accessible to manager or higher."""
    role_service.require_manager_or_higher(current_user)
    items = (
        db.query(AssortmentItem)
        .order_by(AssortmentItem.name.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return items


def _write_assortment_context_markdown(db_session: Session) -> None:
    """Write a markdown summary of assortment items into context docs for the chatbot."""
    try:
        from app.models import SystemConfig
        from app.config import settings

        cfg = {c.key: c.value for c in db_session.query(SystemConfig).all()}
        dir_value = cfg.get("system_context_docs_dir") or settings.context_docs_dir
        base = Path(dir_value)
        if not base.is_absolute():
            base = Path.cwd() / base
        base.mkdir(parents=True, exist_ok=True)
        md_path = base / "00_assortment.md"
        rows = (
            db_session.query(AssortmentItem)
            .order_by(AssortmentItem.name.asc())
            .all()
        )
        lines = ["# Асортимент (Assortment)\n"]
        lines.append("Назва | Опис | Ціна (UAH) | Людей | Вага (кг)")
        lines.append("--- | --- | --- | --- | ---")
        for r in rows:
            name = (r.name or "").replace("|", "/").strip()
            desc = (r.description or "").replace("|", "/").replace("\n", " ").replace("\r", " ").strip()
            price = f"{Decimal(r.price_uah):.2f}"
            lines.append(f"{name} | {desc} | {price} | {r.guests} | {r.weight}")
        md_path.write_text("\n".join(lines), encoding="utf-8")

        # Invalidate chatbot context cache
        try:
            from app.api.chat import chatbot_service  # local import to avoid cycle

            chatbot_service._context_docs_cache.clear()
        except Exception as clear_err:
            logger.debug(f"Could not clear chatbot context cache: {clear_err}")
    except Exception as e:
        logger.warning(f"Failed writing assortment context markdown: {e}")


@router.post("/upload", response_model=AssortmentUploadResult, status_code=status.HTTP_201_CREATED)
async def upload_assortment_excel(
    file: UploadFile = File(...),
    replace: bool = Form(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user_dependency),
):
    """Upload assortment from an Excel file (XLSX). Columns: name, description, price_uah.

    - replace=True: clears existing items before import
    - Accessible to manager or higher
    """
    role_service.require_manager_or_higher(current_user)

    filename = (file.filename or "").lower()
    is_excel = filename.endswith(".xlsx") or filename.endswith(".xls")
    is_csv = filename.endswith(".csv")

    if not (is_excel or is_csv):
        raise HTTPException(
            status_code=400,
            detail="Only Excel (.xlsx/.xls) or CSV (.csv) files are supported",
        )

    imported = 0
    skipped = 0
    errors: list[str] = []
    total_rows = 0

    try:
        if is_excel:
            try:
                from openpyxl import load_workbook  # type: ignore
            except Exception:
                raise HTTPException(status_code=500, detail="Excel support missing: install openpyxl")

            try:
                data = await file.read()
                wb = load_workbook(BytesIO(data), data_only=True)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to read Excel: {e}")

            ws = wb.active

            # Detect header row within the first 10 rows
            header_row_index = None
            idx_name = -1
            idx_desc = -1
            idx_price = -1
            for r_index, row in enumerate(ws.iter_rows(min_row=1, max_row=10), start=1):
                headers: list[str] = [str(c.value or "").strip().lower() for c in row]
                try:
                    idx_name = headers.index("name")
                except ValueError:
                    idx_name = -1
                try:
                    idx_desc = headers.index("description")
                except ValueError:
                    idx_desc = -1
                price_candidates = [
                    i for i, h in enumerate(headers) if h in {"price", "price_uah", "ціна", "tsina"}
                ]
                if idx_name >= 0 and price_candidates:
                    idx_price = price_candidates[0]
                    header_row_index = r_index
                    break

            if header_row_index is None or idx_name < 0 or idx_price < 0:
                raise HTTPException(status_code=400, detail="File must have 'name' and 'price' columns")

            if replace:
                db.query(AssortmentItem).delete()
                db.commit()

            for r in ws.iter_rows(min_row=header_row_index + 1):
                try:
                    name_cell = r[idx_name]
                    price_cell = r[idx_price]
                    desc_cell = r[idx_desc] if idx_desc >= 0 else None

                    name = str(name_cell.value).strip() if name_cell and name_cell.value is not None else ""
                    if not name:
                        skipped += 1
                        continue
                    raw_price = price_cell.value if price_cell else None
                    price: Decimal
                    if raw_price is None or (isinstance(raw_price, str) and not raw_price.strip()):
                        skipped += 1
                        continue
                    try:
                        if isinstance(raw_price, (int, float)):
                            price = Decimal(str(raw_price))
                        else:
                            price = Decimal(str(raw_price).replace(",", ".").strip())
                    except Exception:
                        skipped += 1
                        continue

                    description = (
                        str(desc_cell.value).strip() if desc_cell and desc_cell.value is not None else None
                    )

                    item = AssortmentItem(name=name, description=description, price_uah=price)
                    db.add(item)
                    imported += 1
                except Exception as row_err:
                    errors.append(str(row_err))

            db.commit()
            total_rows = max(ws.max_row - header_row_index, 0)

        else:
            # CSV parsing path
            try:
                data = await file.read()
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to read file: {e}")

            try:
                text = data.decode("utf-8-sig")
            except Exception:
                text = data.decode("utf-8", errors="ignore")

            # Detect delimiter (handle semicolon/comma)
            sample = text[:2048]
            delimiter = ","
            try:
                sniffed = csv.Sniffer().sniff(sample, delimiters=[",", ";", "\t", "|"])
                delimiter = sniffed.delimiter
            except Exception:
                # Fallback heuristic
                if ";" in sample and "," not in sample:
                    delimiter = ";"

            reader = csv.reader(StringIO(text), delimiter=delimiter)
            rows = list(reader)
            if not rows:
                raise HTTPException(status_code=400, detail="CSV is empty")

            headers = [str(h or "").strip().lower() for h in rows[0]]
            try:
                idx_name = headers.index("name")
            except ValueError:
                idx_name = -1
            try:
                idx_desc = headers.index("description")
            except ValueError:
                idx_desc = -1
            price_candidates = [
                i for i, h in enumerate(headers) if h in {"price", "price_uah", "ціна", "tsina"}
            ]
            idx_price = price_candidates[0] if price_candidates else -1

            if idx_name < 0 or idx_price < 0:
                raise HTTPException(status_code=400, detail="File must have 'name' and 'price' columns")

            if replace:
                db.query(AssortmentItem).delete()
                db.commit()

            for row in rows[1:]:
                try:
                    # Guard against short rows
                    name = str(row[idx_name]).strip() if idx_name < len(row) else ""
                    if not name:
                        skipped += 1
                        continue

                    raw_price_value = row[idx_price] if idx_price < len(row) else None
                    if raw_price_value is None or (isinstance(raw_price_value, str) and not str(raw_price_value).strip()):
                        skipped += 1
                        continue

                    try:
                        price = Decimal(str(raw_price_value).replace(",", ".").strip())
                    except Exception:
                        skipped += 1
                        continue

                    description = (
                        str(row[idx_desc]).strip() if (idx_desc >= 0 and idx_desc < len(row) and row[idx_desc] is not None) else None
                    )

                    item = AssortmentItem(name=name, description=description, price_uah=price)
                    db.add(item)
                    imported += 1
                except Exception as row_err:
                    errors.append(str(row_err))

            db.commit()
            total_rows = max(len(rows) - 1, 0)

        # Write/refresh assortment.md for chatbot context
        try:
            _write_assortment_context_markdown(db)
        except Exception:
            pass

        return AssortmentUploadResult(
            replaced=bool(replace),
            total_rows=total_rows,
            imported=imported,
            skipped=skipped,
            errors=(errors if errors else None),
        )
    finally:
        try:
            await file.close()
        except Exception:
            pass

