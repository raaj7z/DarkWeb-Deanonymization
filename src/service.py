
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from config import OUTPUT_DIR, REPORT_DIR
from database import Database
from crawler import DarkCrawler
from ai_cleaner import AICleaner
from db import queries as dbq
from utils import get_tor_session, verify_tor, info, success, error, warn


def new_session_id() -> str:
    """Return the crawler-compatible short session id format."""
    return str(uuid.uuid4())[:8]


def check_tor() -> Tuple[bool, str]:
    """
    Verify that the crawler can reach the Tor network.

    This function deliberately does not print or expose the investigator's
    public IP address.
    """
    try:
        session = get_tor_session()
        ok = verify_tor(session)
        return ok, "Tor OK" if ok else "Tor verification failed"
    except Exception as exc:
        return False, f"Tor error: {exc}"


def _ensure_exact_session(
    crawler_db: Database,
    session_id: str,
    target_username: Optional[str],
    urls: Sequence[str],
) -> str:
    """
    Ensure the crawler DB contains the exact session id supplied by PRALAYX.

    Database.create_session() generates its own id. During platform execution
    that would create two different IDs for one crawl. We therefore insert the
    platform-owned session id directly when one is supplied.
    """
    if not session_id:
        return crawler_db.create_session(target_username, list(urls))

    conn = getattr(crawler_db, "conn", None)
    if conn is None:
        return session_id

    try:
        conn.execute(
            """
            INSERT OR IGNORE INTO sessions
            (session_id, target_username, urls_crawled, status)
            VALUES (?, ?, ?, 'running')
            """,
            (
                session_id,
                target_username,
                json.dumps(list(urls)),
            ),
        )
        conn.commit()
        return session_id
    except sqlite3.Error as exc:
        # If the crawler DB schema is unavailable, keep the caller's stable id.
        # The actual crawl should still be allowed to run.
        warn(f"[service] unable to register exact session id: {exc}")
        return session_id


def _mark_session_complete(
    crawler_db: Database,
    session_id: str,
    summary: Dict[str, Any],
) -> None:
    try:
        crawler_db.complete_session(session_id, summary)
    except Exception as exc:
        warn(f"[service] session completion update failed: {exc}")


def _close_crawler(crawler: Any) -> None:
    try:
        crawler.close()
    except Exception as exc:
        warn(f"[service] crawler close failed: {exc}")


def run_crawl(
    urls: Sequence[str],
    target_username: Optional[str] = None,
    workers: int = 3,
    use_js: bool = False,
    rotate_circuits: bool = True,
    rotate_every: int = 10,
    session_id: Optional[str] = None,
    db: Optional[Database] = None,
) -> Dict[str, Any]:
    """
    Run one crawl session.

    ``session_id`` is PRALAYX-owned when supplied. This is important because
    the platform creates the investigation/session/run IDs before launching
    the worker.

    Returns:
        {
            "session_id": str,
            "results": list,
            "actor_rows": list,
            "network_rows": list,
            "actor_count": int,
            "network_count": int,
            "summary": dict,
            "status": "COMPLETED" | "NO_RESULTS" | "ERROR"
        }
    """
    clean_urls = [
        str(url).strip()
        for url in (urls or [])
        if str(url).strip()
    ]

    if not clean_urls:
        return {
            "session_id": session_id or new_session_id(),
            "results": [],
            "actor_rows": [],
            "network_rows": [],
            "actor_count": 0,
            "network_count": 0,
            "summary": {
                "urls_crawled": 0,
                "urls_ok": 0,
                "actor_rows": 0,
                "network_rows": 0,
            },
            "status": "NO_RESULTS",
            "error": "no urls provided",
        }

    crawler_db = db or Database()
    exact_session_id = session_id or new_session_id()

    _ensure_exact_session(
        crawler_db,
        exact_session_id,
        target_username,
        clean_urls,
    )

    info(
        f"[service] starting crawl — session "
        f"{exact_session_id}, {len(clean_urls)} url(s)"
    )

    crawler: Optional[DarkCrawler] = None

    try:
        crawler = DarkCrawler(
            db=crawler_db,
            session_id=exact_session_id,
            max_workers=max(1, int(workers)),
            use_js=bool(use_js),
            rotate_circuits=bool(rotate_circuits),
            rotate_every=max(1, int(rotate_every)),
        )

        results = crawler.crawl_concurrent(
            clean_urls,
            target_username=target_username,
            use_js=bool(use_js),
        )

        results = list(results or [])

        actor_rows, network_rows = flatten_results(
            results,
            exact_session_id,
        )

        # Keep the crawler's own normalized tables populated. These are
        # historical/native crawler records; PRALAYX has a separate DB.
        try:
            if actor_rows:
                dbq.write_actor_rows(actor_rows)
            if network_rows:
                dbq.write_network_rows(network_rows)
        except Exception as exc:
            # A native-table write failure must not masquerade as a crawl
            # failure when the crawler itself produced results.
            warn(f"[service] native DB write failed: {exc}")

        urls_ok = sum(
            1 for result in results
            if isinstance(result, dict) and result.get("success")
        )

        summary = {
            "urls_crawled": len(clean_urls),
            "urls_ok": urls_ok,
            "actor_rows": len(actor_rows),
            "network_rows": len(network_rows),
            "completed_at": datetime.utcnow().isoformat(timespec="seconds"),
        }

        status = (
            "COMPLETED"
            if results or actor_rows or network_rows
            else "NO_RESULTS"
        )

        _mark_session_complete(
            crawler_db,
            exact_session_id,
            summary,
        )

        return {
            "session_id": exact_session_id,
            "results": results,
            "actor_rows": actor_rows,
            "network_rows": network_rows,
            "actor_count": len(actor_rows),
            "network_count": len(network_rows),
            "summary": summary,
            "status": status,
        }

    except Exception as exc:
        error(f"[service] crawl failed: {exc}")

        summary = {
            "urls_crawled": len(clean_urls),
            "urls_ok": 0,
            "actor_rows": 0,
            "network_rows": 0,
            "error": str(exc),
            "completed_at": datetime.utcnow().isoformat(timespec="seconds"),
        }

        _mark_session_complete(
            crawler_db,
            exact_session_id,
            summary,
        )

        return {
            "session_id": exact_session_id,
            "results": [],
            "actor_rows": [],
            "network_rows": [],
            "actor_count": 0,
            "network_count": 0,
            "summary": summary,
            "status": "ERROR",
            "error": str(exc),
        }

    finally:
        if crawler is not None:
            _close_crawler(crawler)


