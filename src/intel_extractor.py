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

# ADDED: optional Base58 checksum validation
try:
    import base58
    _BASE58_OK = True
except ImportError:
    _BASE58_OK = False


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
# ADDED: returns (found, validated) tuple instead of just found
def extract_crypto(self, text):
    found = {}
    validated = {}
    for crypto, pattern in self.crypto_patterns.items():
        matches = list(set(re.findall(pattern, text)))
        if matches:
            found[crypto] = matches
            for addr in matches:
                validated[addr] = self._validate_wallet(crypto, addr)
            info(f"  Crypto [{crypto}]: {len(matches)} addresses "
                 f"({sum(1 for a in matches if validated[a])} validated)")
    return found, validated

# ADDED: original behavior, kept for backward compatibility
def extract_crypto_legacy(self, text):
    """Original extract_crypto — returns only the dict."""
    found = {}
    for crypto, pattern in self.crypto_patterns.items():
        matches = list(set(re.findall(pattern, text)))
        if matches:
            found[crypto] = matches
            info(f"  Crypto [{crypto}]: {len(matches)} addresses")
    return found

# ADDED: Base58 checksum + regex validation
def _validate_wallet(self, crypto, addr):
    """NEW METHOD — wasn't in your original."""
    if crypto in ('bitcoin', 'litecoin', 'dash') and _BASE58_OK:
        try:
            decoded = base58.b58decode_check(addr)
            return len(decoded) in (21, 25)
        except Exception:
            return False
    if crypto == 'bitcoin_bech32':
        return bool(re.match(r'^bc1[a-z0-9]{39,59}$', addr))
    if crypto == 'ethereum':
        return bool(re.match(r'^0x[a-fA-F0-9]{40}$', addr))
    if crypto == 'monero':
        return len(addr) in (95, 106) and addr.startswith('4')
    if crypto == 'zcash':
        return bool(re.match(r'^t1[a-zA-Z0-9]{33}$', addr))
    return False

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
    """Extract certificate information through the Tor SOCKS proxy."""
    result = {
        'hostname': hostname, 'port': port, 'ssl_available': False,
        'certificate': {}, 'vulnerabilities': [], 'server_info': {}
    }
    try:
        import socks, ssl
        from cryptography import x509
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives import hashes

        sock = socks.socksocket()
        sock.set_proxy(socks.SOCKS5, '127.0.0.1', 9050, rdns=True)
        sock.settimeout(10)
        sock.connect((hostname, port))

        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        with context.wrap_socket(sock, server_hostname=hostname) as ssock:
            raw_cert = ssock.getpeercert(binary_form=True)
            cipher = ssock.cipher()
            version = ssock.version()

        cert = x509.load_der_x509_certificate(raw_cert, default_backend())
        try:
            san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
            sans = [n.value for n in san if isinstance(n, x509.DNSName)]
        except x509.ExtensionNotFound:
            sans = []

        result['ssl_available'] = True
        result['certificate'] = {
            'subject': cert.subject.rfc4514_string(),
            'issuer': cert.issuer.rfc4514_string(),
            'valid_from': cert.not_valid_before_utc.isoformat(),
            'valid_until': cert.not_valid_after_utc.isoformat(),
            'serial_number': format(cert.serial_number, 'X'),
            'san': sans,
            'fingerprint_sha256': cert.fingerprint(hashes.SHA256()).hex(),
        }
        result['server_info'] = {
            'cipher': cipher[0] if cipher else '',
            'protocol': version or '',
            'bits': cipher[2] if cipher else 0,
        }
        if version in ('TLSv1', 'TLSv1.1', 'SSLv3', 'SSLv2'):
            result['vulnerabilities'].append(f'Outdated protocol: {version}')
        if cipher and cipher[2] and cipher[2] < 128:
            result['vulnerabilities'].append(f'Weak cipher: {cipher[0]} ({cipher[2]} bits)')
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
    
    for category, patterns in self.misconfig_patterns.items():
        for pattern in patterns:
            if re.search(pattern, html or '', re.IGNORECASE):
                misconfigs['found'].append(f'{category}: {pattern[:50]}')
                
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
    
    username_pattern = r'(?:alias|aka|also known as|nickname|nick|handle)[\s:]+([A-Za-z0-9_\-\.]{3,25})'
    aliases = re.findall(username_pattern, text, re.IGNORECASE)
    profiles['aliases'] = list(set(aliases))
    
    return profiles
