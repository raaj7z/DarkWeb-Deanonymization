# db/queries.py — NEW
# All read/write helpers for the new tables.
import json
import sqlite3
from config import DB_PATH
from db.schema import ensure_schema
from logging_setup import get_logger

log = get_logger('db.queries')


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA busy_timeout=30000')
    return conn


def write_actor_rows(rows):
    """
    Write actor report rows (OSINT entities + stylo posts).
    Detects the type by presence of 'entity_type' vs 'content'.
    """
    if not rows:
        return 0
    conn = get_conn()
    try:
        ensure_schema(conn)
        n = 0
        for r in rows:
            if 'entity_type' in r and 'value' in r:
                conn.execute('''
                    INSERT INTO osint_entities
                    (session_id, actor_id, entity_type, value, normalized,
                     platform, source_url, category, context, occurrences,
                     confidence, confidence_level, source)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                ''', (
                    r.get('session_id'), r.get('actor_id'),
                    r.get('entity_type'), r.get('value'), r.get('normalized'),
                    r.get('platform', 'darkweb'), r.get('source_url'),
                    r.get('category', 'unknown'), r.get('context', ''),
                    r.get('occurrences', 1),
                    r.get('confidence', 0.0), r.get('confidence_level', 'LOW'),
                    r.get('source', 'crawler'),
                ))
                n += 1
            elif 'content' in r:
                conn.execute('''
                    INSERT INTO stylo_posts
                    (session_id, actor_id, username, handle, platform, source_url,
                     content, raw_html_ref, word_count, char_count, lang,
                     timestamp_raw, timestamp_parsed, category, confidence, source)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ''', (
                    r.get('session_id'), r.get('actor_id'),
                    r.get('username'), r.get('handle'),
                    r.get('platform', 'darkweb'), r.get('source_url'),
                    r.get('content'), r.get('raw_html_ref', ''),
                    r.get('word_count', 0), r.get('char_count', 0),
                    r.get('lang', 'en'),
                    r.get('timestamp_raw', ''), r.get('timestamp_parsed', ''),
                    r.get('category', 'unknown'), r.get('confidence', 0.0),
                    r.get('source', 'crawler'),
                ))
                n += 1
        conn.commit()
        return n
    finally:
        conn.close()


def write_network_rows(rows):
    """
    Write network artifacts (TLS, banners, headers, etc.).
    """
    if not rows:
        return 0
    conn = get_conn()
    try:
        ensure_schema(conn)
        n = 0
        for r in rows:
            conn.execute('''
                INSERT INTO network_artifacts
                (session_id, actor_id, artifact_type, source_url, host,
                 ip_address, domain, port, protocol, banner, server_software,
                 ssl_issuer, ssl_san, raw_data, confidence, source)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ''', (
                r.get('session_id'), r.get('actor_id'),
                r.get('artifact_type'), r.get('source_url'),
                r.get('host'), r.get('ip_address'), r.get('domain'),
                r.get('port', 0), r.get('protocol', 'tcp'),
                r.get('banner', ''), r.get('server_software', ''),
                r.get('ssl_issuer', ''),
                json.dumps(r.get('ssl_san', []) or []),
                json.dumps(r.get('raw_data', {}) or {}),
                r.get('confidence', 0.0), r.get('source', 'crawler'),
            ))
            n += 1
        conn.commit()
        return n
    finally:
        conn.close()
