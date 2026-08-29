
import time
import random
import re
import json
from bs4 import BeautifulSoup
from datetime import datetime
from utils import get_tor_session, success, error, info, warn, setup_logger
from database import Database

class DarkCrawler:
    
    def __init__(self, db=None, delay=(2, 5), timeout=30, max_retries=3):
        self.session = get_tor_session()
        self.db = db or Database()
        self.delay = delay          # Random delay range between requests
        self.timeout = timeout
        self.max_retries = max_retries
        self.visited = set()        # Track visited URLs
        self.logger = setup_logger()
        
        # Username extraction patterns
        self.username_patterns = [
            r'@([A-Za-z0-9_\-\.]{3,20})',
            r'User:\s*([A-Za-z0-9_\-\.]{3,20})',
            r'Posted by:\s*([A-Za-z0-9_\-\.]{3,20})',
            r'Author:\s*([A-Za-z0-9_\-\.]{3,20})',
            r'by\s+([A-Za-z0-9_\-\.]{3,20})\s+\|',
            r'<username>([^<]+)</username>',
            r'class="username">([^<]+)<',
            r'class="author">([^<]+)<',
        ]
        
        # Timestamp patterns
        self.time_patterns = [
            r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}(?::\d{2})?',
            r'\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}',
            r'\d{2}:\d{2}(?::\d{2})?\s*(?:UTC|GMT|EST|PST|IST)',
            r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4}',
        ]
        
        info("DarkCrawler initialized")
    
    def _random_delay(self):
        """Random delay between requests — avoid detection"""
        delay = random.uniform(*self.delay)
        time.sleep(delay)
    
    def _refresh_session(self):
        """Get fresh Tor session with new identity"""
        self.session = get_tor_session()
        warn("Tor session refreshed")
    
    def fetch(self, url):
        """
        Fetch a URL through Tor with retry logic
        Solves: network latency, disappearing nodes
        """
        if url in self.visited:
            return None
        
        for attempt in range(self.max_retries):
            try:
                self._random_delay()
                
                response = self.session.get(
                    url,
                    timeout=self.timeout,
                    allow_redirects=True
                )
                
                self.visited.add(url)
                
                if response.status_code == 200:
                    success(f"Fetched: {url[:60]}...")
                    return response
                
                elif response.status_code == 403:
                    warn(f"403 Forbidden — possible CAPTCHA/auth: {url}")
                    return None
                
                elif response.status_code == 404:
                    error(f"404 Not found: {url}")
                    return None
                
                else:
                    warn(f"Status {response.status_code}: {url}")
                    
            except Exception as e:
                warn(f"Attempt {attempt+1}/{self.max_retries} failed: {e}")
                self._refresh_session()
                time.sleep(random.uniform(5, 10))
        
        error(f"Failed after {self.max_retries} attempts: {url}")
        return None
    
    def extract_usernames(self, html, url):
        """Extract all usernames from page HTML"""
        usernames = set()
        
        # Try patterns on raw HTML
        for pattern in self.username_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            usernames.update(matches)
        
        # Try BeautifulSoup for structured extraction
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Common forum username classes
            for class_name in ['username', 'author', 'user', 'poster', 'nick']:
                elements = soup.find_all(class_=re.compile(class_name, re.I))
                for el in elements:
                    text = el.get_text().strip()
                    if 3 <= len(text) <= 25 and text.replace('_','').replace('-','').isalnum():
                        usernames.add(text)
        except:
            pass
        
        # Save to database
        for username in usernames:
            self.db.save_username(username, url)
        
        return list(usernames)
    
    def extract_timestamps(self, html):
        """Extract posting timestamps — reveals timezone/location"""
        timestamps = []
        for pattern in self.time_patterns:
            found = re.findall(pattern, html, re.IGNORECASE)
            timestamps.extend(found)
        return list(set(timestamps))
    
    def extract_links(self, html, base_url):
        """Extract all links including .onion links"""
        links = {'onion': [], 'surface': [], 'relative': []}
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            for a in soup.find_all('a', href=True):
                href = a['href'].strip()
                
                if '.onion' in href:
                    links['onion'].append(href)
                    self.db.save_link(base_url, href)
                elif href.startswith('http'):
                    links['surface'].append(href)
                elif href.startswith('/'):
                    links['relative'].append(href)
            
            # Also find onion links in plain text
            onion_pattern = r'http[s]?://[a-z2-7]{16,56}\.onion[^\s"\'<>]*'
            text_onions = re.findall(onion_pattern, html, re.IGNORECASE)
            links['onion'].extend(text_onions)
            
        except Exception as e:
            error(f"Link extraction error: {e}")
        
        return links
    
    def extract_posts(self, html, target_username=None):
        """Extract forum posts — optionally filter by username"""
        posts = []
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Common post container patterns
            post_selectors = [
                {'class': re.compile(r'post|message|content|reply', re.I)},
                {'id': re.compile(r'post|message|reply', re.I)},
            ]
            
            for selector in post_selectors:
                elements = soup.find_all(attrs=selector)
                for el in elements:
                    text = el.get_text(separator=' ', strip=True)
                    if len(text) > 20:
                        post = {
                            'text': text[:2000],
                            'html': str(el)[:5000]
                        }
                        
                        # Filter by target username if provided
                        if target_username:
                            if target_username.lower() in text.lower():
                                posts.append(post)
                        else:
                            posts.append(post)
                
                if posts:
                    break
            
        except Exception as e:
            error(f"Post extraction error: {e}")
        
        return posts
    
    def extract_emails(self, text):
        """Extract email addresses"""
        pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        return list(set(re.findall(pattern, text)))
    
    def extract_crypto_addresses(self, text):
        """Extract cryptocurrency addresses — common on dark web"""
        patterns = {
            'bitcoin': r'\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b',
            'monero': r'\b4[0-9AB][1-9A-HJ-NP-Za-km-z]{93}\b',
            'ethereum': r'\b0x[a-fA-F0-9]{40}\b',
        }
        addresses = {}
        for crypto, pattern in patterns.items():
            found = re.findall(pattern, text)
            if found:
                addresses[crypto] = found
        return addresses
    
    def crawl(self, url, target_username=None, depth=1):
        """
        Main crawl function
        Returns complete data extracted from URL
        """
        info(f"Crawling: {url}")
        info(f"Target username: {target_username or 'All'}")
        info(f"Depth: {depth}")
        
        result = {
            'url': url,
            'crawled_at': datetime.utcnow().isoformat(),
            'usernames': [],
            'posts': [],
            'timestamps': [],
            'links': {},
            'emails': [],
            'crypto_addresses': {},
            'title': '',
            'success': False
        }
        
        # Fetch the page
        response = self.fetch(url)
        if not response:
            result['error'] = 'Failed to fetch'
            return result
        
        html = response.text
        text = BeautifulSoup(html, 'html.parser').get_text(separator=' ')
        
        # Extract page title
        title_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
        result['title'] = title_match.group(1).strip() if title_match else 'No title'
        
        # Save to database
        site_id = self.db.save_site(
            url=url,
            title=result['title'],
            status_code=response.status_code,
            alive=True,
            server=response.headers.get('Server', '')
        )
        self.db.save_page(site_id, url, html[:50000], text[:10000])
        
        # Extract all data
        result['usernames']         = self.extract_usernames(html, url)
        result['timestamps']        = self.extract_timestamps(html)
        result['links']             = self.extract_links(html, url)
        result['posts']             = self.extract_posts(html, target_username)
        result['emails']            = self.extract_emails(text)
        result['crypto_addresses']  = self.extract_crypto_addresses(text)
        result['success']           = True
        
        # Save posts to database
        for post in result['posts']:
            self.db.save_post(
                username=target_username or 'unknown',
                content=post['text'],
                timestamp=result['timestamps'][0] if result['timestamps'] else '',
                source_url=url
            )
        
        # Recursive crawl if depth > 1
        if depth > 1:
            onion_links = result['links'].get('onion', [])[:5]
            for link in onion_links:
                if link not in self.visited:
                    info(f"Following link (depth {depth-1}): {link}")
                    sub_result = self.crawl(link, target_username, depth-1)
                    result['posts'].extend(sub_result.get('posts', []))
                    result['usernames'].extend(sub_result.get('usernames', []))
        
        # Print summary
        success(f"Crawl complete!")
        info(f"Usernames found: {len(result['usernames'])}")
        info(f"Posts extracted: {len(result['posts'])}")
        info(f"Links found: {len(result['links'].get('onion', []))} onion, {len(result['links'].get('surface', []))} surface")
        info(f"Emails: {len(result['emails'])}")
        info(f"Crypto addresses: {result['crypto_addresses']}")
        
        return result
    
    def crawl_multiple(self, urls, target_username=None):
        """Crawl multiple URLs"""
        all_results = []
        
        info(f"Starting multi-crawl: {len(urls)} URLs")
        
        for i, url in enumerate(urls):
            info(f"\n[{i+1}/{len(urls)}] Processing: {url}")
            result = self.crawl(url, target_username)
            all_results.append(result)
            
            # Longer delay between different sites
            time.sleep(random.uniform(5, 10))
        
        # Summary
        total_usernames = sum(len(r['usernames']) for r in all_results)
        total_posts = sum(len(r['posts']) for r in all_results)
        
        success(f"\nMulti-crawl complete!")
        success(f"Total usernames: {total_usernames}")
        success(f"Total posts: {total_posts}")
        
        return all_results