def flatten_results(
    results: Iterable[Dict[str, Any]],
    session_id: str,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Normalize crawler output into the two native report streams.

    Stream 1:
        actor_rows
        usernames, emails, wallets, PGP, posts, aliases, etc.

    Stream 2:
        network_rows
        TLS, banners, server-status, exposed infrastructure,
        descriptors and other infrastructure artifacts.
    """
    cleaner = AICleaner(session_id=session_id)
    actor_rows: List[Dict[str, Any]] = []
    network_rows: List[Dict[str, Any]] = []

    for result in results or []:
        if not isinstance(result, dict):
            continue

        intel = result.get("intel") or {}
        merged = dict(intel)

        merged.setdefault("url", result.get("url"))
        merged.setdefault("headers", {})

        if "emails" not in merged:
            merged["emails"] = result.get("emails", [])

        if "usernames" not in merged:
            merged["usernames"] = result.get("usernames", [])

        try:
            actor_part, network_part = cleaner.clean(merged)

            if actor_part:
                actor_rows.extend(actor_part)

            if network_part:
                network_rows.extend(network_part)

        except Exception as exc:
            warn(
                "[service] cleaner failed on "
                f"{str(result.get('url', '?'))[:80]}: {exc}"
            )

    return actor_rows, network_rows


def run_autonomous(
    urls: Sequence[str],
    target_username: Optional[str] = None,
    hours: float = 1,
    interval_minutes: int = 30,
    workers: int = 3,
    session_id: Optional[str] = None,
    db: Optional[Database] = None,
) -> Dict[str, Any]:
    """
    Blocking autonomous crawl entrypoint for CLI/background workers.

    The same externally supplied session_id is preserved when provided.
    """
    clean_urls = [
        str(url).strip()
        for url in (urls or [])
        if str(url).strip()
    ]

    crawler_db = db or Database()
    exact_session_id = session_id or new_session_id()

    _ensure_exact_session(
        crawler_db,
        exact_session_id,
        target_username,
        clean_urls,
    )

    crawler: Optional[DarkCrawler] = None

    try:
        crawler = DarkCrawler(
            db=crawler_db,
            session_id=exact_session_id,
            max_workers=max(1, int(workers)),
        )

        result = crawler.autonomous_crawl(
            seed_urls=clean_urls,
            target_username=target_username,
            duration_hours=float(hours),
            interval_minutes=max(1, int(interval_minutes)),
        )

        return {
            "session_id": exact_session_id,
            **(result or {}),
        }

    finally:
        if crawler is not None:
            _close_crawler(crawler)


def get_session_summary(
    session_id: str,
    db: Optional[Database] = None,
) -> Dict[str, int]:
    """
    Pull native crawler counts for one session.

    This is intentionally a crawler-side summary. PRALAYX's canonical
    investigation counts live in the platform database.
    """
    crawler_db = db or Database()

    conn = getattr(crawler_db, "conn", None)
    if conn is None:
        return {}

    rows: Dict[str, int] = {}

    for table in (
        "osint_entities",
        "stylo_posts",
        "network_artifacts",
    ):
        try:
            row = conn.execute(
                f'SELECT COUNT(*) FROM "{table}" WHERE session_id=?',
                (session_id,),
            ).fetchone()

            rows[table] = int(row[0]) if row else 0

        except sqlite3.Error:
            # Older crawler databases may not contain the normalized tables.
            rows[table] = 0

    return rows


def write_session_reports(
    session_id: str,
    actor_rows: Sequence[Dict[str, Any]],
    network_rows: Sequence[Dict[str, Any]],
) -> Any:
    """
    Generate native crawler report artifacts.

    PRALAYX additionally registers these files in its own report registry.
    This function does not delete or overwrite historical crawler reports.
    """
    from reports.report_builder import produce_all_reports

    return produce_all_reports(
        session_id,
        list(actor_rows or []),
        list(network_rows or []),
    )


def crawl_for_platform(
    urls: Sequence[str],
    investigation_id: str,
    session_id: str,
    target_username: Optional[str] = None,
    workers: int = 3,
    use_js: bool = False,
    rotate_circuits: bool = True,
    rotate_every: int = 10,
    db: Optional[Database] = None,
) -> Dict[str, Any]:
    """
    Explicit platform adapter.

    The investigation_id is carried in the returned envelope so the platform
    worker can associate every result/report with its PRALAYX investigation.
    The crawler itself continues to use its established session_id.
    """
    result = run_crawl(
        urls=urls,
        target_username=target_username,
        workers=workers,
        use_js=use_js,
        rotate_circuits=rotate_circuits,
        rotate_every=rotate_every,
        session_id=session_id,
        db=db,
    )

    result["investigation_id"] = investigation_id
    result["platform_session_id"] = session_id

    return result
