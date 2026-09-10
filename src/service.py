# service.py — Pure functions for CLI and (later) any UI.
# No menu logic, no print prompts — just callable actions.
import os
import json
import uuid
from datetime import datetime
from pathlib import Path

from config import OUTPUT_DIR, REPORT_DIR
from database import Database
from crawler import DarkCrawler
from ai_cleaner import AICleaner
from db import queries as dbq
from utils import get_tor_session, verify_tor, info, success, error, warn


def new_session_id():
    """Short 8-char session id — matches your original format."""
    return str(uuid.uuid4())[:8]


def check_tor():
    """Verify Tor is up. Returns (bool, message)."""
    try:
        s = get_tor_session()
        ok = verify_tor(s)
        return ok, "Tor OK" if ok else "Tor verification failed"
    except Exception as e:
        return False, f"Tor error: {e}"


def run_crawl(urls, target_username=None,
              workers=3, use_js=False,
              rotate_circuits=True, rotate_every=10,
              session_id=None, db=None):
    """
    Run one crawl session over the given URLs.

    Returns dict:
      {
        session_id,
        results,          # raw crawler results
        actor_rows,       # flattened OSINT + posts for report 1
        network_rows,     # flattened network artifacts for report 2
        actor_count,
        network_count,
        summary
      }
    """
    if not urls:
        return {'error': 'no urls provided'}

    db = db or Database()
    session_id = session_id or new_session_id()

    # create session row
    try:
        db.create_session(target_username, urls)
    except Exception:
        pass

    info(f"[service] starting crawl — session {session_id}, {len(urls)} urls")

    crawler = DarkCrawler(
        db=db,
        session_id=session_id,
        max_workers=workers,
        use_js=use_js,
        rotate_circuits=rotate_circuits,
        rotate_every=rotate_every,
    )

    results = crawler.crawl_concurrent(
        urls, target_username=target_username, use_js=use_js
    )

    # Flatten results into two buckets
    actor_rows, network_rows = flatten_results(results, session_id)

    # Persist to new tables
    try:
        dbq.write_actor_rows(actor_rows)
        dbq.write_network_rows(network_rows)
    except Exception as e:
        warn(f"[service] DB write failed: {e}")

    summary = {
        'urls_crawled': len(urls),
        'urls_ok': sum(1 for r in results if r.get('success')),
        'actor_rows': len(actor_rows),
        'network_rows': len(network_rows),
    }

    try:
        db.complete_session(session_id, summary)
    except Exception:
        pass

    try:
        crawler.close()
    except Exception:
        pass

    return {
        'session_id': session_id,
        'results': results,
        'actor_rows': actor_rows,
        'network_rows': network_rows,
        'actor_count': len(actor_rows),
        'network_count': len(network_rows),
        'summary': summary,
    }


def flatten_results(results, session_id):
    """
    Takes crawler results, runs the AI cleaner on each page's intel,
    returns (actor_rows, network_rows).
    """
    cleaner = AICleaner(session_id=session_id)
    actor_rows, network_rows = [], []

    for r in results:
        intel = r.get('intel') or {}
        merged = dict(intel)
        merged.setdefault('url', r.get('url'))
        merged.setdefault('headers', {})
        # Fill in crawler-level extras the cleaner might want
        if 'emails' not in merged:
            merged['emails'] = r.get('emails', [])
        if 'usernames' not in merged:
            merged['usernames'] = r.get('usernames', [])

        try:
            a, n = cleaner.clean(merged)
            actor_rows.extend(a)
            network_rows.extend(n)
        except Exception as e:
            warn(f"[service] cleaner failed on {r.get('url','?')[:40]}: {e}")

    return actor_rows, network_rows

def run_autonomous(urls, target_username=None,
                   hours=1, interval_minutes=30,
                   workers=3, session_id=None, db=None):
    """
    Blocking call — runs the crawler in autonomous mode.
    For CLI, this is fine.
    """
    db = db or Database()
    session_id = session_id or new_session_id()
    try:
        db.create_session(target_username, urls)
    except Exception:
        pass

    crawler = DarkCrawler(db=db, session_id=session_id, max_workers=workers)
    result = crawler.autonomous_crawl(
        seed_urls=urls,
        target_username=target_username,
        duration_hours=hours,
        interval_minutes=interval_minutes,
    )
    try:
        crawler.close()
    except Exception:
        pass
    return {'session_id': session_id, **result}


def get_session_summary(session_id, db=None):
    """Pull a session's stats from the new tables."""
    db = db or Database()
    conn = dbq.get_conn()
    try:
        cur = conn.cursor()
        rows = {}
        for table in ('osint_entities', 'stylo_posts', 'network_artifacts'):
            r = cur.execute(
                f'SELECT COUNT(*) FROM {table} WHERE session_id=?',
                (session_id,),
            ).fetchone()
            rows[table] = r[0] if r else 0
        return rows
    finally:
        conn.close()


def write_session_reports(session_id, actor_rows, network_rows):
    """
    Delegates to reports.report_builder.produce_all_reports.
    Writes actor_report.json + network_report.json + CSV/JSON/JSONL exports.
    """
    from reports.report_builder import produce_all_reports
    return produce_all_reports(session_id, actor_rows, network_rows)
