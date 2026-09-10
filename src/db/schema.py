# db/schema.py — NEW
# Adds new tables + standard columns on top of your existing crawler.db.
# Safe to run multiple times — all statements are idempotent.
import sqlite3
from config import DB_PATH
from logging_setup import get_logger

log = get_logger('db.schema')

# Standard columns to add to existing tables
STANDARD_COLUMNS = [
    ('session_id', 'TEXT'),
    ('actor_id',   'TEXT'),
    ('source',     "TEXT DEFAULT 'crawler'"),
    ('confidence', 'REAL DEFAULT 0.0'),
    ('updated_at', 'TIMESTAMP'),
]

# New tables (CREATE TABLE IF NOT EXISTS — safe to re-run)
NEW_TABLES = {
    'osint_entities': '''
        CREATE TABLE IF NOT EXISTS osint_entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT, actor_id TEXT,
            entity_type TEXT, value TEXT, normalized TEXT,
            platform TEXT, source_url TEXT, category TEXT,
            context TEXT, occurrences INTEGER DEFAULT 1,
            confidence REAL, confidence_level TEXT,
            source TEXT DEFAULT 'crawler',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP
        )''',
    'stylo_posts': '''
        CREATE TABLE IF NOT EXISTS stylo_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT, actor_id TEXT,
            username TEXT, handle TEXT, platform TEXT, source_url TEXT,
            content TEXT, raw_html_ref TEXT,
            word_count INTEGER, char_count INTEGER, lang TEXT,
            timestamp_raw TEXT, timestamp_parsed TEXT,
            category TEXT, confidence REAL,
            source TEXT DEFAULT 'crawler',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP
        )''',
    'network_artifacts': '''
        CREATE TABLE IF NOT EXISTS network_artifacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT, actor_id TEXT,
            artifact_type TEXT, source_url TEXT,
            host TEXT, ip_address TEXT, domain TEXT,
            port INTEGER, protocol TEXT,
            banner TEXT, server_software TEXT,
            ssl_issuer TEXT, ssl_san TEXT, raw_data TEXT,
            confidence REAL,
            source TEXT DEFAULT 'crawler',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP
        )''',
    'actor_ids': '''
        CREATE TABLE IF NOT EXISTS actor_ids (
            actor_id TEXT PRIMARY KEY,
            session_id TEXT,
            primary_handle TEXT,
            first_seen TIMESTAMP,
            last_seen TIMESTAMP,
            notes TEXT
        )''',
    'jobs': '''
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT UNIQUE, session_id TEXT,
            job_type TEXT, status TEXT DEFAULT 'pending',
            progress REAL DEFAULT 0.0, message TEXT,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ended_at TIMESTAMP
        )''',
}


def _table_exists(conn, name):
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (name,)
    ).fetchone()
    return row is not None


def _column_names(conn, table):
    return {r[1] for r in conn.execute(f'PRAGMA table_info("{table}")').fetchall()}


def ensure_schema(conn=None):
    """
    Create new tables and add standard columns to existing ones.
    Safe to call repeatedly.
    """
    own = conn is None
    if own:
        conn = sqlite3.connect(DB_PATH)
    try:
        # Create new tables
        for name, ddl in NEW_TABLES.items():
            conn.execute(ddl)

        # Add standard columns to existing tables (idempotent)
        existing = [
            'sessions', 'sites', 'pages', 'usernames', 'posts',
            'links', 'crypto_addresses', 'misconfigs',
            'server_fingerprints', 'profiles', 'timed_posts',
            'timing_analysis', 'service_banners',
            'descriptor_checks', 'trust_links', 'timeline_crawls',
        ]
        for tbl in existing:
            if not _table_exists(conn, tbl):
                continue
            cols = _column_names(conn, tbl)
            for col, coltype in STANDARD_COLUMNS:
                if col not in cols:
                    try:
                        conn.execute(
                            f'ALTER TABLE "{tbl}" ADD COLUMN {col} {coltype}'
                        )
                    except sqlite3.OperationalError as e:
                        log.warning(f"could not add {col} to {tbl}: {e}")

        # Indexes for fast queries
        for idx in (
            'CREATE INDEX IF NOT EXISTS idx_osint_session ON osint_entities(session_id)',
            'CREATE INDEX IF NOT EXISTS idx_osint_type ON osint_entities(entity_type)',
            'CREATE INDEX IF NOT EXISTS idx_stylo_session ON stylo_posts(session_id)',
            'CREATE INDEX IF NOT EXISTS idx_net_session ON network_artifacts(session_id)',
            'CREATE INDEX IF NOT EXISTS idx_net_type ON network_artifacts(artifact_type)',
        ):
            conn.execute(idx)

        conn.commit()
        log.info("schema ensured")
    finally:
        if own:
            conn.close()
