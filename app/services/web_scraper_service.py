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

from app.database import SessionLocal
from app.models import SystemConfig
from app.config import settings


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
                    await asyncio.wait_for(self._stop_event.wait(), timeout=step)
                    slept += step
            except asyncio.TimeoutError:
                # Normal path: timeout means continue
                pass
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
                self.status.url = url
                if not url:
                    logger.info("WebScraperService: no website URL configured, skipping")
                    return {"skipped": True, "reason": "no_url"}

                base_dir = _safe_context_base_dir(db)
                target_dir = base_dir / "website_cache"
                target_dir.mkdir(parents=True, exist_ok=True)

            # Crawl footer-linked sections
            headers = {
                "User-Agent": "BoxCateringBot/1.0 (+https://boxcatering-chatbot.local)"
            }
            resp = requests.get(url, timeout=20, headers=headers)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            domain = self._origin(url)
            footer_links = self._collect_footer_links(soup, domain)
            # Exclude blog links
            footer_links = [
                link for link in footer_links if not self._is_blog_link(link)
            ]

            # Always include the homepage as a section
            if url not in footer_links:
                footer_links.insert(0, url)

            docs: List[Tuple[str, str]] = []  # (filename, content)
            for link in footer_links:
                try:
                    p = requests.get(link, timeout=20, headers=headers)
                    p.raise_for_status()
                    sec_soup = BeautifulSoup(p.text, "html.parser")
                    title = self._extract_title(sec_soup) or link
                    content = self._extract_main_text(sec_soup)
                    if content.strip():
                        fname = _slugify(link.replace(domain, "")).replace("/", "-")
                        if not fname or fname == "-":
                            fname = "index"
                        fname = f"{fname}.md"
                        md = f"# {title}\n\n{content}\n"
                        docs.append((fname, md))
                        pages_scraped += 1
                except Exception as page_err:
                    logger.warning(f"Failed to fetch {link}: {page_err}")

            # Write files
            for fname, md in docs:
                try:
                    (target_dir / fname).write_text(md, encoding="utf-8")
                except Exception as write_err:
                    logger.warning(f"Failed writing {fname}: {write_err}")

            # Invalidate chatbot context cache so new docs are included
            try:
                from app.api.chat import chatbot_service  # local import to avoid cycle

                chatbot_service._context_docs_cache.clear()
            except Exception as clear_err:
                logger.debug(f"Could not clear chatbot context cache: {clear_err}")

            self.status.pages_scraped = pages_scraped
            self.status.last_run_utc = datetime.now(timezone.utc)

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

    def _origin(self, url: str) -> str:
        m = re.match(r"^(https?://[^/]+)", url)
        return m.group(1) if m else url

    def _collect_footer_links(self, soup: BeautifulSoup, domain: str) -> List[str]:
        """Collect unique absolute links from the page footer within same origin."""
        links: List[str] = []
        seen: Set[str] = set()
        footer = soup.find("footer")
        if not footer:
            return links
        for a in footer.find_all("a", href=True):
            href: str = a.get("href", "").strip()
            if not href or href.startswith("#"):
                continue
            if href.startswith("http://") or href.startswith("https://"):
                if not href.startswith(domain):
                    continue
                abs_url = href
            else:
                if not href.startswith("/"):
                    href = "/" + href
                abs_url = domain + href
            if abs_url in seen:
                continue
            seen.add(abs_url)
            links.append(abs_url)
        return links

    def _is_blog_link(self, url: str) -> bool:
        s = url.lower()
        return "/blog" in s or s.endswith("/blog/") or "blog." in s

    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        for selector in ["h1", "title", "h2"]:
            el = soup.select_one(selector)
            if el and el.get_text(strip=True):
                return el.get_text(strip=True)
        return None

    def _extract_main_text(self, soup: BeautifulSoup) -> str:
        """Heuristic text extraction: prefer <main> or <article>, else body sans nav/footer."""
        # Remove noise
        for sel in ["script", "style", "noscript", "header", "nav", "footer", "form"]:
            for node in soup.select(sel):
                try:
                    node.decompose()
                except Exception:
                    pass

        container = soup.select_one("main") or soup.select_one("article") or soup.body
        if not container:
            return ""
        text = container.get_text(separator="\n", strip=True)
        # Normalize excessive blank lines
        lines = [ln.strip() for ln in text.splitlines()]
        clean = "\n".join([ln for ln in lines if ln])
        return clean


# Expose a singleton for app/main and API modules
web_scraper = WebScraperService()


