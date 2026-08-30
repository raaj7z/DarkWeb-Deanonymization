# crawler.py — v2.0
import time
import random
import re
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
from datetime import datetime
from utils import get_tor_session, success, error, info, warn, setup_logger
from database import Database

class DarkCrawler:
    
    def __init__(self, db=None, session_id=None, delay=(1, 3),
                 timeout=30, max_retries=3, max_workers=5):
        self.session = get_tor_session()
        self.db = db or Database()
        self.session_id = session_id or 'default'
        self.delay = delay
        self.timeout = timeout
        self.max_retries = max_retries
        self.max_workers = max_workers  # Concurrent threads
        self.visited = set()
        self.logger = setup_logger()
        
        self.username_patterns = [
            (r'@([A-Za-z0-9_\-\.]{3,20})',           '@mention'),
            (r'User:\s*([A-Za-z0-9_\-\.]{3,20})',    'User: prefix'),
            (r'Posted by:\s*([A-Za-z0-9_\-\.]{3,20})','Posted by:'),
            (r'Author:\s*([A-Za-z0-9_\-\.]{3,20})',  'Author:'),
            (r'by\s+([A-Za-z0-9_\-\.]{3,20})\s+\|', 'by | format'),
            (r'class="username">([^<]{3,20})<',       'CSS class'),
            (r'class="author">([^<]{3,20})<',         'CSS author'),
            (r'class="nick">([^<]{3,20})<',           'CSS nick'),
        ]
        
        self.time_patterns = [
            r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}(?::\d{2})?',
            r'\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}',
            r'\d{2}:\d{2}(?::\d{2})?\s*(?:UTC|GMT|EST|PST|IST)',
            r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4}',
        ]
        
        info(f"DarkCrawler v2.0 ready | Workers: {max_workers} | Session: {session_id}")
    
    def _random_delay(self):
        time.sleep(random.uniform(*self.delay))
    
    def _refresh_session(self):
        self.session = get_tor_session()
        warn("Session refreshed with new Tor identity")
    
    def fetch(self, url):
        if url in self.visited:
            return None
        
        for attempt in range(self.max_retries):
            try:
                self._random_delay()
                start = time.time()
                
                response = self.session.get(
                    url, timeout=self.timeout,
                    allow_redirects=True
                )
                
                response_time = int((time.time() - start) * 1000)
                self.visited.add(url)
                
                if response.status_code == 200:
                    success(f"[{response_time}ms] {url[:60]}")
                    return response, response_time
                
                elif response.status_code == 403:
                    warn(f"403 — CAPTCHA/Auth wall: {url}")
                    return None, 0
                
                else:
                    warn(f"HTTP {response.status_code}: {url}")
                    return None, 0
                    
            except Exception as e:
                warn(f"Attempt {attempt+1}/{self.max_retries}: {e}")
                self._refresh_session()
                time.sleep(random.uniform(3, 7))
        
        error(f"Failed after {self.max_retries} attempts: {url}")
        return None, 0
    
    def extract_usernames(self, html, url):
        usernames = []
        seen = set()
        
        for pattern, pattern_name in self.username_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            for match in matches:
                if match not in seen and len(match) >= 3:
                    seen.add(match)
                    usernames.append(match)
                    self.db.save_username(
                        self.session_id, match, url,
                        pattern=pattern_name
                    )
        
        # BeautifulSoup extraction
        try:
            soup = BeautifulSoup(html, 'html.parser')
            for cls in ['username', 'author', 'user', 'poster', 'nick', 'handle']:
                for el in soup.find_all(class_=re.compile(cls, re.I)):
                    text = el.get_text().strip()
                    if 3 <= len(text) <= 25 and text not in seen:
                        if re.match(r'^[A-Za-z0-9_\-\.]+$', text):
                            seen.add(text)
                            usernames.append(text)
                            self.db.save_username(
                                self.session_id, text, url,
                                pattern=f'bs4-class-{cls}'
                            )
        except:
            pass
        
        return usernames
    
    def extract_timestamps(self, html):
        timestamps = []
        for pattern in self.time_patterns:
            found = re.findall(pattern, html, re.IGNORECASE)
            timestamps.extend(found)
        return list(set(timestamps))
    
    def extract_links(self, html, base_url):
        links = {'onion': [], 'surface': [], 'relative': []}
        try:
            soup = BeautifulSoup(html, 'html.parser')
            for a in soup.find_all('a', href=True):
                href = a['href'].strip()
                if '.onion' in href:
                    links['onion'].append(href)
                    self.db.save_link(self.session_id, base_url, href, 'onion')
                elif href.startswith('http'):
                    links['surface'].append(href)
                elif href.startswith('/'):
                    links['relative'].append(href)
            
            # Find text-based onion addresses
            onion_re = r'http[s]?://[a-z2-7]{16,56}\.onion[^\s"\'<>]*'
            for match in re.findall(onion_re, html, re.I):
                if match not in links['onion']:
                    links['onion'].append(match)
        except:
            pass
        return links
    
    def extract_posts(self, html, target_username=None):
        posts = []
        try:
            soup = BeautifulSoup(html, 'html.parser')
            selectors = [
                {'class': re.compile(r'post|message|content|reply|entry', re.I)},
                {'id': re.compile(r'post|message|reply', re.I)},
            ]
            for selector in selectors:
                elements = soup.find_all(attrs=selector)
                for el in elements:
                    text = el.get_text(separator=' ', strip=True)
                    if len(text) > 30:
                        if target_username:
                            if target_username.lower() in text.lower():
                                posts.append({'text': text[:2000]})
                        else:
                            posts.append({'text': text[:2000]})
                if posts:
                    break
        except:
            pass
        return posts
    
    def extract_emails(self, text):
        pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        return list(set(re.findall(pattern, text)))
    
    def extract_crypto(self, text):
        patterns = {
            'bitcoin':  r'\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b',
            'monero':   r'\b4[0-9AB][1-9A-HJ-NP-Za-km-z]{93}\b',
            'ethereum': r'\b0x[a-fA-F0-9]{40}\b',
        }
        return {
            k: list(set(re.findall(v, text)))
            for k, v in patterns.items()
            if re.findall(v, text)
        }
    
    def crawl_single(self, url, target_username=None):
        """Crawl a single URL — used in concurrent mode"""
        result = {
            'url': url,
            'crawled_at': datetime.utcnow().isoformat(),
            'usernames': [], 'posts': [],
            'timestamps': [], 'links': {},
            'emails': [], 'crypto': {},
            'title': '', 'success': False
        }
        
        response, response_time = self.fetch(url)
        if not response:
            result['error'] = 'Fetch failed'
            return result
        
        html = response.text
        soup = BeautifulSoup(html, 'html.parser')
        text = soup.get_text(separator=' ')
        
        # Extract title
        title_tag = soup.find('title')
        result['title'] = title_tag.get_text().strip() if title_tag else 'No title'
        
        # Save to DB
        site_id = self.db.save_site(
            url=url, title=result['title'],
            status_code=response.status_code,
            alive=True,
            server=response.headers.get('Server', ''),
            session_id=self.session_id,
            response_time=response_time
        )
        self.db.save_page(self.session_id, site_id, url, html, text)
        
        # Extract everything
        result['usernames']  = self.extract_usernames(html, url)
        result['timestamps'] = self.extract_timestamps(html)
        result['links']      = self.extract_links(html, url)
        result['posts']      = self.extract_posts(html, target_username)
        result['emails']     = self.extract_emails(text)
        result['crypto']     = self.extract_crypto(text)
        result['success']    = True
        
        # Save posts
        for post in result['posts']:
            self.db.save_post(
                self.session_id,
                target_username or 'unknown',
                post['text'],
                result['timestamps'][0] if result['timestamps'] else '',
                url
            )
        
        return result
    
    def crawl_concurrent(self, urls, target_username=None):
        """
        FASTER: Crawl multiple URLs concurrently using ThreadPoolExecutor
        """
        all_results = []
        
        info(f"Concurrent crawl: {len(urls)} URLs | {self.max_workers} workers")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self.crawl_single, url, target_username): url
                for url in urls
            }
            
            for future in as_completed(futures):
                url = futures[future]
                try:
                    result = future.result(timeout=60)
                    all_results.append(result)
                    
                    if result['success']:
                        success(f"Done: {url[:50]}")
                        info(f"  → Usernames: {len(result['usernames'])}")
                        info(f"  → Posts: {len(result['posts'])}")
                    else:
                        error(f"Failed: {url[:50]}")
                        
                except Exception as e:
                    error(f"Thread error for {url}: {e}")
        
        return all_results
