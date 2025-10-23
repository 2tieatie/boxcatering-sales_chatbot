"""Background website scraper service.

Fetches the website configured in System Settings (system_scrape_website_url)
at the configured interval (system_scrape_interval_minutes), extracts content
from footer-linked sections (excluding Blog), and writes markdown files into the
configured context documents directory so the chatbot can use the cache.
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import requests
from bs4 import BeautifulSoup  # type: ignore
from loguru import logger
import random
import time
import re
from sqlalchemy.orm import Session
# from fastapi import Depends


from app.api.assortment import _write_assortment_context_markdown
from app.database import SessionLocal, get_db
from app.models import SystemConfig
from app.config import settings
from app.models.assortment_item import AssortmentItem


def _safe_context_base_dir(db_session) -> Path:
    """Compute the effective base directory for context documents.

    Uses DB override `system_context_docs_dir` when present, otherwise falls
    back to `settings.context_docs_dir`. Returns absolute path.
    """
    try:
        cfg = (
            db_session.query(SystemConfig)
            .filter(SystemConfig.key == "system_context_docs_dir")
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
    """Holds the latest scrape status information."""

    last_run_utc: Optional[datetime] = None
    last_error: Optional[str] = None
    pages_scraped: int = 0
    url: Optional[str] = None
    interval_minutes: Optional[int] = None
    running: bool = False


class WebScraperService:
    """Simple scheduled scraper writing content as markdown into context dir."""

    def __init__(self) -> None:
        self._task: Optional[asyncio.Task[Any]] = None
        self._stop_event = asyncio.Event()
        self.status = ScrapeStatus()

    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start(self) -> None:
        """Start the background scraping loop if not already running."""
        if self.is_running():
            return
        self._stop_event = asyncio.Event()
        self._task = asyncio.create_task(self._run_loop())
        logger.info("WebScraperService started")

    async def stop(self) -> None:
        """Signal the background loop to stop and await task completion."""
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
        """Background loop that runs scrape jobs at configured interval."""
        # Run once on startup, then sleep according to interval
        while not self._stop_event.is_set():
            try:
                await self.scrape_once()
            except Exception as e:
                logger.error(f"Scheduled scrape failed: {e}")
            # Compute interval; default to 24h when not configured or invalid
            interval_minutes = 1440
            try:
                with SessionLocal() as db:
                    cfg = {
                        c.key: c.value for c in db.query(SystemConfig).all()
                    }
                raw = cfg.get("system_scrape_interval_minutes")
                if raw is not None:
                    interval_minutes = max(5, int(raw))
            except Exception:
                interval_minutes = 1440

            self.status.interval_minutes = interval_minutes

            try:
                # Sleep in small chunks to react to stop_event
                total = interval_minutes * 60
                step = min(30, total)
                slept = 0
                while slept < total and not self._stop_event.is_set():
                    try:
                        chunk = min(step, total - slept)
                        await asyncio.wait_for(self._stop_event.wait(), timeout=chunk)
                        # stop_event set
                        break
                    except asyncio.TimeoutError:
                        slept += chunk
            except Exception:
                # Ignore spurious errors and continue
                pass

    async def scrape_once(self) -> Dict[str, Any]:
        """Run one scrape cycle based on current DB configuration.

        Returns a summary dict. Writes results to context docs subdirectory
        and clears chatbot context cache so fresh data is used.
        """
        self.status.running = True
        self.status.last_error = None
        pages_scraped = 0
        url: Optional[str] = None
        try:
            with SessionLocal() as db:
                cfg = {c.key: c.value for c in db.query(SystemConfig).all()}
                url = cfg.get("system_scrape_website_url") or None
                # Honor global toggle
                enabled_raw = cfg.get("system_scrape_enabled")
                enabled = True
                if enabled_raw is not None:
                    s = str(enabled_raw).strip().lower()
                    enabled = s in {"1", "true", "yes", "on"}
                if not enabled:
                    logger.debug("WebScraperService: disabled via system_scrape_enabled; skipping")
                    return {"skipped": True, "reason": "disabled"}
                self.status.url = url
                if not url:
                    logger.info("WebScraperService: no website URL configured, skipping")
                    return {"skipped": True, "reason": "no_url"}

                base_dir = _safe_context_base_dir(db)
                # target_dir = base_dir / "website_cache"
                target_dir = base_dir
                target_dir.mkdir(parents=True, exist_ok=True)

            # # Crawl footer-linked sections using a browser-like session
            # session = self._create_session(use_cloudscraper=False)
            # resp = session.get(url, timeout=25, allow_redirects=True)
            # if resp.status_code == 403:
            #     # Retry with cloudscraper (Cloudflare/WAF bypass)
            #     logger.info("403 on homepage; retrying with cloudscraper")
            #     session = self._create_session(use_cloudscraper=True)
            #     resp = session.get(url, timeout=25, allow_redirects=True)
            # resp.raise_for_status()
            # soup = BeautifulSoup(resp.text, "html.parser")

            domain = self._origin(url)
            # footer_links = self._collect_footer_links(soup, domain)
            # # Exclude blog links
            # footer_links = [
            #     link for link in footer_links if not self._is_blog_link(link)
            # ]

            # # Always include the homepage as a section
            # if url not in footer_links:
            #     footer_links.insert(0, url)

            # docs: List[Tuple[str, str]] = []  # (filename, content)
            # for link in footer_links:
            #     try:
            #         # Small randomized delay to avoid rate/anti-bot triggers
            #         time.sleep(random.uniform(0.6, 1.4))
            #         # Include referer to look more like a human navigation
            #         p = session.get(
            #             link,
            #             timeout=25,
            #             allow_redirects=True,
            #             headers={"Referer": url},
            #         )
            #         if p.status_code == 403:
            #             # Attempt retry with cloudscraper if not already
            #             if session.__class__.__name__.lower() != "cloudscrapersession":
            #                 logger.info(f"403 on {link}; retrying with cloudscraper")
            #                 session_cf = self._create_session(use_cloudscraper=True)
            #                 logger.debug(f"Session {session_cf}")
            #                 p = session_cf.get(
            #                     link,
            #                     timeout=25,
            #                     allow_redirects=True,
            #                     headers={"Referer": url},
            #                 )
            #         p.raise_for_status()
                    
            #         sec_soup = BeautifulSoup(p.text, "html.parser")
            #         title = self._extract_title(sec_soup) or link
            #         content = self._extract_main_text(sec_soup)
            #         if content.strip():
            #             fname = _slugify(link.replace(domain, "")).replace("/", "-")
            #             if not fname or fname == "-":
            #                 fname = "index"
            #             fname = f"{fname}_auto_catalog.md"
            #             md = f"# {title}\n\n{content}\n"
            #             docs.append((fname, md))
            #             pages_scraped += 1
            #     except Exception as page_err:
            #         logger.warning(f"Failed to fetch {link}: {page_err}")

            ############################
            products = self._scrape_catalog_pages(domain)
            if products is None:
                logger.info("WebScraperService: no products at URL, skipping")
                return {"skipped": True, "reason": "no_products"}

            logger.info(f"Scraped {len(products)} products")
            # logger.info(f"Scraped {products}")
            db = next(get_db())  # get the actual Session
            await self.update_assortment_site(products, db=db)
            ############################

            # # Write file
            # try:
            #     (target_dir / fname).write_text(md, encoding="utf-8")
            # except Exception as write_err:
            #     logger.warning(f"Failed writing {fname}: {write_err}")

            # Invalidate chatbot context cache so new docs are included
            try:
                from app.api.chat import chatbot_service  # local import to avoid cycle

                chatbot_service._context_docs_cache.clear()
            except Exception as clear_err:
                logger.debug(f"Could not clear chatbot context cache: {clear_err}")

            self.status.pages_scraped = 1
            self.status.last_run_utc = datetime.now(timezone.utc)

            logger.info(f" Scraped pages from {url}")

            return {
                "ok": True,
                "pages": pages_scraped,
                "dir": str(target_dir),
                "url": url,
            }
        except Exception as e:
            self.status.last_error = str(e)
            logger.error(f"Scrape error: {e}")
            return {"ok": False, "error": str(e)}
        finally:
            self.status.running = False

    # def _create_session(self, use_cloudscraper: bool) -> requests.Session:
    #     """Create a session with realistic browser headers. Optionally use cloudscraper."""
    #     sess: requests.Session
    #     if use_cloudscraper:
    #         try:
    #             import cloudscraper  # type: ignore

    #             sess = cloudscraper.create_scraper(
    #                 browser={
    #                     "browser": "chrome",
    #                     "platform": "windows",
    #                     "mobile": False,
    #                 }
    #             )
    #         except Exception as e:
    #             logger.warning(f"cloudscraper not available or failed to init: {e}")
    #             sess = requests.Session()
    #     else:
    #         sess = requests.Session()

    #     # Reasonable desktop Chrome headers
    #     sess.headers.update(
    #         {
    #             "User-Agent": (
    #                 "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    #                 "AppleWebKit/537.36 (KHTML, like Gecko) "
    #                 "Chrome/126.0.0.0 Safari/537.36"
    #             ),
    #             "Accept": (
    #                 "text/html,application/xhtml+xml,application/xml;q=0.9,"
    #                 "image/avif,image/webp,*/*;q=0.8"
    #             ),
    #             "Accept-Language": "uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7",
    #             "Accept-Encoding": "gzip, deflate, br",
    #             "Connection": "keep-alive",
    #             "Upgrade-Insecure-Requests": "1",
    #         }
    #     )
    #     return sess

    def _origin(self, url: str) -> str:
        m = re.match(r"^(https?://[^/]+)", url)
        return m.group(1) if m else url

    # def _collect_footer_links(self, soup: BeautifulSoup, domain: str) -> List[str]:
    #     """Collect unique absolute links from the page footer within same origin."""
    #     links: List[str] = []
    #     seen: Set[str] = set()
    #     footer = soup.find("footer")
    #     if not footer:
    #         return links
    #     for a in footer.find_all("a", href=True):
    #         href: str = a.get("href", "").strip()
    #         if not href or href.startswith("#"):
    #             continue
    #         if href.startswith("http://") or href.startswith("https://"):
    #             if not href.startswith(domain):
    #                 continue
    #             abs_url = href
    #         else:
    #             if not href.startswith("/"):
    #                 href = "/" + href
    #             abs_url = domain + href
    #         if abs_url in seen:
    #             continue
    #         seen.add(abs_url)
    #         links.append(abs_url)
    #     return links

    # def _is_blog_link(self, url: str) -> bool:
    #     s = url.lower()
    #     return "/blog" in s or s.endswith("/blog/") or "blog." in s

    # def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
    #     for selector in ["h1", "title", "h2"]:
    #         el = soup.select_one(selector)
    #         if el and el.get_text(strip=True):
    #             return el.get_text(strip=True)
    #     return None

    # def _extract_main_text(self, soup: BeautifulSoup) -> str:
    #     """Heuristic text extraction: prefer <main> or <article>, else body sans nav/footer."""
    #     # Remove noise
    #     for sel in ["script", "style", "noscript", "header", "nav", "footer", "form"]:
    #         for node in soup.select(sel):
    #             try:
    #                 node.decompose()
    #             except Exception:
    #                 pass

    #     container = soup.select_one("main") or soup.select_one("article") or soup.body
    #     if not container:
    #         return ""
    #     text = container.get_text(separator="\n", strip=True)
    #     # Normalize excessive blank lines
    #     lines = [ln.strip() for ln in text.splitlines()]
    #     clean = "\n".join([ln for ln in lines if ln])
    #     return clean
    
    def _scrape_catalog_pages(self, base_url: str) -> List[Dict[str, str]]:
        return None # Remove this line on publish
    
        import cloudscraper
        from bs4 import BeautifulSoup

        scraper = cloudscraper.create_scraper()
        products = []
        page = 1

        logger.debug(f"Scraping catalog pages from {base_url}")

        while True:
            url = f"{base_url}/catalog/"
            if page > 1:
                url = f"{base_url}/catalog/?page={page}"

            try:
                response = scraper.get(url)
                response.raise_for_status()
            except Exception as e:
                logger.warning(f"Failed to fetch page {page}: {e}")
                break

            soup = BeautifulSoup(response.text, "html.parser")

            # get all product links
            product_links = []
            for card in soup.select(".goods[href]"):
                href = card.get("href")
                if href and href.startswith("/product/"):
                    product_links.append(f"{base_url}{href}")

            logger.debug(f"Page {page}: found {len(product_links)} product links")

            if not product_links:
                break  # pagination is over

            # check every link
            for link in product_links:
                try:
                    logger.debug(f"Scraping product {link}")
                    response = scraper.get(link)
                    response.raise_for_status()
                    item = BeautifulSoup(response.text, "html.parser")

                    title_el = item.select_one(".product-info__title")
                    title = title_el.get_text(strip=True) if title_el else ""

                    ds_el = item.select_one(".product-info__descr")
                    description = ds_el.get_text(strip=True) if ds_el else ""

                    dm_el = item.select_one(".product-info__description")
                    description_more = dm_el.get_text(strip=True) if dm_el else ""

                    pr_el = item.select_one(".product-values__price-default")
                    price_raw = pr_el.get_text(strip=True) if pr_el else None

                    if price_raw is None:
                        pr_actual_el = item.select_one(".product-values__price-actual")
                        price_raw = pr_actual_el.get_text(strip=True) if pr_actual_el else ""

                    price = re.sub(r'\D', '', price_raw)

                    qs_el = item.select_one(".product-calculated__val")
                    guests_raw = qs_el.get_text(strip=True) if qs_el else "1"
                    guests = re.sub(r'\D', '', guests_raw)

                    wt_el = item.select_one(".product-values__weight")
                    weight_raw = wt_el.get_text(strip=True) if wt_el else "0"
                    weight = re.sub(r'\D', '', weight_raw)

                    products.append({
                        "title": title,
                        "description": f"{description}\n{description_more}",
                        "price": price,
                        "guests": guests,
                        "weight": weight
                    })

                except Exception as e:
                    logger.warning(f"Failed to fetch item {link}: {e}")
                    continue 

            page += 1  # next page
            # page += 10  # next page

        return products

    async def update_assortment_site(
        self,
        products: List,
        db: Session,
    ):
        """Update assortment from an website. Columns: name, description, price_uah."""

        errors: list[str] = []

        # Remove existing items
        db.query(AssortmentItem).delete()
        db.commit()

        for pr in products:
            try:
                item = AssortmentItem(name=pr["title"], description=pr["description"], price_uah=pr["price"], guests=pr["guests"], weight=pr["weight"])
                logger.debug(f"Adding item: {pr["title"]}")
                db.add(item)
            except Exception as row_err:
                errors.append(str(row_err))

        db.commit()

        # Write/refresh assortment.md for chatbot context
        try:
            _write_assortment_context_markdown(db)
        except Exception:
            pass

        return True


# Expose a singleton for app/main and API modules
web_scraper = WebScraperService()


