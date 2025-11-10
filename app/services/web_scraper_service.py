"""Background website scraper service.

Fetches external product data and updates the local assortment cache.
Keeps AssortmentItem rows in sync by upserting changed items, inserting new ones,
and deleting missing ones in a minimal number of DB queries.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone, UTC
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Iterable
from haystack import Document
import httpx
from haystack.components.embedders import OpenAIDocumentEmbedder
from haystack.document_stores.types import DuplicatePolicy
from haystack.utils import Secret
from haystack_integrations.document_stores.qdrant import QdrantDocumentStore
from loguru import logger
from pydantic import BaseModel
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import Filter, FilterSelector, FieldCondition, MatchAny
from qdrant_client.models import VectorParams, Distance, PointStruct, PointIdsList
from sqlalchemy.orm import Session

from app.api.assortment import _write_assortment_context_markdown
from app.database import SessionLocal, get_db
from app.models import SystemConfig
from app.config import settings
from app.models.assortment_item import AssortmentItem


def _safe_context_base_dir(db_session) -> Path:
    try:
        cfg = (
            db_session.query(SystemConfig)
            .filter(SystemConfig.key == "system_context_docs_ ")
            .first()
        )
        dir_value = cfg.value if cfg and cfg.value else settings.context_docs_dir
    except Exception as e:
        logger.warning(f"Failed to read context dir from DB, using default: {e}")
        dir_value = settings.context_docs_dir
    base = Path(dir_value)
    if not base.is_absolute():
        base = Path.cwd() / base
    return base


def _slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9\-_/]+", "-", text)
    text = text.replace("--", "-")
    return text.strip("-") or "index"


@dataclass
class ScrapeStatus:
    last_run_utc: Optional[datetime] = None
    last_error: Optional[str] = None
    pages_scraped: int = 0
    url: Optional[str] = None
    interval_minutes: Optional[int] = None
    running: bool = False


class WebScraperService:
    def __init__(self) -> None:
        self._task: Optional[asyncio.Task[Any]] = None
        self._stop_event = asyncio.Event()
        self.status = ScrapeStatus()

    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start(self) -> None:
        if self.is_running():
            return
        self._stop_event = asyncio.Event()
        self._task = asyncio.create_task(self._run_loop())
        logger.info("WebScraperService started")

    async def stop(self) -> None:
        if self._task is None:
            return
        self._stop_event.set()
        try:
            await asyncio.wait_for(self._task, timeout=10)
        except asyncio.TimeoutError:
            logger.warning("WebScraperService did not stop within timeout")
        finally:
            self._task = None
        logger.info("WebScraperService stopped")

    async def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                await self.scrape_once()
            except Exception as e:
                logger.error(f"Scheduled scrape failed: {e}")
            interval_minutes = 1440
            try:
                with SessionLocal() as db:
                    cfg = {c.key: c.value for c in db.query(SystemConfig).all()}
                raw = cfg.get("system_scrape_interval_minutes")
                if raw is not None:
                    interval_minutes = max(5, int(raw))
            except Exception:
                interval_minutes = 1440
            self.status.interval_minutes = interval_minutes
            try:
                total = interval_minutes * 60
                step = min(30, total)
                slept = 0
                while slept < total and not self._stop_event.is_set():
                    try:
                        chunk = min(step, total - slept)
                        await asyncio.wait_for(self._stop_event.wait(), timeout=chunk)
                        break
                    except asyncio.TimeoutError:
                        slept += chunk
            except Exception:
                pass

    async def scrape_once(self) -> Dict[str, Any]:

        # ds = QdrantDocumentStore(
        #     url="https://0a87a722-2e15-4fc0-aa39-5c99fc2866ca.us-west-1-0.aws.cloud.qdrant.io:6333",
        #     api_key=Secret.from_token("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.DI_UrA1AMY62uHlhTsWxIwhsdtyGU0KU2oiwY5e43Vc"),
        #     index="products",
        #     embedding_dim=1536,
        #     recreate_index=False
        # )
        # ds._initialize_client()
        # print(ds._client.get_collections())
        # result = ds._client.delete(
        #     collection_name=ds.index,
        #     points_selector=Filter(must=[]),  # вместо {"filter": {}}
        # )
        # print(result)
        # print(ds._client.count(collection_name="products"))
        # res = await _fetch_all_payloads(ds)
        # print(res)
        self.status.running = True
        self.status.last_error = None
        try:
            with SessionLocal() as db:
                cfg = {c.key: c.value for c in db.query(SystemConfig).all()}
                enabled_raw = cfg.get("system_scrape_enabled")
                enabled = True
                if enabled_raw is not None:
                    s = str(enabled_raw).strip().lower()
                    enabled = s in {"1", "true", "yes", "on"}
                if not enabled:
                    logger.debug("WebScraperService: disabled via system_scrape_enabled; skipping")
                    return {"skipped": True, "reason": "disabled"}
                base_dir = _safe_context_base_dir(db)
                target_dir = base_dir
                target_dir.mkdir(parents=True, exist_ok=True)
            products: List[Dict[str, Any]] = await _fetch_boxcatering_products()
            if not products:
                logger.info("WebScraperService: no products fetched, skipping")
                return {"skipped": True, "reason": "no_products"}
            db = next(get_db())
            await update_assortment_site(products, db=db)
            await update_vector_store_data(db=db)
            try:
                from app.api.chat import chatbot_service
                chatbot_service._context_docs_cache.clear()
            except Exception as clear_err:
                logger.debug(f"Could not clear chatbot context cache: {clear_err}")
            self.status.pages_scraped = 1
            self.status.last_run_utc = datetime.now(timezone.utc)
            logger.info("WebScraperService: products synchronized")
            return {"ok": True, "pages": 1, "dir": str(target_dir)}
        except Exception as e:
            self.status.last_error = str(e)
            logger.error(f"Scrape error: {e}")
            return {"ok": False, "error": str(e)}
        finally:
            self.status.running = False


web_scraper = WebScraperService()


class Category(BaseModel):
    id: int
    title: str
    slug: str


def _split_categories(value: Optional[str]) -> List[str]:
    if not value:
        return []
    parts = [p.strip() for p in str(value).split(",") if p and p.strip()]
    seen = set()
    out = []
    for p in parts:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


async def _fetch_json(client: httpx.AsyncClient, url: str, params: Optional[Dict[str, Any]] = None, attempts: int = 3) -> Optional[Dict[str, Any] | List[Any]]:
    for i in range(attempts):
        try:
            resp = await client.get(url, params=params, timeout=15.0)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        await asyncio.sleep(0.2 * (i + 1))
    return None


async def get_categories(client: httpx.AsyncClient) -> List[Category]:
    url = "https://back.box-catering.ua/api/cities/1/categories"
    data = await _fetch_json(client, url)
    if not isinstance(data, list):
        return []
    out: List[Category] = []
    for raw in data:
        try:
            out.append(Category(id=int(raw.get("id", 0)), title=str(raw.get("title", "")).strip(), slug=str(raw.get("slug", "")).strip()))
        except Exception:
            continue
    return [c for c in out if c.id and c.title and c.slug]


async def get_products_by_category_slug(client: httpx.AsyncClient, slug: str) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    page = 1
    base = f"https://back.box-catering.ua/api/cities/1/categories/{slug}/products"
    while True:
        data = await _fetch_json(client, base, params={"page": page})
        if not isinstance(data, dict):
            break
        products = data.get("products")
        if not isinstance(products, list) or not products:
            break
        for p in products:
            if isinstance(p, dict):
                result.append(p)
        page += 1
    return result


async def _fetch_boxcatering_products() -> List[Dict[str, Any]]:
    async with httpx.AsyncClient(headers={"User-Agent": "BoxCatering-Script"}) as client:
        categories = await get_categories(client)
        if not categories:
            return []
        tasks = [get_products_by_category_slug(client, c.slug) for c in categories]
        batches = await asyncio.gather(*tasks, return_exceptions=True)
        products_by_id: Dict[Any, Dict[str, Any]] = {}
        for cat, batch in zip(categories, batches):
            if isinstance(batch, Exception) or not isinstance(batch, list):
                continue
            for product in batch:
                if not isinstance(product, dict):
                    continue
                pid = product.get("id")
                if pid is None:
                    continue
                cat_list = _split_categories(product.get("category"))
                if cat.title not in cat_list:
                    cat_list.append(cat.title)
                if pid not in products_by_id:
                    merged = dict(product)
                    merged["category"] = ", ".join(cat_list) if cat_list else None
                    products_by_id[pid] = merged
                else:
                    merged = products_by_id[pid]
                    merged_cats = _split_categories(merged.get("category"))
                    for c in cat_list:
                        if c not in merged_cats:
                            merged_cats.append(c)
                    merged["category"] = ", ".join(merged_cats) if merged_cats else None
        items = list(products_by_id.values())
        return items


def _to_decimal(x: Any, default: Decimal = Decimal("0")) -> Decimal:
    if x is None:
        return default
    try:
        if isinstance(x, Decimal):
            return x.quantize(Decimal("0.01"))
        s = str(x).replace(" ", "").replace(",", ".")
        s = re.sub(r"[^\d\.\-]", "", s)
        if s == "" or s == "-" or s == ".":
            return default
        return Decimal(s).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return default


def _norm_str(x: Any) -> Optional[str]:
    if x is None:
        return None
    s = str(x).strip()
    return s if s else None


def _product_key(p: Dict[str, Any]) -> Optional[str]:
    slug = _norm_str(p.get("slug"))
    if slug:
        return f"slug:{slug}"
    pid = p.get("id")
    if pid is not None:
        return f"id:{pid}"
    title = _norm_str(p.get("title"))
    if title:
        return f"name:{title}"
    return None


async def update_assortment_site(products: List[Dict[str, Any]], db: Session) -> bool:
    try:
        wanted: Dict[str, Dict[str, Any]] = {}
        for pr in products:
            k = _product_key(pr)
            if not k:
                continue
            wanted[k] = pr

        existing_rows: List[AssortmentItem] = db.query(AssortmentItem).all()
        existing_by_key: Dict[str, AssortmentItem] = {}
        for row in existing_rows:
            k = None
            if row.slug:
                k = f"slug:{row.slug}"
            elif row.name:
                k = f"name:{row.name}"
            if k:
                existing_by_key[k] = row

        to_insert: List[Dict[str, Any]] = []
        to_update: List[Dict[str, Any]] = []
        keep_ids: Set[int] = set()

        for k, pr in wanted.items():
            name = _norm_str(pr.get("title")) or _norm_str(pr.get("name")) or "Без назви"
            description = _norm_str(pr.get("description"))
            price = _to_decimal(pr.get("price") or pr.get("price_uah") or pr.get("priceUAH") or pr.get("priceUah") or pr.get("amount"))
            guests = int(pr.get("people_amount") or 0) if str(pr.get("people_amount") or "").isdigit() else None
            weight = _to_decimal(pr.get("weight") or pr.get("mass") or pr.get("grams") or 0)
            print_label = _norm_str(pr.get("print_label") or pr.get("label"))
            slug = _norm_str(pr.get("slug") or _slugify(name))
            img = _norm_str(pr.get("img") or pr.get("image") or pr.get("photo") or pr.get("thumbnail"))
            type_ = _norm_str(pr.get("type") or pr.get("product_type"))
            category = _norm_str(pr.get("category"))

            if k in existing_by_key:
                row = existing_by_key[k]
                keep_ids.add(row.id)
                changed = False

                if (row.name or "") != (name or ""):
                    changed = True
                if (row.description or "") != (description or ""):
                    changed = True
                if _to_decimal(row.price_uah) != price:
                    changed = True
                if (row.guests or None) != guests:
                    changed = True
                if _to_decimal(row.weight) != weight:
                    changed = True
                if (row.print_label or "") != (print_label or ""):
                    changed = True
                if (row.slug or "") != (slug or ""):
                    changed = True
                if (row.img or "") != (img or ""):
                    changed = True
                if (row.type or "") != (type_ or ""):
                    changed = True
                if (row.category or "") != (category or ""):
                    changed = True

                if changed:
                    to_update.append(
                        {
                            "id": row.id,
                            "name": name,
                            "description": description,
                            "price_uah": price,
                            "guests": guests,
                            "weight": weight,
                            "print_label": print_label,
                            "slug": slug,
                            "img": img,
                            "type": type_,
                            "category": category,
                            "updated_at": datetime.now(UTC),
                        }
                    )
            else:
                to_insert.append(
                    {
                        "name": name,
                        "description": description,
                        "price_uah": price,
                        "guests": guests,
                        "weight": weight,
                        "print_label": print_label,
                        "slug": slug,
                        "img": img,
                        "type": type_,
                        "category": category,
                        "created_at": datetime.now(UTC),
                        "updated_at": datetime.now(UTC),
                    }
                )

        ids_to_delete: List[int] = []
        for row in existing_rows:
            if row.id not in keep_ids:
                ids_to_delete.append(row.id)

        try:
            if ids_to_delete:
                db.query(AssortmentItem).filter(AssortmentItem.id.in_(ids_to_delete)).delete(synchronize_session=False)
            if to_update:
                db.bulk_update_mappings(AssortmentItem, to_update)
            if to_insert:
                db.bulk_insert_mappings(AssortmentItem, to_insert)
            db.commit()
        except Exception as e:
            logger.error(f"DB write error: {e}")
            try:
                db.rollback()
            except Exception:
                pass
            return False

        try:
            _write_assortment_context_markdown(db)
        except Exception as e:
            logger.debug(f"Context markdown refresh skipped: {e}")

        logger.info(
            f"Assortment sync: inserted={len(to_insert)}, updated={len(to_update)}, deleted={len(ids_to_delete)}, total_now={db.query(AssortmentItem).count()}"
        )
        return True
    except Exception as e:
        logger.error(f"Assortment sync failed: {e}")
        try:
            db.rollback()
        except Exception:
            pass
        return False



def _product_to_content_and_meta(p: "AssortmentItem") -> Tuple[str, Dict[str, Any]]:
    content = (
        f"[ID:{p.id}] {p.category or ''}. {p.type or ''}. {p.name or ''}. "
        f"{(p.description or '').strip()} {(p.print_label or '').strip()}. "
        f"{p.price_uah} гривень. {p.weight} грам. На {p.guests} гостей/осіб."
    ).strip()
    meta: Dict[str, Any] = {
        "id": int(p.id),
        "guests": int(p.guests) if p.guests is not None else None,
        "price": float(p.price_uah) if p.price_uah is not None else None,
        "weight": float(p.weight) if p.weight is not None else None,
        "category": (p.category or None),
        "type": (p.type or None),
        "name": (p.name or None),
    }
    return content, meta

def _fingerprint(content: str, meta: Dict[str, Any]) -> str:
    payload = {
        "content": content,
        "meta": json.loads(json.dumps(meta, sort_keys=True, ensure_ascii=False)),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def _iter_batches(items: Iterable[Any], size: int) -> Iterable[List[Any]]:
    batch: List[Any] = []
    for x in items:
        batch.append(x)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch

async def _ensure_collection(client: AsyncQdrantClient, collection: str = "products") -> None:
    try:
        await client.get_collection(collection)
    except Exception:
        await client.create_collection(
            collection,
            vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
        )

async def _fetch_all_payloads(ds: QdrantDocumentStore) -> Dict[str, Dict[str, Any]]:
    existing: Dict[str, Dict[str, Any]] = {}
    next_offset = None
    while True:
        points, next_offset = await asyncio.to_thread(
            ds._client.scroll,
            collection_name=ds.index,
            limit=1000,
            with_payload=True,
            with_vectors=False,
            offset=next_offset,
        )
        for pt in points:
            existing[str(pt.payload["id"])] = pt.payload or {}
        if not next_offset:
            break
    return existing

async def update_vector_store_data(db: "Session") -> None:
    BATCH_SIZE = 128
    ds = QdrantDocumentStore(
        url="https://0a87a722-2e15-4fc0-aa39-5c99fc2866ca.us-west-1-0.aws.cloud.qdrant.io:6333",
        api_key=Secret.from_token(
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.DI_UrA1AMY62uHlhTsWxIwhsdtyGU0KU2oiwY5e43Vc"),
        index="products",
        embedding_dim=1536,
        recreate_index=False,
    )
    ds._initialize_client()
    existing_payloads = await _fetch_all_payloads(ds)

    products: List["AssortmentItem"] = db.query(AssortmentItem).all()
    to_upsert_docs: List[Document] = []
    wanted_ids: Set[str] = set()
    for p in products:
        content, meta = _product_to_content_and_meta(p)
        fp = _fingerprint(content, meta)
        meta["fp"] = fp
        doc_id = str(p.id)
        wanted_ids.add(doc_id)
        if doc_id not in existing_payloads:
            to_upsert_docs.append(Document(id=doc_id, content=content, meta=meta))

    ids_to_delete = [pid for pid in existing_payloads.keys() if pid not in wanted_ids]
    await asyncio.to_thread(
        ds._client.delete,
        collection_name=ds.index,
        points_selector=FilterSelector(
            filter=Filter(
                must=[
                    FieldCondition(
                        key="id",
                        match=MatchAny(any=ids_to_delete),
                    )
                ]
            )
        ),
    )

    if to_upsert_docs:
        embedder = OpenAIDocumentEmbedder(api_key=Secret.from_token(settings.openai_api_key))
        embedded_all: List[Document] = []
        for batch in _iter_batches(to_upsert_docs, 25):
            res = await embedder.run_async(batch)
            embedded_all.extend(res["documents"])
        try:
            for batch in _iter_batches(embedded_all, 10):
                await ds.write_documents_async(batch, DuplicatePolicy.SKIP)
        except Exception as e:
            print(e)
            print(traceback.format_exc())
if __name__ == "__main__":
    try:
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(web_scraper.scrape_once())
        print(result)
    except Exception:
        print({"ok": False})
