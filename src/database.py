# SQLite storage for all crawled data
import sqlite3
import json
import os
from datetime import datetime
from utils import success, error, info

class Database:
    
    def __init__(self, db_path='data/crawler.db'):
        os.makedirs('data', exist_ok=True)
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
        success(f"Database initialized: {db_path}")
    
    def _create_tables(self):
        cursor = self.conn.cursor()
        
        # Sites table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE,
                title TEXT,
                status_code INTEGER,
                alive BOOLEAN,
                server TEXT,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Pages table — raw crawled content
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                site_id INTEGER,
                url TEXT,
                html TEXT,
                text_content TEXT,
                crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (site_id) REFERENCES sites(id)
            )
        ''')
        
        # Usernames table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usernames (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                source_url TEXT,
                context TEXT,
                found_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Posts table — extracted forum posts
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                content TEXT,
                timestamp TEXT,
                source_url TEXT,
                extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Links table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_url TEXT,
                target_url TEXT,
                found_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Investigations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS investigations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_username TEXT,
                status TEXT DEFAULT 'running',
                results TEXT,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
        ''')
        
        self.conn.commit()
    
    def save_site(self, url, title, status_code, alive, server=''):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO sites 
                (url, title, status_code, alive, server, last_checked)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (url, title, status_code, alive, server, datetime.now()))
            self.conn.commit()
            return cursor.lastrowid
        except Exception as e:
            error(f"DB save_site error: {e}")
            return None
    
    def save_page(self, site_id, url, html, text):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO pages (site_id, url, html, text_content)
                VALUES (?, ?, ?, ?)
            ''', (site_id, url, html, text))
            self.conn.commit()
        except Exception as e:
            error(f"DB save_page error: {e}")
    
    def save_username(self, username, source_url, context=''):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO usernames (username, source_url, context)
                VALUES (?, ?, ?)
            ''', (username, source_url, context))
            self.conn.commit()
        except Exception as e:
            error(f"DB save_username error: {e}")
    
    def save_post(self, username, content, timestamp, source_url):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO posts (username, content, timestamp, source_url)
                VALUES (?, ?, ?, ?)
            ''', (username, content, timestamp, source_url))
            self.conn.commit()
        except Exception as e:
            error(f"DB save_post error: {e}")
    
    def save_link(self, source_url, target_url):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO links (source_url, target_url)
                VALUES (?, ?)
            ''', (source_url, target_url))
            self.conn.commit()
        except Exception as e:
            error(f"DB save_link error: {e}")
    
    def get_posts_by_username(self, username):
        cursor = self.conn.cursor()
        cursor.execute(
            'SELECT * FROM posts WHERE username = ?', (username,)
        )
        return cursor.fetchall()
    
    def get_all_usernames(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT DISTINCT username FROM usernames')
        return [row['username'] for row in cursor.fetchall()]
    
    def save_investigation(self, username, results):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO investigations 
                (target_username, status, results, completed_at)
                VALUES (?, ?, ?, ?)
            ''', (username, 'completed', 
                  json.dumps(results), datetime.now()))
            self.conn.commit()
            return cursor.lastrowid
        except Exception as e:
            error(f"DB save_investigation error: {e}")
            return None
    
    def get_stats(self):
        cursor = self.conn.cursor()
        stats = {}
        for table in ['sites', 'pages', 'usernames', 'posts', 'links']:
            cursor.execute(f'SELECT COUNT(*) as count FROM {table}')
            stats[table] = cursor.fetchone()['count']
        return stats
    
    def close(self):
        self.conn.close()