# ── POST + TIMING ANALYSIS ──
# ADDED: new optional parameter raw_ref_prefix (default empty = old behavior)
def extract_posts_with_timing(self, html, target_username=None, raw_ref_prefix=''):
    """
    Extract posts WITH their timestamps
    Timing analysis reveals timezone = location intelligence
    ADDED: each post now carries 'raw_html' and 'raw_html_ref' for stylometry.
    """
    posts = []
    soup = BeautifulSoup(html, 'html.parser')
    
    post_containers = []
    
    selectors = [
        {'class_': re.compile(r'post|message|entry|reply|comment', re.I)},
        {'class_': re.compile(r'thread-item|forum-post|board-post', re.I)},
    ]
    
    for selector in selectors:
        containers = soup.find_all(attrs=selector)
        if containers:
            post_containers = containers
            break
    
    # ADDED: enumerate for post index
    for idx, container in enumerate(post_containers):
        post_text = container.get_text(separator=' ', strip=True)
        
        if len(post_text) < 20:
            continue

        # ADDED: reject overly large containers (whole thread as one post)
        if len(post_text.split()) > 500:
            continue
        
        if target_username and target_username.lower() not in post_text.lower():
            continue
        
        post_html = str(container)
        timestamps_found = []
        
        for pattern in self.timing_patterns:
            matches = re.findall(pattern, post_html, re.IGNORECASE)
            timestamps_found.extend(matches)
        
        time_tags = container.find_all(['time', 'span', 'div'],
                                       attrs={'class': re.compile(r'time|date|when|posted', re.I)})
        for tag in time_tags:
            ts = tag.get('datetime') or tag.get_text().strip()
            if ts:
                timestamps_found.append(ts)
        
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
            # ADDED: legacy call avoids tuple unpack
            'has_crypto': bool(self.extract_crypto_legacy(post_text)),
            'has_links': bool(re.findall(r'\.onion', post_text)),
            # ADDED: preserve raw HTML for stylometry
            'raw_html': post_html[:20000],
            'raw_html_ref': f'{raw_ref_prefix}/post_{idx:03d}.html' if raw_ref_prefix else '',
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
        hour_match = re.search(r'(\d{2}):\d{2}', ts)
        if hour_match:
            hours.append(int(hour_match.group(1)))
    
    if not hours:
        return {}
    
    from collections import Counter
    hour_counts = Counter(hours)
    peak_hours = hour_counts.most_common(3)
    
    avg_hour = sum(hours) / len(hours)
    
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
        
        if 'cloudflare' in server or 'cf-ray' in str(response_headers):
            fingerprint['cdn'] = 'Cloudflare'
    
    if html:
        html_lower = html.lower()
        
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
# ADDED: new optional parameter raw_ref_prefix
def full_extract(self, url, html, headers=None, target_username=None, raw_ref_prefix=''):
    """
    Run ALL extractors on a page — returns complete intelligence package
    """
    info(f"Full extraction: {url[:60]}")
    
    soup = BeautifulSoup(html, 'html.parser') if html else None
    text = soup.get_text(separator=' ') if soup else ''
    
    # ADDED: unpack tuple from new extract_crypto
    crypto_addrs, crypto_validated = self.extract_crypto(text)
    
    result = {
        'url': url,
        'extracted_at': datetime.utcnow().isoformat(),
        
        # ADDED: crypto_validated map + crypto_context
        'crypto_addresses': crypto_addrs,
        'crypto_validated': crypto_validated,
        'crypto_context': {},
        
        'misconfigs': self.detect_misconfigs(html, url, headers),
        'server_fingerprint': self.fingerprint_server(headers, html),
        'profiles': self.extract_profiles(html, text),
        
        # ADDED: raw_ref_prefix pass-through
        'posts_with_timing': self.extract_posts_with_timing(
            html, target_username, raw_ref_prefix
        ),
    }
    
    # ADDED: populate crypto_context map
    for currency, addrs in crypto_addrs.items():
        for a in addrs:
            result['crypto_context'][a] = self.analyze_crypto_context(text, a)
    
    all_timestamps = []
    for post in result['posts_with_timing']:
        all_timestamps.extend(post.get('timestamps', []))
    
    result['timing_analysis'] = self.analyze_posting_times(all_timestamps)
    
    if url.startswith('https://'):
        try:
            hostname = url.split('/')[2]
            result['ssl_info'] = self.get_ssl_info(hostname)
        except:
            result['ssl_info'] = {'error': 'SSL extraction failed'}
    
    # ADDED: correct profile indicator count (was skipping dicts)
    p = result['profiles']
    result['profile_indicator_count'] = (
        len(p.get('pgp_keys', [])) +
        sum(len(v) for v in p.get('contact_methods', {}).values()) +
        len(p.get('communication_channels', [])) +
        sum(len(v) for v in p.get('social_presence', {}).values()) +
        len(p.get('aliases', []))
    )
    
    success(f"Extraction complete:")
    info(f"  Crypto wallets: {sum(len(v) for v in result['crypto_addresses'].values())}")
    info(f"  Misconfigs: {len(result['misconfigs']['found'])}")
    # ADDED: uses new count field
    info(f"  Profile indicators: {result['profile_indicator_count']}")
    info(f"  Posts with timing: {len(result['posts_with_timing'])}")
    
    if result['timing_analysis']:
        info(f"  Timezone estimate: {result['timing_analysis'].get('timezone_estimate', 'Unknown')}")
    
    return result


