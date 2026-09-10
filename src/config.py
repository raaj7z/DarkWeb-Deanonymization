# config.py — Central configuration
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# ── Paths ──
DATA_DIR   = BASE_DIR / 'data'
OUTPUT_DIR = BASE_DIR / 'output'
LOG_DIR    = BASE_DIR / 'logs'
REPORT_DIR = BASE_DIR / 'reports'
DB_PATH    = DATA_DIR / 'crawler.db'

for _p in (DATA_DIR, OUTPUT_DIR, LOG_DIR, REPORT_DIR):
    _p.mkdir(parents=True, exist_ok=True)

# ── Tor ──
TOR_SOCKS_HOST    = '127.0.0.1'
TOR_SOCKS_PORT    = 9050
TOR_CTRL_PORT     = 9051
TOR_CTRL_PASSWORD = ''

# ── Crawl behavior ──
DEFAULT_TIMEOUT      = 30
DEFAULT_MAX_RETRIES  = 3
DEFAULT_WORKERS      = 3
DEFAULT_DELAY        = (1, 3)
DEFAULT_ROTATE_EVERY = 10

# ── Feature toggles ──
ENABLE_JS_RENDER     = False
ENABLE_AI_FILTER     = True
ENABLE_ML_CLASSIFIER = False
ENABLE_BANNER_GRAB   = True
ENABLE_TLS_FETCH     = True
ENABLE_SERVER_STATUS = True

# ── Confidence ──
CONFIDENCE_LEVELS = [
    (85, 'VERY_HIGH'),
    (65, 'HIGH'),
    (40, 'MEDIUM'),
    (0,  'LOW'),
]

def confidence_level(score: float) -> str:
    for threshold, label in CONFIDENCE_LEVELS:
        if score >= threshold:
            return label
    return 'LOW'

# ── Category keywords ──
CATEGORY_KEYWORDS = {
    'drugs':   ['cocaine', 'heroin', 'mdma', 'fentanyl', 'meth', 'weed', 'cannabis', 'lsd'],
    'arms':    ['ak-47', 'glock', 'rifle', 'ammo', 'explosive', 'grenade', 'silencer'],
    'data':    ['database', 'leak', 'dump', 'ssn', 'credit card', 'cvv', 'credentials'],
    'hacking': ['ransomware', 'malware', 'exploit', '0day', 'rat', 'botnet', 'ddos'],
    'finance': ['laundering', 'mixer', 'tumbler', 'cashout', 'wire', 'western union'],
}

# ── Username blacklist ──
USERNAME_BLACKLIST = {
    'admin', 'user', 'root', 'guest', 'example', 'localhost', 'test',
    'gmail', 'protonmail', 'riseup', 'tutanota', 'tuta', 'outlook',
    'onion', 'http', 'https', 'www', 'com', 'net', 'org',
    'index', 'home', 'login', 'register', 'profile', 'account',
    'moderator', 'mod', 'staff', 'system', 'null', 'undefined',
}

# ── Boilerplate patterns ──
BOILERPLATE_PATTERNS = [
    r'©\s*\d{4}',
    r'all rights reserved',
    r'cookie policy',
    r'privacy policy',
    r'terms of service',
    r'page \d+ of \d+',
    r'powered by',
    r'loading\.\.\.',
    r'please enable javascript',
    r'skip to (main )?content',
    r'^\s*menu\s*$',
    r'^\s*home\s*$',
    r'^\s*about\s*$',
    r'^\s*contact\s*$',
]

# ── ID formats ──
ACTOR_ID_PREFIX  = 'ACT'
SCAN_ID_PREFIX   = 'SCN'
ALERT_ID_PREFIX  = 'ALT'
REPORT_ID_PREFIX = 'RPT'
