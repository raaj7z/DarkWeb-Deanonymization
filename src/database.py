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

        # Crypto addresses table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS crypto_addresses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                currency TEXT,
                address TEXT,
                context TEXT,
                source_url TEXT,
                found_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Misconfigs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS misconfigs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                url TEXT,
                misconfig_type TEXT,
                severity TEXT,
                detail TEXT,
                found_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Server fingerprints table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS server_fingerprints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                url TEXT,
                server_software TEXT,
                backend_language TEXT,
                framework TEXT,
                database_hints TEXT,
                os_hints TEXT,
                cdn TEXT,
                ssl_info TEXT,
                found_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Profiles table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                source_url TEXT,
                pgp_keys TEXT,
                contact_methods TEXT,
                communication_channels TEXT,
                aliases TEXT,
                found_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Posts with timing table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS timed_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                source_url TEXT,
                username TEXT,
                content TEXT,
                word_count INTEGER,
                timestamps TEXT,
                hour_of_day INTEGER,
                timezone_estimate TEXT,
                has_crypto BOOLEAN,
                has_links BOOLEAN,
                extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Timing analysis table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS timing_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                target_username TEXT,
                peak_hours TEXT,
                average_hour REAL,
                timezone_estimate TEXT,
                activity_pattern TEXT,
                total_posts INTEGER,
                analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Service banners table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS service_banners (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                host TEXT,
                port INTEGER,
                banner TEXT,
                service TEXT,
                version TEXT,
                vulnerabilities TEXT,
                found_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Descriptor checks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS descriptor_checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                onion_address TEXT,
                reachable BOOLEAN,
                inconsistencies TEXT,
                clearnet_refs TEXT,
                exposed_ips TEXT,
                metadata TEXT,
                checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Trust links table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trust_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                source_url TEXT,
                from_actor TEXT,
                to_actor TEXT,
                link_type TEXT,
                wallet_address TEXT,
                pgp_signature TEXT,
                trust_score TEXT,
                found_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Timeline crawls table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS timeline_crawls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                url TEXT,
                crawled_at TEXT,
                crawled_at_unix REAL,
                date TEXT,
                hour INTEGER,
                day_of_week TEXT,
                week_number INTEGER,
                descriptor_issues INTEGER,
                trust_links_found INTEGER,
                new_content BOOLEAN DEFAULT FALSE
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

    # ── SAVING EXTENDED DATA ──
    def save_crypto(self, session_id, currency, address, context, source_url):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO crypto_addresses 
                (session_id, currency, address, context, source_url)
                VALUES (?, ?, ?, ?, ?)
            ''', (session_id, currency, address, context, source_url))
            self.conn.commit()
        except Exception as e:
            error(f"save_crypto: {e}")

    def save_misconfig(self, session_id, url, misconfig_type, severity, detail):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO misconfigs 
                (session_id, url, misconfig_type, severity, detail)
                VALUES (?, ?, ?, ?, ?)
            ''', (session_id, url, misconfig_type, severity, detail))
            self.conn.commit()
        except Exception as e:
            error(f"save_misconfig: {e}")

    def save_fingerprint(self, session_id, url, fingerprint):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO server_fingerprints
                (session_id, url, server_software, backend_language,
                 framework, database_hints, os_hints, cdn)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                session_id, url,
                fingerprint.get('server_software', ''),
                fingerprint.get('backend_language', ''),
                fingerprint.get('framework', ''),
                json.dumps(fingerprint.get('database_hints', [])),
                json.dumps(fingerprint.get('os_hints', [])),
                fingerprint.get('cdn', '')
            ))
            self.conn.commit()
        except Exception as e:
            error(f"save_fingerprint: {e}")

    def save_profile(self, session_id, url, profile):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO profiles
                (session_id, source_url, pgp_keys, contact_methods,
                 communication_channels, aliases)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                session_id, url,
                json.dumps(profile.get('pgp_keys', [])),
                json.dumps(profile.get('contact_methods', {})),
                json.dumps(profile.get('communication_channels', [])),
                json.dumps(profile.get('aliases', []))
            ))
            self.conn.commit()
        except Exception as e:
            error(f"save_profile: {e}")

    def save_timed_post(self, session_id, url, post, timezone_estimate):
        try:
            cursor = self.conn.cursor()
            hours = []
            for ts in post.get('timestamps', []):
                import re
                h = re.search(r'(\d{2}):\d{2}', ts)
                if h:
                    hours.append(int(h.group(1)))
            avg_hour = sum(hours)/len(hours) if hours else 0
            
            cursor.execute('''
                INSERT INTO timed_posts
                (session_id, source_url, username, content, word_count,
                 timestamps, hour_of_day, timezone_estimate, has_crypto, has_links)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                session_id, url,
                post.get('username', 'unknown'),
                post.get('text', '')[:3000],
                post.get('word_count', 0),
                json.dumps(post.get('timestamps', [])),
                round(avg_hour),
                timezone_estimate,
                post.get('has_crypto', False),
                post.get('has_links', False)
            ))
            self.conn.commit()
        except Exception as e:
            error(f"save_timed_post: {e}")

    def save_timing_analysis(self, session_id, username, analysis):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO timing_analysis
                (session_id, target_username, peak_hours, average_hour,
                 timezone_estimate, activity_pattern, total_posts)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                session_id, username,
                json.dumps(analysis.get('peak_hours', [])),
                analysis.get('average_hour', 0),
                analysis.get('timezone_estimate', ''),
                analysis.get('activity_pattern', ''),
                analysis.get('total_timestamps', 0)
            ))
            self.conn.commit()
        except Exception as e:
            error(f"save_timing_analysis: {e}")

    def save_banner(self, session_id, banner_data):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO service_banners
                (session_id, host, port, banner, service, version, vulnerabilities)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                session_id,
                banner_data.get('host', ''),
                banner_data.get('port', 0),
                banner_data.get('banner', '')[:500],
                banner_data.get('service', ''),
                banner_data.get('version', ''),
                json.dumps(banner_data.get('vulnerabilities', []))
            ))
            self.conn.commit()
        except Exception as e:
            error(f"save_banner: {e}")

    def save_descriptor(self, session_id, descriptor):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO descriptor_checks
                (session_id, onion_address, reachable, inconsistencies,
                 clearnet_refs, exposed_ips, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                session_id,
                descriptor.get('onion_address', ''),
                descriptor.get('reachable', False),
                json.dumps(descriptor.get('inconsistencies', [])),
                json.dumps(descriptor.get('metadata', {}).get('clearnet_refs', [])),
                json.dumps(descriptor.get('metadata', {}).get('exposed_ips', [])),
                json.dumps(descriptor.get('metadata', {}))
            ))
            self.conn.commit()
        except Exception as e:
            error(f"save_descriptor: {e}")

    def save_trust_links(self, session_id, url, trust_data):
        try:
            cursor = self.conn.cursor()
            
            # Save relationship edges
            for edge in trust_data.get('relationship_edges', []):
                cursor.execute('''
                    INSERT INTO trust_links
                    (session_id, source_url, from_actor, to_actor, link_type)
                    VALUES (?, ?, ?, ?, ?)
                ''', (session_id, url, edge['from'], edge['to'], edge['type']))
            
            # Save wallet links
            for wallet in trust_data.get('wallet_links', []):
                cursor.execute('''
                    INSERT INTO trust_links
                    (session_id, source_url, link_type, wallet_address)
                    VALUES (?, ?, ?, ?)
                ''', (session_id, url, 'wallet', wallet['address']))
            
            self.conn.commit()
        except Exception as e:
            error(f"save_trust_links: {e}")

    def save_timeline_crawl(self, session_id, url, timeline, descriptor, trust_links):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO timeline_crawls
                (session_id, url, crawled_at, crawled_at_unix, date,
                 hour, day_of_week, week_number, descriptor_issues, trust_links_found)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                session_id, url,
                timeline['crawled_at'],
                timeline['crawled_at_unix'],
                timeline['date'],
                timeline['hour'],
                timeline['day_of_week'],
                timeline['week_number'],
                len(descriptor.get('inconsistencies', [])),
                len(trust_links.get('relationship_edges', []))
            ))
            self.conn.commit()
        except Exception as e:
            error(f"save_timeline_crawl: {e}")
    
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

    def query_timeline(self, start_date, end_date, url=None):
        """Query crawls within a timeline — required by NTRO"""
        cursor = self.conn.cursor()
        if url:
            cursor.execute('''
                SELECT * FROM timeline_crawls
                WHERE date BETWEEN ? AND ? AND url = ?
                ORDER BY crawled_at ASC
            ''', (start_date, end_date, url))
        else:
            cursor.execute('''
                SELECT * FROM timeline_crawls
                WHERE date BETWEEN ? AND ?
                ORDER BY crawled_at ASC
            ''', (start_date, end_date))
        return cursor.fetchall()

    def get_actor_relationships(self, username=None):
        """Get trust relationship graph data"""
        cursor = self.conn.cursor()
        if username:
            cursor.execute('''
                SELECT * FROM trust_links
                WHERE from_actor = ? OR to_actor = ?
            ''', (username, username))
        else:
            cursor.execute('SELECT * FROM trust_links')
        return cursor.fetchall()
    
    def close(self):
        self.conn.close()
