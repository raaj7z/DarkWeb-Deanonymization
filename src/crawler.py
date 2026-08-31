# crawler.py — v3.0
# NEW: CAPTCHA bypass + JS rendering + Tor circuit rotation
import time
import random
import re
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
from datetime import datetime
from utils import get_tor_session, success, error, info, warn, setup_logger
from database import Database
from captcha_handler import CaptchaHandler
from tor_controller import TorController
from js_renderer import JSRenderer

class DarkCrawler:
    
    def __init__(self, db=None, session_id=None,
                 delay=(1, 3), timeout=30,
                 max_retries=3, max_workers=5,
                 use_js=False, rotate_circuits=True,
                 rotate_every=10):
        
        self.session = get_tor_session()
        self.db = db or Database()
        self.session_id = session_id or 'default'
        self.delay = delay
        self.timeout = timeout
        self.max_retries = max_retries
        self.max_workers = max_workers
        self.visited = set()
        self.request_count = 0
        self.rotate_every = rotate_every
        self.logger = setup_logger()
        
        # NEW: Initialize advanced components
        self.captcha = CaptchaHandler()
        
        # Tor circuit rotation
        self.tor_ctrl = None
        if rotate_circuits:
            try:
                self.tor_ctrl = TorController()
                info("Circuit rotation: ENABLED")
            except:
                warn("Circuit rotation: DISABLED")
        
        # JS rendering
        self.js_renderer = None
        if use_js:
            self.js_renderer = JSRenderer()
            if self.js_renderer.available:
                info("JS rendering: ENABLED")
            else:
                warn("JS rendering: DISABLED")
        
        self.username_patterns = [
            (r'@([A-Za-z0-9_\-\.]{3,20})',            '@mention'),
            (r'User:\s*([A-Za-z0-9_\-\.]{3,20})',     'User:'),
            (r'Posted by:\s*([A-Za-z0-9_\-\.]{3,20})', 'Posted by:'),
            (r'Author:\s*([A-Za-z0-9_\-\.]{3,20})',   'Author:'),
            (r'by\s+([A-Za-z0-9_\-\.]{3,20})\s+\|',  'by|format'),
            (r'class="username">([^<]{3,20})<',        'CSS username'),
            (r'class="author">([^<]{3,20})<',          'CSS author'),
            (r'class="nick">([^<]{3,20})<',            'CSS nick'),
        ]
        
        self.time_patterns = [
            r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}(?::\d{2})?',
            r'\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}',
            r'\d{2}:\d{2}(?::\d{2})?\s*(?:UTC|GMT|EST|PST|IST)',
            r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4}',
        ]
        
        info(f"DarkCrawler v3.0 | Workers: {max_workers} | Session: {session_id}")
    
    def _random_delay(self):
        time.sleep(random.uniform(*self.delay))
    
    def _refresh_session(self):
        self.session = get_tor_session()
        warn("New Tor session")
    
    def _maybe_rotate_circuit(self):
        """Rotate Tor circuit every N requests"""
        self.request_count += 1
        if self.tor_ctrl and self.request_count % self.rotate_every == 0:
            info(f"Rotating circuit after {self.rotate_every} requests")
            self.tor_ctrl.new_circuit()
            self._refresh_session()
    
    def fetch(self, url, force_js=False):
        """
        Smart fetch — tries JS rendering first if enabled,
        falls back to requests. Handles CAPTCHAs automatically.
        """
        if url in self.visited:
            return None, 0
        
        self._maybe_rotate_circuit()
        
        # Try JS rendering if available and requested
        if force_js and self.js_renderer and self.js_renderer.available:
            result = self.js_renderer.render(url)
            if result:
                self.visited.add(url)
                return result, 0
        
        # Standard requests fetch with retry
        for attempt in range(self.max_retries):
            try:
                self._random_delay()
                start = time.time()
                
                response = self.session.get(
                    url, timeout=self.timeout,
                    allow_redirects=True
                )
                
                response_time = int((time.time() - start) * 1000)
                
                # Check for CAPTCHA
                is_captcha, reason = self.captcha.is_captcha(
                    response.text, response.status_code
                )
                
                if is_captcha:
                    warn(f"CAPTCHA detected: {reason}")
                    warn(f"URL: {url[:60]}")
                    
                    # Try bypass
                    bypass = self.captcha.bypass_strategy(url, self.session)
                    if bypass:
                        self.visited.add(url)
                        return bypass, response_time
                    
                    # Fallback to JS renderer
                    if self.js_renderer and self.js_renderer.available:
                        info("Trying JS renderer for CAPTCHA bypass...")
                        result = self.js_renderer.render(url, wait_time=8)
                        if result:
                            self.visited.add(url)
                            return result, response_time
                    
                    error(f"CAPTCHA bypass failed: {url[:50]}")
                    return None, 0
                
                if response.status_code == 200:
                    success(f"[{response_time}ms] {url[:55]}")
                    self.visited.add(url)
                    return response, response_time
                
                else:
                    warn(f"HTTP {response.status_code}: {url[:50]}")
                    
            except Exception as e:
                warn(f"Attempt {attempt+1}: {str(e)[:50]}")
                self._refresh_session()
                time.sleep(random.uniform(3, 8))
        
        error(f"Failed: {url[:50]}")
        return None, 0
    
    def get_html(self, response):
        """Extract HTML from either requests response or JS render result"""
        if isinstance(response, dict):
            return response.get('html', '')
        return response.text if response else ''
    
    def extract_usernames(self, html, url):
        usernames = []
        seen = set()
        
        for pattern, name in self.username_patterns:
            for match in re.findall(pattern, html, re.IGNORECASE):
                if match not in seen and 3 <= len(match) <= 25:
                    seen.add(match)
                    usernames.append(match)
                    self.db.save_username(
                        self.session_id, match, url, pattern=name
                    )
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            for cls in ['username', 'author', 'user', 'poster', 'nick']:
                for el in soup.find_all(class_=re.compile(cls, re.I)):
                    text = el.get_text().strip()
                    if 3 <= len(text) <= 25 and text not in seen:
                        if re.match(r'^[A-Za-z0-9_\-\.]+$', text):
                            seen.add(text)
                            usernames.append(text)
                            self.db.save_username(
                                self.session_id, text, url,
                                pattern=f'bs4-{cls}'
                            )
        except:
            pass
        
        return usernames
    
    def extract_timestamps(self, html):
        timestamps = []
        for pattern in self.time_patterns:
            timestamps.extend(re.findall(pattern, html, re.IGNORECASE))
        return list(set(timestamps))
    
    def extract_links(self, html, base_url):
        links = {'onion': [], 'surface': [], 'relative': []}
        try:
            soup = BeautifulSoup(html, 'html.parser')
            for a in soup.find_all('a', href=True):
                href = a['href'].strip()
                if '.onion' in href:
                    links['onion'].append(href)
                    self.db.save_link(
                        self.session_id, base_url, href, 'onion'
                    )
                elif href.startswith('http'):
                    links['surface'].append(href)
                elif href.startswith('/'):
                    links['relative'].append(href)
            
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
                for el in soup.find_all(attrs=selector):
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
        return list(set(re.findall(
            r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text
        )))
    
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
    
    def crawl_single(self, url, target_username=None, use_js=False):
        """Crawl one URL with full intelligence extraction"""
        result = {
            'url': url,
            'crawled_at': datetime.utcnow().isoformat(),
            'usernames': [], 'posts': [],
            'timestamps': [], 'links': {},
            'emails': [], 'crypto': {},
            'title': '', 'success': False,
            'captcha_detected': False,
            'js_rendered': False
        }
        
        response, response_time = self.fetch(url, force_js=use_js)
        if not response:
            result['error'] = 'Fetch failed'
            return result
        
        # Handle both requests response and JS render dict
        html = self.get_html(response)
        result['js_rendered'] = isinstance(response, dict)
        
        soup = BeautifulSoup(html, 'html.parser')
        text = soup.get_text(separator=' ')
        
        title_tag = soup.find('title')
        result['title'] = title_tag.get_text().strip() if title_tag else 'No title'
        
        site_id = self.db.save_site(
            url=url, title=result['title'],
            status_code=200 if isinstance(response, dict) else response.status_code,
            alive=True,
            server='' if isinstance(response, dict) else response.headers.get('Server', ''),
            session_id=self.session_id,
            response_time=response_time
        )
        self.db.save_page(self.session_id, site_id, url, html, text)
        
        result['usernames']  = self.extract_usernames(html, url)
        result['timestamps'] = self.extract_timestamps(html)
        result['links']      = self.extract_links(html, url)
        result['posts']      = self.extract_posts(html, target_username)
        result['emails']     = self.extract_emails(text)
        result['crypto']     = self.extract_crypto(text)
        result['success']    = True
        
        for post in result['posts']:
            self.db.save_post(
                self.session_id,
                target_username or 'unknown',
                post['text'],
                result['timestamps'][0] if result['timestamps'] else '',
                url
            )
        
        # Take screenshot if JS rendered
        if result['js_rendered'] and self.js_renderer:
            safe_name = url.replace('://', '_').replace('/', '_')[:30]
            self.js_renderer.take_screenshot(safe_name)
        
        return result
    
    def crawl_concurrent(self, urls, target_username=None, use_js=False):
        """Fast concurrent crawling with all features"""
        all_results = []
        captcha_count = 0
        js_count = 0
        
        info(f"Crawling {len(urls)} URLs | "
             f"Workers: {self.max_workers} | "
             f"JS: {'ON' if use_js else 'OFF'} | "
             f"Circuit rotation: {'ON' if self.tor_ctrl else 'OFF'}")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(
                    self.crawl_single, url, target_username, use_js
                ): url for url in urls
            }
            
            for future in as_completed(futures):
                url = futures[future]
                try:
                    result = future.result(timeout=120)
                    all_results.append(result)
                    
                    if result['success']:
                        mode = "JS" if result['js_rendered'] else "HTTP"
                        success(f"[{mode}] {url[:45]}")
                        info(f"  Users: {len(result['usernames'])} | "
                             f"Posts: {len(result['posts'])} | "
                             f"Links: {len(result['links'].get('onion',[]))}")
                        
                        if result['js_rendered']:
                            js_count += 1
                    else:
                        error(f"Failed: {url[:45]}")
                        
                    if result.get('captcha_detected'):
                        captcha_count += 1
                        
                except Exception as e:
                    error(f"Thread error: {e}")
        
        # Final summary
        success(f"\n{'='*50}")
        success(f"CRAWL COMPLETE")
        success(f"URLs processed : {len(all_results)}")
        success(f"JS rendered    : {js_count}")
        success(f"CAPTCHAs hit   : {captcha_count}")
        success(f"Circuit rotates: {self.request_count // self.rotate_every}")
        success(f"{'='*50}")
        
        return all_results
    
    def close(self):
        if self.js_renderer:
            self.js_renderer.close()
        if self.tor_ctrl:
            self.tor_ctrl.close()
