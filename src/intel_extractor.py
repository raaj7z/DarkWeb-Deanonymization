# intel_extractor.py — Extract everything from dark web pages
# Misconfigs, SSL, profiles, crypto wallets, posts, timing analysis

import re
import ssl
import socket
import json
import hashlib
from datetime import datetime
from bs4 import BeautifulSoup
from utils import info, success, warn, error

class IntelExtractor:
    
    def __init__(self):
        
        # Crypto patterns
        self.crypto_patterns = {
            'bitcoin':   r'\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b',
            'bitcoin_bech32': r'\bbc1[a-z0-9]{39,59}\b',
            'monero':    r'\b4[0-9AB][1-9A-HJ-NP-Za-km-z]{93}\b',
            'ethereum':  r'\b0x[a-fA-F0-9]{40}\b',
            'litecoin':  r'\b[LM3][a-km-zA-HJ-NP-Z1-9]{26,33}\b',
            'dash':      r'\bX[1-9A-HJ-NP-Za-km-z]{33}\b',
            'zcash':     r'\bt1[a-zA-Z0-9]{33}\b',
        }
        
        # Misconfiguration patterns
        self.misconfig_patterns = {
            'directory_listing': [
                r'Index of /',
                r'Directory listing for',
                r'Parent Directory',
                r'\[DIR\].*\[TXT\]',
            ],
            'exposed_files': [
                r'\.env',
                r'\.git',
                r'config\.php',
                r'wp-config\.php',
                r'database\.yml',
                r'settings\.py',
                r'\.htpasswd',
                r'backup\.sql',
                r'dump\.sql',
            ],
            'error_disclosure': [
                r'MySQL server version',
                r'PostgreSQL.*ERROR',
                r'ORA-\d{5}',
                r'Microsoft OLE DB',
                r'Traceback \(most recent call last\)',
                r'Fatal error:.*PHP',
                r'Warning:.*PHP',
                r'stack trace:',
                r'django\.core\.exceptions',
            ],
            'admin_panels': [
                r'/admin',
                r'/wp-admin',
                r'/phpmyadmin',
                r'/cpanel',
                r'/administrator',
                r'/manager',
                r'/dashboard',
                r'/control',
            ],
            'open_ports_mentioned': [
                r'port\s+\d{2,5}\s+(?:open|exposed|accessible)',
                r'running on\s+(?:port\s+)?\d{2,5}',
            ],
        }
        
        # Profile indicators
        self.profile_patterns = {
            'pgp_key': r'-----BEGIN PGP PUBLIC KEY BLOCK-----.*?-----END PGP PUBLIC KEY BLOCK-----',
            'jabber': r'[a-zA-Z0-9._%+-]+@(?:jabber|xmpp|conversations)\.[a-zA-Z]{2,}',
            'telegram': r'(?:t\.me|telegram\.me)/([a-zA-Z0-9_]{5,32})',
            'wickr': r'(?:wickr|wicker)(?::\s*|id:\s*|me:\s*)([a-zA-Z0-9_]{1,20})',
            'session_id': r'(?:session|signal)(?::\s*|id:\s*)([a-f0-9]{66})',
            'onion_address': r'[a-z2-7]{56}\.onion',
            'i2p_address': r'[a-z0-9]+\.i2p',
            'email_riseup': r'[a-zA-Z0-9._%+-]+@riseup\.net',
            'email_proton': r'[a-zA-Z0-9._%+-]+@proton(?:mail)?\.(?:com|me)',
            'email_tutanota': r'[a-zA-Z0-9._%+-]+@tutanota\.(?:com|de)',
        }
        
        # Post timing patterns
        self.timing_patterns = [
            r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}(?::\d{2})?(?:\s*UTC|\s*GMT)?)',
            r'(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}(?::\d{2})?)',
            r'(\d{2}:\d{2}(?::\d{2})?\s*(?:UTC|GMT|EST|PST|IST|CET|MSK))',
            r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4}\s+\d{2}:\d{2})',
            r'(\d+\s+(?:seconds?|minutes?|hours?|days?)\s+ago)',
            r'(yesterday\s+at\s+\d{2}:\d{2})',
        ]
    
    # ── CRYPTO WALLET EXTRACTION ──
    def extract_crypto(self, text):
        """Extract all cryptocurrency addresses"""
        found = {}
        for crypto, pattern in self.crypto_patterns.items():
            matches = list(set(re.findall(pattern, text)))
            if matches:
                found[crypto] = matches
                info(f"  Crypto [{crypto}]: {len(matches)} addresses")
        return found
    
    def analyze_crypto_context(self, text, address):
        """Get context around a crypto address — reveals purpose"""
        idx = text.find(address)
        if idx == -1:
            return ''
        start = max(0, idx - 200)
        end = min(len(text), idx + 200)
        return text[start:end].strip()
    
    # ── SSL/TLS ANALYSIS ──
    def get_ssl_info(self, hostname, port=443):
        """
        Extract SSL certificate information
        Reveals: real server info, organization, expiry, alternative names
        """
        result = {
            'hostname': hostname,
            'port': port,
            'ssl_available': False,
            'certificate': {},
            'vulnerabilities': [],
            'server_info': {}
        }
        
        try:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            with socket.create_connection((hostname, port), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()
                    cipher = ssock.cipher()
                    version = ssock.version()
                    
                    result['ssl_available'] = True
                    result['certificate'] = {
                        'subject': dict(x[0] for x in cert.get('subject', [])),
                        'issuer': dict(x[0] for x in cert.get('issuer', [])),
                        'valid_from': cert.get('notBefore', ''),
                        'valid_until': cert.get('notAfter', ''),
                        'serial_number': cert.get('serialNumber', ''),
                        'san': [x[1] for x in cert.get('subjectAltName', [])],
                        'version': cert.get('version', ''),
                    }
                    result['server_info'] = {
                        'cipher': cipher[0] if cipher else '',
                        'protocol': version,
                        'bits': cipher[2] if cipher else 0,
                    }
                    
                    # Check for vulnerabilities
                    if version in ['TLSv1', 'TLSv1.1', 'SSLv3', 'SSLv2']:
                        result['vulnerabilities'].append(
                            f'Outdated protocol: {version}'
                        )
                    
                    # Check for weak ciphers
                    if cipher and cipher[2] and cipher[2] < 128:
                        result['vulnerabilities'].append(
                            f'Weak cipher: {cipher[0]} ({cipher[2]} bits)'
                        )
                    
                    # Check SAN for additional domains — intelligence gold
                    if result['certificate']['san']:
                        info(f"  SSL SANs found: {result['certificate']['san']}")
                    
                    success(f"SSL analyzed: {hostname}")
                    
        except ssl.SSLError as e:
            result['vulnerabilities'].append(f'SSL Error: {str(e)}')
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    # ── MISCONFIGURATION DETECTION ──
    def detect_misconfigs(self, html, url, headers=None):
        """Detect server misconfigurations — exposes real server info"""
        misconfigs = {
            'found': [],
            'severity': {},
            'server_disclosure': {},
            'exposed_paths': []
        }
        
        text = BeautifulSoup(html, 'html.parser').get_text() if html else ''
        
        # Check response headers for server disclosure
        if headers:
            server = headers.get('Server', '')
            powered_by = headers.get('X-Powered-By', '')
            
            if server:
                misconfigs['server_disclosure']['server'] = server
                misconfigs['found'].append(f'Server header exposed: {server}')
                misconfigs['severity']['server_header'] = 'MEDIUM'
            
            if powered_by:
                misconfigs['server_disclosure']['powered_by'] = powered_by
                misconfigs['found'].append(f'Technology exposed: {powered_by}')
                misconfigs['severity']['powered_by'] = 'MEDIUM'
            
            # Missing security headers
            security_headers = [
                'X-Frame-Options',
                'X-Content-Type-Options',
                'Content-Security-Policy',
                'Strict-Transport-Security',
                'X-XSS-Protection'
            ]
            
            for header in security_headers:
                if header not in headers:
                    misconfigs['found'].append(f'Missing header: {header}')
                    misconfigs['severity'][header] = 'LOW'
        
        # Check HTML content for misconfigs
        for category, patterns in self.misconfig_patterns.items():
            for pattern in patterns:
                if re.search(pattern, html or '', re.IGNORECASE):
                    misconfigs['found'].append(
                        f'{category}: {pattern[:50]}'
                    )
                    
                    severity = {
                        'directory_listing': 'HIGH',
                        'exposed_files': 'CRITICAL',
                        'error_disclosure': 'HIGH',
                        'admin_panels': 'MEDIUM',
                        'open_ports_mentioned': 'LOW',
                    }.get(category, 'MEDIUM')
                    
                    misconfigs['severity'][category] = severity
                    
                    if category == 'admin_panels':
                        misconfigs['exposed_paths'].append(pattern)
        
        if misconfigs['found']:
            warn(f"  Misconfigs found: {len(misconfigs['found'])}")
            
            # Check for critical findings
            critical = [k for k, v in misconfigs['severity'].items() 
                       if v == 'CRITICAL']
            if critical:
                error(f"  CRITICAL misconfigs: {critical}")
        
        return misconfigs
    
    # ── PROFILE EXTRACTION ──
    def extract_profiles(self, html, text):
        """Extract complete threat actor profile indicators"""
        profiles = {
            'pgp_keys': [],
            'contact_methods': {},
            'social_presence': {},
            'communication_channels': [],
            'aliases': [],
        }
        
        # Extract each profile type
        for profile_type, pattern in self.profile_patterns.items():
            flags = re.DOTALL if 'pgp' in profile_type else re.IGNORECASE
            matches = re.findall(pattern, html or '', flags)
            
            if matches:
                if profile_type == 'pgp_key':
                    profiles['pgp_keys'] = matches
                    info(f"  PGP key found!")
                    
                elif profile_type in ['jabber', 'email_riseup', 
                                       'email_proton', 'email_tutanota']:
                    profiles['contact_methods'][profile_type] = list(set(matches))
                    
                elif profile_type in ['telegram', 'wickr', 'session_id']:
                    profiles['communication_channels'].extend(
                        [{'type': profile_type, 'value': m} for m in set(matches)]
                    )
                    
                elif profile_type in ['onion_address', 'i2p_address']:
                    profiles['social_presence'][profile_type] = list(set(matches))
        
        # Extract usernames as aliases
        username_pattern = r'(?:alias|aka|also known as|nickname|nick|handle)[\s:]+([A-Za-z0-9_\-\.]{3,25})'
        aliases = re.findall(username_pattern, text, re.IGNORECASE)
        profiles['aliases'] = list(set(aliases))
        
        return profiles
    
    # ── POST + TIMING ANALYSIS ──
    def extract_posts_with_timing(self, html, target_username=None):
        """
        Extract posts WITH their timestamps
        Timing analysis reveals timezone = location intelligence
        """
        posts = []
        soup = BeautifulSoup(html, 'html.parser')
        
        # Common forum post structures
        post_containers = []
        
        # Try multiple selectors
        selectors = [
            {'class_': re.compile(r'post|message|entry|reply|comment', re.I)},
            {'class_': re.compile(r'thread-item|forum-post|board-post', re.I)},
        ]
        
        for selector in selectors:
            containers = soup.find_all(attrs=selector)
            if containers:
                post_containers = containers
                break
        
        for container in post_containers:
            post_text = container.get_text(separator=' ', strip=True)
            
            if len(post_text) < 20:
                continue
            
            if target_username and target_username.lower() not in post_text.lower():
                continue
            
            # Extract timestamp from this specific post
            post_html = str(container)
            timestamps_found = []
            
            for pattern in self.timing_patterns:
                matches = re.findall(pattern, post_html, re.IGNORECASE)
                timestamps_found.extend(matches)
            
            # Also check time/datetime elements
            time_tags = container.find_all(['time', 'span', 'div'],
                                           attrs={'class': re.compile(r'time|date|when|posted', re.I)})
            for tag in time_tags:
                ts = tag.get('datetime') or tag.get_text().strip()
                if ts:
                    timestamps_found.append(ts)
            
            # Extract username from post
            post_username = None
            for cls in ['username', 'author', 'user', 'poster', 'nick']:
                user_el = container.find(class_=re.compile(cls, re.I))
                if user_el:
                    post_username = user_el.get_text().strip()
                    break
            
            post_data = {
                'username': post_username or target_username or 'unknown',
                'text': post_text[:3000],
                'word_count': len(post_text.split()),
                'timestamps': list(set(timestamps_found)),
                'char_count': len(post_text),
                'has_crypto': bool(self.extract_crypto(post_text)),
                'has_links': bool(re.findall(r'\.onion', post_text)),
            }
            
            posts.append(post_data)
        
        return posts
    
    def analyze_posting_times(self, all_timestamps):
        """
        Analyze posting patterns to determine likely timezone/location
        This is KEY for de-anonymization
        """
        if not all_timestamps:
            return {}
        
        hours = []
        
        for ts in all_timestamps:
            # Try to extract hour from timestamp
            hour_match = re.search(r'(\d{2}):\d{2}', ts)
            if hour_match:
                hours.append(int(hour_match.group(1)))
        
        if not hours:
            return {}
        
        # Find peak activity hours
        from collections import Counter
        hour_counts = Counter(hours)
        peak_hours = hour_counts.most_common(3)
        
        # Determine likely timezone based on activity patterns
        avg_hour = sum(hours) / len(hours)
        
        # Common active hours by timezone (assuming 9am-11pm active)
        timezone_guess = 'Unknown'
        if 8 <= avg_hour <= 23:
            if avg_hour <= 14:
                timezone_guess = 'Likely UTC+0 to UTC+5 (Europe/South Asia)'
            elif avg_hour <= 18:
                timezone_guess = 'Likely UTC+5 to UTC+8 (Asia)'
            else:
                timezone_guess = 'Likely UTC-5 to UTC+0 (Americas/Europe)'
        
        return {
            'total_timestamps': len(all_timestamps),
            'peak_hours': peak_hours,
            'average_hour': round(avg_hour, 1),
            'timezone_estimate': timezone_guess,
            'activity_pattern': 'Night owl' if avg_hour > 20 or avg_hour < 6 else 'Day active',
            'raw_hours': hours
        }
    
    # ── SERVER FINGERPRINTING ──
    def fingerprint_server(self, response_headers, html):
        """Fingerprint the real server behind Tor hidden service"""
        fingerprint = {
            'server_software': '',
            'backend_language': '',
            'framework': '',
            'database_hints': [],
            'cdn': '',
            'os_hints': [],
        }
        
        if response_headers:
            server = response_headers.get('Server', '').lower()
            powered = response_headers.get('X-Powered-By', '').lower()
            
            # Server software
            if 'apache' in server:
                fingerprint['server_software'] = 'Apache'
                version = re.search(r'apache/(\d+\.\d+)', server)
                if version:
                    fingerprint['server_software'] += f' {version.group(1)}'
            elif 'nginx' in server:
                fingerprint['server_software'] = 'Nginx'
            elif 'lighttpd' in server:
                fingerprint['server_software'] = 'Lighttpd'
            elif 'iis' in server:
                fingerprint['server_software'] = 'Microsoft IIS'
                fingerprint['os_hints'].append('Windows Server')
            
            # Backend language
            if 'php' in powered:
                fingerprint['backend_language'] = 'PHP'
                version = re.search(r'php/(\d+\.\d+)', powered)
                if version:
                    fingerprint['backend_language'] += f' {version.group(1)}'
            elif 'asp.net' in powered:
                fingerprint['backend_language'] = 'ASP.NET'
                fingerprint['os_hints'].append('Windows')
            elif 'python' in powered or 'django' in powered:
                fingerprint['backend_language'] = 'Python'
            
            # CDN detection
            if 'cloudflare' in server or 'cf-ray' in str(response_headers):
                fingerprint['cdn'] = 'Cloudflare'
        
        # Check HTML for additional hints
        if html:
            html_lower = html.lower()
            
            # Framework detection
            frameworks = {
                'wordpress': 'WordPress',
                'wp-content': 'WordPress',
                'drupal': 'Drupal',
                'joomla': 'Joomla',
                'django': 'Django',
                'rails': 'Ruby on Rails',
                'laravel': 'Laravel',
                'symfony': 'Symfony',
            }
            
            for marker, framework in frameworks.items():
                if marker in html_lower:
                    fingerprint['framework'] = framework
                    break
            
            # Database hints from errors
            db_patterns = {
                'mysql': 'MySQL',
                'postgresql': 'PostgreSQL',
                'sqlite': 'SQLite',
                'mongodb': 'MongoDB',
                'oracle': 'Oracle',
                'mssql': 'MSSQL',
            }
            
            for pattern, db in db_patterns.items():
                if pattern in html_lower:
                    fingerprint['database_hints'].append(db)
        
        return fingerprint
    
    # ── FULL EXTRACTION ──
    def full_extract(self, url, html, headers=None, target_username=None):
        """
        Run ALL extractors on a page — returns complete intelligence package
        """
        info(f"Full extraction: {url[:60]}")
        
        soup = BeautifulSoup(html, 'html.parser') if html else None
        text = soup.get_text(separator=' ') if soup else ''
        
        result = {
            'url': url,
            'extracted_at': datetime.utcnow().isoformat(),
            
            # Crypto intelligence
            'crypto_addresses': self.extract_crypto(text),
            
            # Server intelligence
            'misconfigs': self.detect_misconfigs(html, url, headers),
            'server_fingerprint': self.fingerprint_server(headers, html),
            
            # Profile intelligence
            'profiles': self.extract_profiles(html, text),
            
            # Post + timing intelligence
            'posts_with_timing': self.extract_posts_with_timing(
                html, target_username
            ),
        }
        
        # Timing analysis across all posts
        all_timestamps = []
        for post in result['posts_with_timing']:
            all_timestamps.extend(post.get('timestamps', []))
        
        result['timing_analysis'] = self.analyze_posting_times(all_timestamps)
        
        # SSL analysis for onion sites with SSL
        if url.startswith('https://'):
            try:
                hostname = url.split('/')[2]
                result['ssl_info'] = self.get_ssl_info(hostname)
            except:
                result['ssl_info'] = {'error': 'SSL extraction failed'}
        
        # Summary
        success(f"Extraction complete:")
        info(f"  Crypto wallets: {sum(len(v) for v in result['crypto_addresses'].values())}")
        info(f"  Misconfigs: {len(result['misconfigs']['found'])}")
        info(f"  Profile indicators: {sum(len(v) for v in result['profiles'].values() if isinstance(v, list))}")
        info(f"  Posts with timing: {len(result['posts_with_timing'])}")
        
        if result['timing_analysis']:
            info(f"  Timezone estimate: {result['timing_analysis'].get('timezone_estimate', 'Unknown')}")
        
        return result
