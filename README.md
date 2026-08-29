# DarkWeb-Deanonymization

Dark web intelligence system for Tor hidden service deanonymization, cross-platform threat actor profiling, and clearnet entity attribution.

> **⚠️ Legal & Ethical Notice**: This tool is designed for authorized security research, law enforcement, and defensive cybersecurity purposes only. Unauthorized access to computer systems is illegal. Users must comply with all applicable laws and obtain proper authorization before use.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [System Requirements](#system-requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Modules](#modules)
- [Output & Reporting](#output--reporting)
- [Architecture](#architecture)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## 🎯 Overview

**DarkWeb-Deanonymization** is a Python-based OSINT framework that automates dark web reconnaissance. It:

- ✅ Crawls `.onion` hidden services through the Tor network
- ✅ Extracts threat actor identities (usernames, emails, crypto addresses)
- ✅ Profiles cross-platform activity and behavioral patterns
- ✅ Correlates clearnet entities with dark web presence
- ✅ Generates structured intelligence reports
- ✅ Maintains SQLite database for analysis and trending

The system combines **web scraping**, **regex pattern matching**, and **Tor anonymization** to uncover operational security failures and link disparate threat actors.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| **Tor Integration** | SOCKS proxy through Tor with automatic identity rotation |
| **Multi-threaded Crawling** | Parallel requests with randomized delays to avoid detection |
| **Alive Site Checker** | Quickly identifies responsive `.onion` services with retry logic |
| **Data Extraction** | Usernames, emails, timestamps, crypto addresses, posts, links |
| **Post Filtering** | Target-specific username searches across forums |
| **Database Storage** | SQLite persistence with indexed queries |
| **JSON Reports** | Exportable results for further analysis |
| **Anti-Detection** | Random user agents, request delays, session rotation |
| **Error Handling** | Automatic retries, timeout management, graceful degradation |

---

## 💻 System Requirements

### Minimum Specifications

- **OS**: Linux, macOS, or Windows (WSL2 recommended)
- **Python**: 3.8+
- **Memory**: 512 MB
- **Disk**: 500 MB (for database and reports)
- **Network**: Stable internet connection
- **Tor**: Must be installed and running locally

### Dependencies

See `requirements.txt`:

```
requests[socks]==2.31.0       # HTTP client with SOCKS support
beautifulsoup4==4.12.2        # HTML parsing
colorama==0.4.6               # Colored terminal output
tqdm==4.66.1                  # Progress bars
fake-useragent==1.4.0         # Random user agent spoofing
```

---

## 📦 Installation

### Step 1: Install Tor

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install tor -y
```

**macOS (Homebrew):**
```bash
brew install tor
```

**Windows:**
Download from https://www.torproject.org/download/ and follow the installer.

### Step 2: Clone Repository

```bash
git clone https://github.com/raaj7z/DarkWeb-Deanonymization.git
cd DarkWeb-Deanonymization
```

### Step 3: Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 4: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 5: Start Tor Service

```bash
# Linux/macOS
sudo service tor start

# Check Tor status
sudo service tor status

# macOS (Homebrew)
brew services start tor

# Windows (from Tor Browser folder)
tor.exe
```

Verify Tor is listening:
```bash
curl -x socks5://127.0.0.1:9050 https://www.example.com -v
```

---

## ⚙️ Configuration

Create a `config.py` in the project root (optional):

```python
# Tor Configuration
TOR_SOCKS_HOST = "127.0.0.1"
TOR_SOCKS_PORT = 9050

# Crawler Settings
DEFAULT_TIMEOUT = 30           # Seconds
REQUEST_DELAY = (2, 5)         # Random range in seconds
MAX_RETRIES = 3                # Retry attempts per URL
MAX_DEPTH = 2                  # Link recursion depth

# Database
DB_PATH = "darkweb_intel.db"

# Output
REPORTS_DIR = "reports"
LOGS_DIR = "logs"

# Anti-Detection
RANDOM_USER_AGENTS = True
ROTATE_IDENTITY = True         # Refresh Tor identity between sites
```

---

## 🚀 Usage

### Basic Usage

```bash
cd src
python3 main.py
```

The script will:

1. **Verify Tor Connection** — Confirm anonymity by comparing real IP vs Tor IP
2. **Check Alive Sites** — Ping target `.onion` services (DuckDuckGo, ProtonMail)
3. **Crawl & Extract** — Search for usernames, timestamps, posts
4. **Save Results** — Export to `reports/crawl_results.json`
5. **Display Stats** — Show database record counts

#### Example Output:

```
╔══════════════════════════════════════════════════════════════╗
║     Dark Web Intelligence & Threat Actor Deanonymization    ║
║                     DarkWeb Crawler v1.0                     ║
╚══════════════════════════════════════════════════════════════╝

[INFO] Starting Dark Web Crawler...
[INFO] Verifying Tor connection...
[INFO] Real IP:  203.0.113.42
[INFO] Tor IP:   198.51.100.89
[SUCCESS] Anonymity confirmed — IPs are different!

=== STEP 1: Checking which URLs are alive ===
[SUCCESS] http://duckduckgogg42xjoc72x3sjasowoarfbgcmvfimaftt6twagswzczad.onion is ALIVE
[SUCCESS] Found 2 alive URLs

=== STEP 2: Crawling alive URLs ===
Enter target username to search (or press Enter to crawl all): 
[SUCCESS] Fetched: http://duckduckgogg42xjoc72x3sjasowoarfbgcmvfimaftt6twagswzczad.onion...
[SUCCESS] Crawl complete!
[INFO] Usernames found: 42
[INFO] Posts extracted: 156
[INFO] Emails: 8
[INFO] Crypto addresses: {'bitcoin': 3, 'monero': 1}

=== STEP 3: Database Stats ===
[INFO] sites: 2 records
[INFO] pages: 2 records
[INFO] usernames: 42 records
[INFO] posts: 156 records

[SUCCESS] Results saved to reports/crawl_results.json
[SUCCESS] Crawl session complete!
```

### Advanced Usage - Python API

```python
from src.crawler import DarkCrawler
from src.database import Database
from src.alive_checker import AliveChecker
from src.utils import get_tor_session, verify_tor

# Initialize
db = Database()
crawler = DarkCrawler(db=db, delay=(2, 5), timeout=30)
checker = AliveChecker(timeout=30, retries=3)

# Check if site is alive
result = checker.check('http://example.onion')
print(f"Status: {result['status']}")

# Crawl single URL
data = crawler.crawl('http://example.onion', target_username='actor_xyz', depth=2)

# Crawl multiple URLs
urls = ['http://site1.onion', 'http://site2.onion']
results = crawler.crawl_multiple(urls, target_username='actor_xyz')

# Query database
stats = db.get_stats()
usernames = db.get_usernames_by_site('http://example.onion')
```

---

## 📁 Modules

### `crawler.py`
**Core web scraping engine**

```python
DarkCrawler(db, delay=(2,5), timeout=30, max_retries=3)
```

**Key Methods:**

- `fetch(url)` — Retrieve page with Tor SOCKS proxy, retry logic
- `extract_usernames(html, url)` — Regex + BeautifulSoup parsing
- `extract_emails(text)` — Email regex extraction
- `extract_crypto_addresses(text)` — Bitcoin/Monero/Ethereum patterns
- `extract_links(html, base_url)` — Find `.onion` and clearnet links
- `extract_posts(html, target_username)` — Forum post extraction
- `extract_timestamps(html)` — Timezone/activity pattern detection
- `crawl(url, target_username, depth)` — Main crawl function with recursion
- `crawl_multiple(urls, target_username)` — Batch processing

**Example:**
```python
result = crawler.crawl('http://darkforum.onion', target_username='alice', depth=1)
print(result['usernames'])      # ['alice_2024', 'alice_dev', ...]
print(result['emails'])         # ['alice@riseup.net', ...]
print(result['crypto_addresses']) # {'bitcoin': ['1A1...'], 'monero': ['4...']...}
```

---

### `alive_checker.py`
**Fast availability scanning**

```python
AliveChecker(timeout=30, retries=3)
```

**Key Methods:**

- `check(url)` — Single URL availability check
- `check_multiple(urls)` — Batch check with progress bar
- Returns: `{'alive': [...], 'dead': [...], 'unknown': [...]}`

**Example:**
```python
checker = AliveChecker()
results = checker.check_multiple([
    'http://forum1.onion',
    'http://forum2.onion',
    'http://market.onion'
])
print(f"Alive: {len(results['alive'])}")
```

---

### `database.py`
**SQLite persistence layer**

**Schema:**
```sql
sites          — Crawled .onion services
pages          — Full HTML + text snapshots
usernames      — Extracted identities with source URLs
emails         — Contact information
posts          — Forum messages and comments
links          — Cross-references between sites
```

**Key Methods:**

- `save_site(url, title, status_code, alive, server)` — Register a site
- `save_username(username, source_url)` — Store identity
- `save_post(username, content, timestamp, source_url)` — Archive posts
- `get_usernames_by_site(url)` — Query identities by site
- `get_posts_by_username(username)` — Timeline of activity
- `get_stats()` — Database statistics
- `close()` — Commit and close connection

**Example:**
```python
db = Database()
usernames = db.get_usernames_by_site('http://forum.onion')
for user in usernames:
    posts = db.get_posts_by_username(user)
    print(f"{user}: {len(posts)} posts")
db.close()
```

---

### `utils.py`
**Helper functions & Tor integration**

**Key Functions:**

- `get_tor_session()` — Create requests.Session with SOCKS5 proxy
- `verify_tor()` — Check if Tor is running and responsive
- `get_real_ip()` — Fetch clearnet IP (for comparison)
- `get_tor_ip(session)` — Fetch Tor exit node IP
- `print_banner()` — ASCII art header
- `info()`, `success()`, `error()`, `warn()` — Colored logging
- `setup_logger()` — File + console logging configuration

**Example:**
```python
from src.utils import get_tor_session, verify_tor

session = get_tor_session()
response = session.get('http://example.onion', timeout=30)
```

---

### `main.py`
**Orchestration & full workflow**

Runs complete investigation pipeline:
1. Tor verification
2. Alive site checking
3. Multi-URL crawling
4. Database persistence
5. JSON report generation

---

## 📊 Output & Reporting

### JSON Report Format

**File:** `reports/crawl_results.json`

```json
[
  {
    "url": "http://example.onion",
    "title": "Underground Forum",
    "usernames": ["actor_001", "threat_xyz"],
    "emails": ["actor@riseup.net"],
    "posts_count": 45,
    "timestamps": ["2024-08-28 14:23:45", "2024-08-28 15:10:12"],
    "crypto": {
      "bitcoin": ["1A1z7agoat..."],
      "monero": ["4..."]
    },
    "success": true
  }
]
```

### Database Queries

```bash
# View all sites
sqlite3 darkweb_intel.db "SELECT url, title, alive FROM sites;"

# Find usernames associated with a site
sqlite3 darkweb_intel.db "SELECT DISTINCT username FROM usernames WHERE source_url LIKE '%forum%';"

# Timeline of posts by user
sqlite3 darkweb_intel.db "SELECT timestamp, content FROM posts WHERE username='actor_001' ORDER BY timestamp DESC;"

# Count crypto addresses
sqlite3 darkweb_intel.db "SELECT address FROM emails LIMIT 10;"
```

---

## 🏗️ Architecture

```
DarkWeb-Deanonymization/
├── src/
│   ├── main.py              # Entry point
│   ├── crawler.py           # Core scraping engine
│   ├── alive_checker.py     # Availability scanner
│   ├── database.py          # SQLite ORM
│   ├── utils.py             # Tor + logging utilities
│   └── __init__.py
├── reports/                 # JSON output
├── logs/                    # Application logs
├── darkweb_intel.db         # SQLite database (auto-created)
├── requirements.txt         # Python dependencies
├── README.md                # This file
└── config.py               # Optional configuration
```

### Data Flow

```
┌───��─────────────┐
│  Target URLs    │
└────────┬────────┘
         │
         ▼
┌──────────────────────────┐
│   Alive Checker          │  SOCKS5/Tor
│   (Filter responsive)    │  Proxy
└────────┬─────────────────┘
         │
         ▼
┌────────────────────────────┐
│   Dark Crawler             │
│   • Fetch HTML             │
│   • Extract patterns       │  Retry logic
│   • Detect identities      │  Anti-evasion
└────────┬───────────────────┘
         │
    ┌────┴─────┬──────┬─────┐
    ▼          ▼      ▼     ▼
┌────────┐ ┌───────┐ ┌───┐ ┌──────┐
│Users   │ │Posts  │ │IPs│ │Crypto│
├────────┤ ├───────┤ └───┘ ├──────┤
│Emails  │ │Links  │       │Addrs │
└────────┘ └───────┘       └──────┘
    │          │              │
    └──────────┼──────────────┘
               ▼
       ┌─────────────────┐
       │  SQLite DB      │
       │  (Persistence)  │
       └─────────────────┘
               │
               ▼
       ┌──────────────────┐
       │ JSON Report      │
       │ Intelligence     │
       └──────────────────┘
```

---

## 🔧 Troubleshooting

### **Tor Connection Errors**

**Problem:** `[ERROR] WARNING: Real IP and Tor IP are the same`

**Solution:**
```bash
# Verify Tor is running
sudo service tor status

# Restart Tor
sudo service tor restart

# Check SOCKS port
netstat -tuln | grep 9050

# Test SOCKS connection
curl -x socks5://127.0.0.1:9050 https://www.example.com
```

---

### **Timeout/Connection Refused**

**Problem:** `ConnectionError: Failed to establish a connection`

**Solution:**
```bash
# Increase timeout in code
crawler = DarkCrawler(timeout=60)

# Check if site is actually alive
curl -x socks5://127.0.0.1:9050 http://example.onion

# Verify Tor has enough circuits
echo "SIGNAL NEWNYM" | nc localhost 9051
```

---

### **403 Forbidden / CAPTCHA**

**Problem:** Sites returning 403 or CAPTCHA challenges

**Solution:**
- Increase delays between requests
- Rotate Tor identity more frequently
- Use `alive_checker.py` to identify responsive sites first
- Consider implementing headless browser (Selenium) for JavaScript sites

```python
crawler = DarkCrawler(delay=(5, 15))  # Longer delays
```

---

### **"No module named 'requests'"**

**Problem:** Import errors

**Solution:**
```bash
# Ensure venv is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

---

### **Database Locked**

**Problem:** `sqlite3.OperationalError: database is locked`

**Solution:**
```python
db.close()  # Always close connections
# Or use context manager
with Database() as db:
    db.get_stats()
```

---

## 🤝 Contributing

Contributions welcome! Please follow these guidelines:

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/new-capability`
3. **Code** with style (PEP 8 compliance)
4. **Test** functionality before submitting
5. **Commit** with clear messages: `git commit -m "Add feature: X"`
6. **Push** to branch: `git push origin feature/new-capability`
7. **Open PR** with detailed description

### Development Roadmap

- [ ] Async/concurrent crawling (asyncio)
- [ ] Headless browser support (Selenium/Playwright) for JS-heavy sites
- [ ] Machine learning clustering (threat actor profiling)
- [ ] REST API for remote access
- [ ] Graph database integration (Neo4j)
- [ ] Clearnet correlation engine
- [ ] Export to various formats (CSV, Parquet, SQLite)

---

## ⚖️ Legal & Ethics

**IMPORTANT**: This tool must only be used:

✅ **With explicit authorization** from site/network owners
✅ **For authorized security research** and defensive purposes
✅ **In compliance with** all applicable laws (CFAA, GDPR, local regulations)
✅ **By security professionals** with proper training

❌ **NOT for** unauthorized network access, data theft, or illegal intelligence gathering
❌ **NOT to** violate user privacy or circumvent security controls
❌ **NOT without** proper legal review and authorization

**Disclaimer**: Users are solely responsible for ensuring compliance with law. The developers assume no liability for misuse.

---

## 📜 License

This project is provided as-is for authorized security research only. See LICENSE file for details.

---

## 📞 Support

- **Issues**: Open GitHub Issues for bugs
- **Discussions**: Use GitHub Discussions for questions
- **Security**: Report vulnerabilities responsibly to [maintainer]

---

## 🔗 Resources

- [Tor Documentation](https://www.torproject.org/docs/)
- [OSINT Guide](https://osintframework.com/)
- [Python Requests](https://docs.python-requests.org/)
- [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
- [SQLite3](https://www.sqlite.org/docs.html)

---

**Last Updated:** August 2024  
**Maintainer:** [@raaj7z](https://github.com/raaj7z)
