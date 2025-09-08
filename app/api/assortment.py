"""Assortment API: list items and upload from Excel.

Accessible to MANAGER, ADMIN, SYSTEM_ADMIN.
"""

from __future__ import annotations

from typing import List
from decimal import Decimal
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
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
        md_path = base / "assortment.md"
        rows = (
            db_session.query(AssortmentItem)
            .order_by(AssortmentItem.name.asc())
            .all()
        )
        lines = ["# Асортимент (Assortment)\n"]
        lines.append("Назва | Опис | Ціна (UAH)")
        lines.append("--- | --- | ---")
        for r in rows:
            name = (r.name or "").replace("|", "/").strip()
            desc = (r.description or "").replace("|", "/").strip()
            price = f"{Decimal(r.price_uah):.2f}"
            lines.append(f"{name} | {desc} | {price}")
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
    replace: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user_dependency),
):
    """Upload assortment from an Excel file (XLSX). Columns: name, description, price_uah.

    - replace=True: clears existing items before import
    - Accessible to manager or higher
    """
    role_service.require_manager_or_higher(current_user)

    filename = (file.filename or "").lower()
    if not (filename.endswith(".xlsx") or filename.endswith(".xls")):
        raise HTTPException(status_code=400, detail="Only Excel files (.xlsx/.xls) are supported")

    try:
        from openpyxl import load_workbook  # type: ignore
    except Exception:
        raise HTTPException(status_code=500, detail="Excel support missing: install openpyxl")

    try:
        content = await file.read()
        wb = load_workbook(filename=file.filename or "import.xlsx", data_only=True)
        # When using file-like bytes, open with BytesIO
    except Exception:
        from io import BytesIO

        try:
            data = await file.read()
            wb = load_workbook(BytesIO(data), data_only=True)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to read Excel: {e}")

    try:
        ws = wb.active
        headers = []
        imported = 0
        skipped = 0
        errors: list[str] = []

        # Read header row
        for cell in ws[1]:
            headers.append(str(cell.value or "").strip().lower())

        # Expect columns: name, description, price or price_uah
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
            raise HTTPException(status_code=400, detail="Excel must have 'name' and 'price' columns")

        if replace:
            db.query(AssortmentItem).delete()
            db.commit()

        for r in ws.iter_rows(min_row=2):
            try:
                name_cell = r[idx_name]
                price_cell = r[idx_price]
                desc_cell = r[idx_desc] if idx_desc >= 0 else None

                name = str(name_cell.value).strip() if name_cell and name_cell.value is not None else ""
                if not name:
                    skipped += 1
                    continue
                # Parse price
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

        # Write/refresh assortment.md for chatbot context
        try:
            _write_assortment_context_markdown(db)
        except Exception:
            pass

        return AssortmentUploadResult(
            replaced=bool(replace),
            total_rows=ws.max_row - 1,
            imported=imported,
            skipped=skipped,
            errors=(errors if errors else None),
        )
    finally:
        try:
            await file.close()
        except Exception:
            pass


