# database.py — v2.0
# FIXED: Never replaces old data, tracks all sessions, full history
import sqlite3
import json
import os
from datetime import datetime
from utils import success, error, info

class Database:
    
    def __init__(self, db_path='data/crawler.db'):
        os.makedirs('data', exist_ok=True)
        self.db_path = db_path
        
        # FIXED: check_same_thread=False for concurrent use
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        
        # FIXED: WAL mode — faster writes, no locking issues
        self.conn.execute('PRAGMA journal_mode=WAL')
        self.conn.execute('PRAGMA synchronous=NORMAL')
        self.conn.execute('PRAGMA cache_size=10000')
        
        self._create_tables()
        success(f"Database: {db_path}")
    
    def _create_tables(self):
        cursor = self.conn.cursor()
        
        # Sessions table — track every run separately
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT UNIQUE,
                target_username TEXT,
                urls_crawled TEXT,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                status TEXT DEFAULT 'running',
                summary TEXT
            )
        ''')
        
        # Search history — never deleted
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS search_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                query_type TEXT,
                query_value TEXT,
                results_count INTEGER,
                searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Sites — INSERT OR IGNORE so old data preserved
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE,
                title TEXT,
                status_code INTEGER,
                alive BOOLEAN,
                server TEXT,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_checked TIMESTAMP,
                check_count INTEGER DEFAULT 1
            )
        ''')
        
        # Site check log — every check recorded
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS site_checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT,
                session_id TEXT,
                status_code INTEGER,
                alive BOOLEAN,
                response_time_ms INTEGER,
                checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Pages — all versions kept
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                site_id INTEGER,
                url TEXT,
                html TEXT,
                text_content TEXT,
                word_count INTEGER,
                crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (site_id) REFERENCES sites(id)
            )
        ''')
        
        # Usernames — with session tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usernames (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                username TEXT,
                source_url TEXT,
                context TEXT,
                pattern_matched TEXT,
                found_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Posts — with session tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                username TEXT,
                content TEXT,
                word_count INTEGER,
                timestamp_found TEXT,
                source_url TEXT,
                extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Links
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                source_url TEXT,
                target_url TEXT,
                link_type TEXT,
                found_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Investigations — full results
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS investigations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                target_username TEXT,
                status TEXT DEFAULT 'running',
                results TEXT,
                confidence_score REAL,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
        ''')
        
        self.conn.commit()
        success("Database tables ready")
    
    # ── SESSION MANAGEMENT ──
    def create_session(self, target_username, urls):
        import uuid
        session_id = str(uuid.uuid4())[:8]
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO sessions (session_id, target_username, urls_crawled, status)
            VALUES (?, ?, ?, 'running')
        ''', (session_id, target_username, json.dumps(urls)))
        self.conn.commit()
        info(f"Session created: {session_id}")
        return session_id
    
    def complete_session(self, session_id, summary):
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE sessions 
            SET status='completed', completed_at=?, summary=?
            WHERE session_id=?
        ''', (datetime.now(), json.dumps(summary), session_id))
        self.conn.commit()
    
    def get_all_sessions(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM sessions ORDER BY started_at DESC')
        return cursor.fetchall()
    
    # ── SEARCH HISTORY ──
    def log_search(self, session_id, query_type, query_value, results_count=0):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO search_history (session_id, query_type, query_value, results_count)
            VALUES (?, ?, ?, ?)
        ''', (session_id, query_type, query_value, results_count))
        self.conn.commit()
    
    def get_search_history(self, limit=20):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM search_history 
            ORDER BY searched_at DESC 
            LIMIT ?
        ''', (limit,))
        return cursor.fetchall()
    
    # ── SITES ──
    def save_site(self, url, title, status_code, alive, server='', session_id='', response_time=0):
        cursor = self.conn.cursor()
        
        # Check if site exists
        existing = cursor.execute(
            'SELECT id, check_count FROM sites WHERE url=?', (url,)
        ).fetchone()
        
        if existing:
            # UPDATE — preserve first_seen, increment check count
            cursor.execute('''
                UPDATE sites 
                SET title=?, status_code=?, alive=?, server=?, 
                    last_checked=?, check_count=check_count+1
                WHERE url=?
            ''', (title, status_code, alive, server, datetime.now(), url))
            site_id = existing['id']
        else:
            # INSERT new site
            cursor.execute('''
                INSERT INTO sites (url, title, status_code, alive, server, last_checked)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (url, title, status_code, alive, server, datetime.now()))
            site_id = cursor.lastrowid
        
        # Always log the check
        cursor.execute('''
            INSERT INTO site_checks (url, session_id, status_code, alive, response_time_ms)
            VALUES (?, ?, ?, ?, ?)
        ''', (url, session_id, status_code, alive, response_time))
        
        self.conn.commit()
        return site_id
    
    # ── PAGES ──
    def save_page(self, session_id, site_id, url, html, text):
        try:
            word_count = len(text.split())
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO pages (session_id, site_id, url, html, text_content, word_count)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (session_id, site_id, url, html[:50000], text[:10000], word_count))
            self.conn.commit()
        except Exception as e:
            error(f"save_page: {e}")
    
    # ── USERNAMES ──
    def save_username(self, session_id, username, source_url, context='', pattern=''):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO usernames (session_id, username, source_url, context, pattern_matched)
                VALUES (?, ?, ?, ?, ?)
            ''', (session_id, username, source_url, context, pattern))
            self.conn.commit()
        except Exception as e:
            error(f"save_username: {e}")
    
    # ── POSTS ──
    def save_post(self, session_id, username, content, timestamp, source_url):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO posts (session_id, username, content, word_count, timestamp_found, source_url)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (session_id, username, content, len(content.split()), timestamp, source_url))
            self.conn.commit()
        except Exception as e:
            error(f"save_post: {e}")
    
    # ── LINKS ──
    def save_link(self, session_id, source_url, target_url, link_type='onion'):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO links (session_id, source_url, target_url, link_type)
                VALUES (?, ?, ?, ?)
            ''', (session_id, source_url, target_url, link_type))
            self.conn.commit()
        except Exception as e:
            error(f"save_link: {e}")
    
    # ── QUERIES ──
    def get_posts_by_username(self, username, session_id=None):
        cursor = self.conn.cursor()
        if session_id:
            cursor.execute(
                'SELECT * FROM posts WHERE username=? AND session_id=?',
                (username, session_id)
            )
        else:
            cursor.execute(
                'SELECT * FROM posts WHERE username=? ORDER BY extracted_at DESC',
                (username,)
            )
        return cursor.fetchall()
    
    def get_all_usernames(self, session_id=None):
        cursor = self.conn.cursor()
        if session_id:
            cursor.execute(
                'SELECT DISTINCT username FROM usernames WHERE session_id=?',
                (session_id,)
            )
        else:
            cursor.execute('SELECT DISTINCT username FROM usernames')
        return [row['username'] for row in cursor.fetchall()]
    
    def get_stats(self, session_id=None):
        cursor = self.conn.cursor()
        stats = {}
        
        if session_id:
            for table in ['usernames', 'posts', 'links']:
                cursor.execute(
                    f'SELECT COUNT(*) as count FROM {table} WHERE session_id=?',
                    (session_id,)
                )
                stats[table] = cursor.fetchone()['count']
            stats['sites'] = cursor.execute(
                'SELECT COUNT(*) as count FROM site_checks WHERE session_id=?',
                (session_id,)
            ).fetchone()['count']
        else:
            for table in ['sites', 'pages', 'usernames', 'posts', 'links', 'sessions']:
                cursor.execute(f'SELECT COUNT(*) as count FROM {table}')
                stats[table] = cursor.fetchone()['count']
        
        return stats
    
    def get_previous_crawls_for_url(self, url):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT sc.*, s.title FROM site_checks sc
            JOIN sites s ON sc.url = s.url
            WHERE sc.url = ?
            ORDER BY sc.checked_at DESC
        ''', (url,))
        return cursor.fetchall()
    
    def close(self):
        self.conn.close()
