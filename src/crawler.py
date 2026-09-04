# crawler.py — v3.0
# NEW: CAPTCHA bypass + JS rendering + Tor circuit rotation
import time
import random
import re
import json
import socket
import ssl
import threading
from intel_extractor import IntelExtractor
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
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
                     
        self.intel = IntelExtractor()
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
        
        # Full intelligence extraction
        intel = self.intel.full_extract(
            url=url,
            html=html,
            headers=dict(response.headers) if not isinstance(response, dict) else {},
            target_username=target_username
        )
        
        # Save all intel to database
        # Crypto
        for currency, addresses in intel['crypto_addresses'].items():
            for addr in addresses:
                context = self.intel.analyze_crypto_context(text, addr)
                self.db.save_crypto(self.session_id, currency, addr, context, url)
        
        # Misconfigs
        for finding in intel['misconfigs']['found']:
            severity = intel['misconfigs']['severity'].get(finding.split(':')[0], 'MEDIUM')
            self.db.save_misconfig(self.session_id, url, finding, severity, finding)
        
        # Server fingerprint
        self.db.save_fingerprint(self.session_id, url, intel['server_fingerprint'])
        
        # Profiles
        self.db.save_profile(self.session_id, url, intel['profiles'])
        
        # Timed posts
        tz = intel['timing_analysis'].get('timezone_estimate', '')
        for post in intel['posts_with_timing']:
            self.db.save_timed_post(self.session_id, url, post, tz)
        
        # Timing analysis
        if intel['timing_analysis'] and target_username:
            self.db.save_timing_analysis(
                self.session_id, target_username, intel['timing_analysis']
            )
        
        # Add intel to result
        result['intel'] = intel
        result['crypto_addresses'] = intel['crypto_addresses']
        result['misconfigs'] = intel['misconfigs']
        result['server_fingerprint'] = intel['server_fingerprint']
        result['profiles'] = intel['profiles']
        result['timing_analysis'] = intel['timing_analysis']
        
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
    
    def grab_service_banner(self, host, port, timeout=5):
        """
        Grab service banners from open ports
        Default banners reveal real server software — key for origin matching
        """
        banner_data = {
            'host': host,
            'port': port,
            'banner': '',
            'service': '',
            'version': '',
            'vulnerabilities': []
        }
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((host, port))
            
            # Send basic probe
            probes = {
                80:   b'HEAD / HTTP/1.0\r\n\r\n',
                443:  b'HEAD / HTTP/1.0\r\n\r\n',
                21:   b'',  # FTP sends banner automatically
                22:   b'',  # SSH sends banner automatically
                25:   b'',  # SMTP sends banner automatically
                3306: b'',  # MySQL sends banner automatically
            }
            
            probe = probes.get(port, b'')
            if probe:
                sock.send(probe)
            
            # Receive banner
            banner = sock.recv(1024).decode('utf-8', errors='ignore').strip()
            sock.close()
            
            banner_data['banner'] = banner
            
            # Parse service from banner
            if 'SSH' in banner:
                banner_data['service'] = 'SSH'
                ver = re.search(r'SSH-[\d\.]+-(.+)', banner)
                if ver:
                    banner_data['version'] = ver.group(1)
                    
            elif 'HTTP' in banner or 'Server:' in banner:
                banner_data['service'] = 'HTTP'
                server = re.search(r'Server:\s*(.+)', banner)
                if server:
                    banner_data['version'] = server.group(1).strip()
                    
            elif '220' in banner and 'FTP' in banner.upper():
                banner_data['service'] = 'FTP'
                
            elif '220' in banner and ('SMTP' in banner.upper() or 'mail' in banner.lower()):
                banner_data['service'] = 'SMTP'
                
            elif '5.5' in banner or '8.0' in banner or 'mysql' in banner.lower():
                banner_data['service'] = 'MySQL'
            
            # Check for default/unchanged banners — misconfiguration indicator
            default_banners = [
                'Apache/2.4.41',
                'nginx/1.18.0',
                'OpenSSH_7.9',
                'ProFTPD',
                'Postfix ESMTP',
            ]
            
            for default in default_banners:
                if default.lower() in banner.lower():
                    banner_data['vulnerabilities'].append(
                        f'Default banner exposed: {default}'
                    )
            
            success(f"Banner [{port}]: {banner[:60]}")
            
        except Exception as e:
            banner_data['error'] = str(e)
        
        return banner_data
    
    def check_tor_descriptor(self, onion_address):
        """
        Check Tor hidden service descriptor for inconsistencies
        Descriptor mismatches can reveal real server information
        """
        descriptor = {
            'onion_address': onion_address,
            'reachable': False,
            'inconsistencies': [],
            'metadata': {}
        }
        
        try:
            # Extract just the onion hostname
            if '/' in onion_address:
                hostname = onion_address.split('/')[2]
            else:
                hostname = onion_address
            
            # Try to fetch the site
            response, _ = self.fetch(onion_address)
            if not response:
                descriptor['inconsistencies'].append('Site unreachable')
                return descriptor
            
            html = self.get_html(response)
            headers = {}
            if not isinstance(response, dict):
                headers = dict(response.headers)
            
            descriptor['reachable'] = True
            
            # Check for inconsistencies
            
            # 1. Server header mismatch
            server = headers.get('Server', '')
            if server:
                descriptor['metadata']['server'] = server
                
            # 2. Date header timezone mismatch
            date_header = headers.get('Date', '')
            if date_header:
                descriptor['metadata']['server_date'] = date_header
                # If server date differs significantly from expected — flag it
                descriptor['inconsistencies'].append(
                    f'Server date exposed: {date_header}'
                )
            
            # 3. Clearnet references in HTML
            clearnet_refs = re.findall(
                r'https?://(?!.*\.onion)[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}',
                html
            )
            if clearnet_refs:
                descriptor['inconsistencies'].append(
                    f'Clearnet URLs found: {list(set(clearnet_refs))[:5]}'
                )
                descriptor['metadata']['clearnet_refs'] = list(set(clearnet_refs))
            
            # 4. IP addresses exposed in HTML
            ip_pattern = r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'
            exposed_ips = re.findall(ip_pattern, html)
            # Filter out localhost and private ranges
            public_ips = [ip for ip in exposed_ips 
                         if not ip.startswith(('127.', '192.168.', '10.', '172.'))]
            if public_ips:
                descriptor['inconsistencies'].append(
                    f'Public IPs exposed: {list(set(public_ips))}'
                )
                descriptor['metadata']['exposed_ips'] = list(set(public_ips))
            
            # 5. Email addresses that could reveal operator
            emails = re.findall(
                r'[a-zA-Z0-9._%+-]+@(?!.*\.onion)[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
                html
            )
            if emails:
                descriptor['inconsistencies'].append(
                    f'Clearnet emails found: {list(set(emails))}'
                )
                descriptor['metadata']['clearnet_emails'] = list(set(emails))
            
            if descriptor['inconsistencies']:
                warn(f"Descriptor inconsistencies: {len(descriptor['inconsistencies'])}")
                for inc in descriptor['inconsistencies']:
                    warn(f"  → {inc}")
            
        except Exception as e:
            descriptor['error'] = str(e)
        
        return descriptor
    
    def match_ssl_to_clearnet(self, onion_url):
        """
        Check SSL certificate SANs to find clearnet domain
        This is the most powerful origin server identification technique
        SSL cert SANs often contain the real domain name
        """
        result = {
            'onion_url': onion_url,
            'clearnet_domains': [],
            'origin_server_hints': [],
            'confidence': 'LOW'
        }
        
        try:
            # Extract hostname
            hostname = onion_url.replace('https://', '').replace('http://', '').split('/')[0]
            
            # Try HTTPS
            if not onion_url.startswith('https://'):
                return result
            
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            # Route through Tor
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as raw_sock:
                # Connect through SOCKS5 Tor proxy
                raw_sock.connect(('127.0.0.1', 9050))
                
                with context.wrap_socket(
                    raw_sock, server_hostname=hostname
                ) as ssl_sock:
                    cert = ssl_sock.getpeercert(binary_form=False)
                    
                    # Extract Subject Alternative Names
                    san = cert.get('subjectAltName', [])
                    for san_type, san_value in san:
                        if san_type == 'DNS':
                            if '.onion' not in san_value:
                                # Clearnet domain in SSL cert!
                                result['clearnet_domains'].append(san_value)
                                result['origin_server_hints'].append(
                                    f'SSL SAN clearnet domain: {san_value}'
                                )
                    
                    # Check Subject CN
                    subject = dict(x[0] for x in cert.get('subject', []))
                    cn = subject.get('commonName', '')
                    if cn and '.onion' not in cn:
                        result['clearnet_domains'].append(cn)
                        result['origin_server_hints'].append(
                            f'SSL CN clearnet: {cn}'
                        )
                    
                    # Check Issuer for CA info
                    issuer = dict(x[0] for x in cert.get('issuer', []))
                    result['certificate_issuer'] = issuer
                    
                    if result['clearnet_domains']:
                        result['confidence'] = 'HIGH'
                        success(f"CLEARNET DOMAINS FOUND: {result['clearnet_domains']}")
                        
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def extract_trust_links(self, html, url):
        """
        Extract trust relationships between actors
        Marketplaces have vendor ratings, trust scores, vouches
        This builds the relationship graph NTRO wants
        """
        trust_data = {
            'vendor_profiles': [],
            'trust_scores': [],
            'vouches': [],
            'pgp_signatures': [],
            'wallet_links': [],
            'relationship_edges': []  # For graph building
        }
        
        soup = BeautifulSoup(html, 'html.parser')
        text = soup.get_text()
        
        # Extract vendor ratings/trust scores
        rating_patterns = [
            r'(?:rating|trust|score|reputation)[\s:]+(\d+(?:\.\d+)?)\s*(?:/\s*\d+)?',
            r'(\d+(?:\.\d+)?)\s*(?:stars?|/5|/10)\s*(?:rating|trust)',
            r'trusted\s+(?:vendor|seller|member)',
            r'(\d+)\s+(?:successful|completed)\s+(?:transactions|orders|deals)',
        ]
        
        for pattern in rating_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                trust_data['trust_scores'].extend(matches)
        
        # Extract PGP signatures — links actors across platforms
        pgp_sig_pattern = r'-----BEGIN PGP SIGNATURE-----.*?-----END PGP SIGNATURE-----'
        sigs = re.findall(pgp_sig_pattern, html, re.DOTALL)
        trust_data['pgp_signatures'] = sigs
        
        # Extract vouches/references between actors
        vouch_patterns = [
            r'(?:vouched?|verified|trusted)\s+by\s+([A-Za-z0-9_\-]{3,25})',
            r'([A-Za-z0-9_\-]{3,25})\s+(?:vouches?|verifies?|trusts?)\s+(?:for\s+)?([A-Za-z0-9_\-]{3,25})',
            r'ref(?:erred|erence)?\s+by\s+([A-Za-z0-9_\-]{3,25})',
        ]
        
        for pattern in vouch_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                for match in matches:
                    if isinstance(match, tuple):
                        trust_data['relationship_edges'].append({
                            'from': match[0],
                            'to': match[1] if len(match) > 1 else 'unknown',
                            'type': 'vouch',
                            'source': url
                        })
                    else:
                        trust_data['vouches'].append(match)
        
        # Extract wallet trust links — same wallet = same actor
        bitcoin_pattern = r'\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b'
        wallets = re.findall(bitcoin_pattern, text)
        
        for wallet in set(wallets):
            trust_data['wallet_links'].append({
                'address': wallet,
                'type': 'bitcoin',
                'source_url': url,
                'context': self._get_context(text, wallet, 100)
            })
        
        # Extract vendor profiles
        vendor_selectors = [
            {'class_': re.compile(r'vendor|seller|merchant|trader', re.I)},
            {'class_': re.compile(r'profile|user-info|member', re.I)},
        ]
        
        for selector in vendor_selectors:
            elements = soup.find_all(attrs=selector)
            for el in elements[:10]:
                vendor_text = el.get_text(separator=' ', strip=True)
                if vendor_text and len(vendor_text) > 10:
                    trust_data['vendor_profiles'].append({
                        'text': vendor_text[:500],
                        'source': url
                    })
            if trust_data['vendor_profiles']:
                break
        
        if any([trust_data['trust_scores'], trust_data['vouches'],
                trust_data['relationship_edges'], trust_data['wallet_links']]):
            info(f"  Trust links found:")
            info(f"    Scores: {len(trust_data['trust_scores'])}")
            info(f"    Relationships: {len(trust_data['relationship_edges'])}")
            info(f"    Wallets: {len(trust_data['wallet_links'])}")
        
        return trust_data
    
    def _get_context(self, text, keyword, window=150):
        """Get surrounding context for a keyword"""
        idx = text.find(keyword)
        if idx == -1:
            return ''
        start = max(0, idx - window)
        end = min(len(text), idx + len(keyword) + window)
        return text[start:end].strip()
    
    def autonomous_crawl(self, seed_urls, target_username=None,
                         duration_hours=1, interval_minutes=30):
        """
        Autonomous continuous crawling mode
        Runs without manual input — required by NTRO problem statement
        Monitors for new content and changes over time
        """
        end_time = datetime.now() + timedelta(hours=duration_hours)
        crawl_count = 0
        
        info(f"Autonomous mode started")
        info(f"Duration: {duration_hours} hours")
        info(f"Interval: {interval_minutes} minutes")
        info(f"Seeds: {len(seed_urls)} URLs")
        info(f"Will stop at: {end_time.strftime('%H:%M:%S')}")
        
        all_discovered_urls = set(seed_urls)
        
        while datetime.now() < end_time:
            crawl_count += 1
            info(f"\n=== Autonomous Crawl #{crawl_count} ===")
            info(f"Time remaining: {end_time - datetime.now()}")
            info(f"URLs in queue: {len(all_discovered_urls)}")
            
            # Crawl current batch
            current_urls = list(all_discovered_urls)
            results = self.crawl_concurrent(
                current_urls[:10],  # Max 10 per cycle
                target_username=target_username
            )
            
            # Discover new URLs from results
            new_urls = set()
            for result in results:
                links = result.get('links', {})
                onion_links = links.get('onion', [])
                for link in onion_links:
                    if link not in all_discovered_urls:
                        new_urls.add(link)
                        info(f"  New URL discovered: {link[:50]}")
            
            # Add new URLs to queue
            all_discovered_urls.update(new_urls)
            
            info(f"Cycle complete — {len(new_urls)} new URLs discovered")
            
            # Wait before next cycle
            if datetime.now() < end_time:
                wait_seconds = interval_minutes * 60
                info(f"Waiting {interval_minutes} minutes before next cycle...")
                time.sleep(wait_seconds)
        
        success(f"Autonomous crawl complete!")
        success(f"Total cycles: {crawl_count}")
        success(f"Total URLs discovered: {len(all_discovered_urls)}")
        
        return {
            'cycles': crawl_count,
            'total_urls': len(all_discovered_urls),
            'all_urls': list(all_discovered_urls)
        }
    
    def crawl_with_timeline(self, url, target_username=None):
        """
        Crawl with full timeline metadata
        Enables timeline queries required by problem statement
        """
        crawl_time = datetime.utcnow()
        
        # Regular crawl
        result = self.crawl_single(url, target_username)
        
        # Add timeline metadata
        result['timeline'] = {
            'crawled_at': crawl_time.isoformat(),
            'crawled_at_unix': crawl_time.timestamp(),
            'date': crawl_time.strftime('%Y-%m-%d'),
            'hour': crawl_time.hour,
            'day_of_week': crawl_time.strftime('%A'),
            'week_number': crawl_time.isocalendar()[1],
        }
        
        # Check for banners on common ports
        try:
            hostname = url.replace('http://', '').replace('https://', '').split('/')[0]
            result['service_banners'] = {}
            
            for port in [80, 443, 22, 21]:
                banner = self.grab_service_banner(hostname, port, timeout=3)
                if banner.get('banner'):
                    result['service_banners'][port] = banner
        except:
            result['service_banners'] = {}
        
        # Check descriptor inconsistencies
        result['descriptor'] = self.check_tor_descriptor(url)
        
        # Check SSL for clearnet domain matching
        if url.startswith('https://'):
            result['ssl_clearnet'] = self.match_ssl_to_clearnet(url)
        
        # Extract trust links
        html = self.get_html(
            self.fetch(url)[0]
        ) if result.get('success') else ''
        
        if html:
            result['trust_links'] = self.extract_trust_links(html, url)
        
        # Save to DB with timeline
        self.db.save_timeline_crawl(
            self.session_id, url, result['timeline'],
            result.get('descriptor', {}),
            result.get('trust_links', {})
        )
        
        return result
    
    def close(self):
        if self.js_renderer:
            self.js_renderer.close()
        if self.tor_ctrl:
            self.tor_ctrl.close()
