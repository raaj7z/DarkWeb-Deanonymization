# DarkWeb-Deanonymization v3.0

**Advanced Tor Hidden Service Deanonymization & Threat Actor Profiling System**

Enterprise-grade Python framework for dark web intelligence gathering, actor relationship mapping, and clearnet entity attribution through behavioral analysis and infrastructure fingerprinting.

> **⚠️ Legal & Ethical Notice**: This tool is designed for authorized law enforcement, government agencies, and authorized security research ONLY. Unauthorized access to computer systems is illegal under the Computer Fraud & Abuse Act (CFAA) and applicable international law. All users are responsible for compliance.

---

## 🎯 Overview

**DarkWeb-Deanonymization v3.0** is a comprehensive Python OSINT framework that automates dark web reconnaissance with enterprise intelligence capabilities:

### Core Capabilities

✅ **Web Scraping** — Tor-routed crawling of `.onion` hidden services  
✅ **Data Extraction** — Usernames, emails, crypto addresses, posts, timestamps  
✅ **Behavioral Analysis** — Timing analysis, timezone estimation, activity patterns  
✅ **Infrastructure Fingerprinting** — Server banners, SSL certificates, Tor descriptors  
✅ **Trust Network Mapping** — Actor relationships, vouches, wallet associations  
✅ **Origin Attribution** — Clearnet domain matching via SSL SANs and exposed IPs  
✅ **Autonomous Crawling** — Continuous unattended reconnaissance with URL discovery  
✅ **Timeline Queries** — Temporal analysis for activity correlation  
✅ **Persistent Storage** — SQLite database with full session history  
✅ **Enterprise Reporting** — JSON exports, actor profiles, relationship graphs  

---

## 📋 Table of Contents

- [What's New in v3.0](#whats-new-in-v30)
- [Key Features](#key-features)
- [System Requirements](#system-requirements)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Menu Options](#menu-options)
- [Advanced Usage](#advanced-usage)
- [Database Schema](#database-schema)
- [Output Formats](#output-formats)
- [Deanonymization Techniques](#deanonymization-techniques)
- [Troubleshooting](#troubleshooting)
- [Legal Notice](#legal-notice)

---

## 🆕 What's New in v3.0

### Major Enhancements

| Feature | Description |
|---------|-------------|
| **Service Banner Grabbing** | Extract server signatures from open ports (SSH, HTTP, FTP, SMTP, MySQL) |
| **SSL Certificate Analysis** | Find clearnet domains in SSL Subject Alternative Names (SANs) |
| **Tor Descriptor Checking** | Detect descriptor inconsistencies revealing origin infrastructure |
| **Trust Link Extraction** | Build actor relationship graphs (vouches, wallets, PGP signatures) |
| **Autonomous Crawl Mode** | Runs continuously without manual intervention; auto-discovers URLs |
| **Timeline Query System** | Search crawls by date range with temporal analysis |
| **Actor Relationship Viewer** | Visualize trust networks and cross-platform correlations |
| **Full Intelligence Extraction** | Comprehensive metadata including cryptography, misconfigs, profiles |
| **Advanced Database** | New tables: `service_banners`, `descriptor_checks`, `trust_links`, `timeline_crawls` |

### Performance Improvements

- ⚡ Concurrent banner grabbing with timeouts
- ⚡ SSL certificate fetching via SOCKS5 Tor proxy
- ⚡ Optimized descriptor checking with regex patterns
- ⚡ Wallet address correlation across posts

---

## ✨ Key Features

### Intelligence Extraction

| Module | Extraction Type | Use Case |
|--------|-----------------|----------|
| **Usernames** | Regex + BeautifulSoup parsing | Actor identification |
| **Emails** | RFC 5322 regex | Contact information tracking |
| **Crypto Addresses** | Bitcoin, Monero, Ethereum patterns | Financial attribution |
| **Posts** | DOM/CSS selectors | Activity timeline |
| **Timestamps** | Multiple datetime formats | Timezone/activity profiling |
| **Links** | `.onion` and clearnet URLs | Network mapping |
| **Service Banners** | Port probing (80, 443, 22, 21, 3306) | Server identification |
| **SSL Certificates** | Subject CN, SANs | Origin server attribution |
| **Tor Descriptors** | Inconsistency detection | Real IP/domain leakage |
| **Trust Networks** | Vouches, references, wallets | Actor correlation |

### System Capabilities

- **Multi-threaded Crawling** — Parallel requests with configurable workers (1-10)
- **Tor Integration** — SOCKS5 proxy with automatic circuit rotation
- **CAPTCHA Detection** — Identifies and logs CAPTCHA blocks
- **JavaScript Rendering** — Optional headless browser for dynamic content
- **Session Management** — Tracks all crawls with session IDs and timelines
- **Database Persistence** — SQLite with WAL mode for concurrent writes
- **Anti-Detection** — Random user agents, delays, identity rotation
- **Error Recovery** — Automatic retries, timeouts, graceful degradation

---

## 💻 System Requirements

### Minimum Specifications

- **OS**: Linux, macOS, or Windows (WSL2)
- **Python**: 3.8+
- **RAM**: 512 MB minimum, 2 GB recommended
- **Disk**: 1 GB (for database and reports)
- **Network**: Stable internet connection
- **Tor**: Must be installed and running locally on port 9050

### Dependencies

```
requests[socks]==2.31.0       # HTTP + SOCKS proxy
beautifulsoup4==4.12.2        # HTML parsing
colorama==0.4.6               # Terminal colors
tqdm==4.66.1                  # Progress bars
fake-useragent==1.4.0         # User agent spoofing
```

---

## 📦 Installation

### Step 1: Install Tor

**Ubuntu/Debian:**
```bash
sudo apt-get update && sudo apt-get install tor -y
sudo service tor start
```

**macOS (Homebrew):**
```bash
brew install tor
brew services start tor
```

**Windows:**
Download from https://www.torproject.org/download/

### Step 2: Clone & Setup

```bash
git clone https://github.com/raaj7z/DarkWeb-Deanonymization.git
cd DarkWeb-Deanonymization
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Step 3: Verify Tor Connection

```bash
curl -x socks5://127.0.0.1:9050 https://check.torproject.org -v
```

### Step 4: Run

```bash
cd src
python3 main.py
```

---

## 🚀 Quick Start

```
╔══════════════════════════════════════════════════════════════╗
║     Dark Web Intelligence & Threat Actor Deanonymization    ║
║                  DarkWeb Crawler v3.0                        ║
╚══════════════════════════════════════════════════════════════╝

[INFO] Checking anonymity...
[INFO] Real IP:  203.0.113.42
[INFO] Tor IP:   198.51.100.89
[SUCCESS] Anonymity confirmed!

[MAIN MENU]
1. Start new crawl session
2. View session history
3. View database stats
4. Search past data by username
5. Exit
6. Autonomous crawl mode
7. Query timeline
8. View actor relationships

Choice [1-8]: _
```

---

## 📊 Menu Options

### Option 1: Start New Crawl Session
Standard web crawling with full extraction pipeline.

**Parameters:**
- Target username (optional) — Filter posts by actor name
- Onion URLs — Enter custom or use defaults
- Crawl depth — Single page or follow links
- Concurrent workers — 1-10 threads
- JS rendering — Enable for dynamic content
- Circuit rotation — Auto-rotate Tor identity

**Output:** Session saved to DB, JSON report generated

### Option 2: View Session History
Browse all past crawl sessions with results summary.

**Shows:**
- Session ID, target username, status
- Usernames found, posts extracted
- Crawl timestamps

### Option 3: View Database Stats
Complete statistics across all tables.

**Displays:**
- Sites, pages, usernames, posts, links
- Crypto addresses, misconfigs, fingerprints
- Trust links, timeline crawls

### Option 4: Search Past Data
Query existing database by username.

**Returns:**
- Post count, source URLs
- Recent content snippets
- Timeline of activity

### Option 5: Exit
Close database and terminate.

### Option 6: Autonomous Crawl Mode ⭐

**Runs continuously without manual input:**
- Duration: Hours of crawling
- Interval: Minutes between crawl cycles
- URL Discovery: Auto-crawls links found in pages
- Target Username: Optional actor tracking

**Output:** Session persisted, all data to database

### Option 7: Query Timeline ⭐

**Search crawls within date range:**
- Start date: `YYYY-MM-DD`
- End date: `YYYY-MM-DD`
- Optional URL filter

**Returns:**
- Descriptor issues detected
- Trust links found
- Temporal distribution

### Option 8: View Actor Relationships ⭐

**Display trust network:**
- Actor username (optional)
- Shows vouch relationships
- Displays wallet associations
- Cross-references

**Output:** Relationship graph for analysis

---

## 🔧 Advanced Usage

### Python API Example

```python
from src.crawler import DarkCrawler
from src.database import Database
from src.alive_checker import AliveChecker

# Initialize
db = Database()
crawler = DarkCrawler(db=db, max_workers=5, rotate_circuits=True)
checker = AliveChecker(timeout=30, retries=3)

# Check alive sites
alive = checker.check_multiple([
    'http://forum.onion',
    'http://market.onion'
])

# Crawl with full extraction
result = crawler.crawl_single(
    'http://forum.onion',
    target_username='actor_xyz'
)

# Access results
print(f"Usernames: {result['usernames']}")
print(f"Crypto: {result['crypto_addresses']}")
print(f"Trust links: {result['trust_links']}")

# Timeline crawling
timeline = crawler.crawl_with_timeline('http://site.onion', 'actor_xyz')
print(f"Crawled: {timeline['timeline']['crawled_at']}")
print(f"Descriptor issues: {timeline['descriptor']['inconsistencies']}")

# Autonomous crawl
auto_result = crawler.autonomous_crawl(
    seed_urls=['http://forum.onion'],
    target_username='actor',
    duration_hours=2,
    interval_minutes=30
)
print(f"URLs discovered: {auto_result['total_urls']}")
```

### Banner Grabbing

```python
crawler = DarkCrawler(db=db)
banner = crawler.grab_service_banner('example.onion', port=443, timeout=5)
print(f"Service: {banner['service']}")
print(f"Version: {banner['version']}")
print(f"Vulnerabilities: {banner['vulnerabilities']}")
```

### SSL Certificate Extraction

```python
ssl_result = crawler.match_ssl_to_clearnet('https://example.onion')
print(f"Clearnet domains found: {ssl_result['clearnet_domains']}")
print(f"Confidence: {ssl_result['confidence']}")  # LOW/MEDIUM/HIGH
```

### Trust Network Analysis

```python
trust_links = crawler.extract_trust_links(html, 'http://forum.onion')
print(f"Relationships: {trust_links['relationship_edges']}")
print(f"Wallet links: {trust_links['wallet_links']}")
```

---

## 🗄️ Database Schema

### Core Tables

| Table | Purpose |
|-------|---------|
| `sessions` | Crawl session metadata |
| `sites` | `.onion` services |
| `pages` | Full HTML snapshots |
| `usernames` | Extracted identities |
| `posts` | Forum messages |
| `links` | URL cross-references |

### Intelligence Tables

| Table | Purpose |
|-------|---------|
| `crypto_addresses` | Bitcoin/Monero/Ethereum addresses |
| `misconfigs` | Security misconfigurations |
| `server_fingerprints` | Server software, language, framework |
| `profiles` | PGP keys, contact methods, aliases |
| `timed_posts` | Posts with timing analysis |
| `timing_analysis` | Activity patterns per actor |

### Deanonymization Tables

| Table | Purpose |
|-------|---------|
| `service_banners` | Port 80/443/22/21/3306 banners |
| `descriptor_checks` | Tor descriptor inconsistencies |
| `trust_links` | Actor relationship graph |
| `timeline_crawls` | Temporal crawl data |

### Queries

```sql
-- Find all usernames on a site
SELECT DISTINCT username FROM usernames 
WHERE source_url LIKE '%example.onion%';

-- Timeline of posts by actor
SELECT timestamp_found, content FROM posts 
WHERE username='actor_xyz' 
ORDER BY extracted_at DESC;

-- Wallet associations
SELECT from_actor, to_actor, wallet_address 
FROM trust_links 
WHERE link_type='wallet';

-- Crawls in date range
SELECT * FROM timeline_crawls 
WHERE date BETWEEN '2024-08-01' AND '2024-08-31';
```

---

## 📤 Output Formats

### JSON Report

**File:** `reports/session_{SESSION_ID}.json`

```json
[
  {
    "url": "http://example.onion",
    "title": "Underground Forum",
    "usernames": ["actor_001", "threat_xyz"],
    "emails": ["actor@riseup.net"],
    "crypto_addresses": {
      "bitcoin": ["1A1z7agoat..."],
      "monero": ["4..."]
    },
    "posts_count": 45,
    "success": true,
    "intel": {
      "server_fingerprint": {...},
      "misconfigs": {...},
      "profiles": {...},
      "timing_analysis": {...}
    }
  }
]
```

### Timeline Data

```
Date: 2024-08-28 | Hour: 14:00 (Tuesday)
URL: http://forum.onion/users/actor_xyz
Issues: 2 | Trust links: 3
```

### Actor Relationships

```
alice → bob [VOUCH]
  Source: http://forum.onion/...

Wallet: 1A1z7agoat2dwjw9w...
  Source: http://market.onion/...
```

---

## 🔓 Deanonymization Techniques

### 1. Service Banner Grabbing
Connects to common ports (80, 443, 22, 21, 3306) and extracts banners revealing real server software.

**Default banners** (e.g., Apache/2.4.41) indicate misconfiguration and can be correlated to known infrastructure.

### 2. SSL Certificate Analysis ⭐
Fetches SSL certificates through Tor SOCKS5 proxy and extracts:
- Subject Alternative Names (SANs) — Often contain real domain
- Common Name (CN) — May reveal clearnet domain
- Issuer — Correlates CA issuance patterns

**Most powerful technique** for origin attribution.

### 3. Tor Descriptor Checking
Analyzes hidden service descriptor for:
- Clearnet URL references in HTML
- Exposed public IP addresses
- Clearnet email addresses
- Server date/timezone mismatches

### 4. Trust Network Correlation
Links actors through:
- Vouch relationships ("verified by user X")
- Wallet associations (same Bitcoin address = same actor)
- PGP signature chains
- Email references across platforms

### 5. Timing Analysis
Correlates posting patterns:
- Peak activity hours
- Timezone estimation
- Cross-platform consistency
- Activity pattern matching

### 6. Behavioral Profiling
Analyzes:
- Post frequency and duration
- Language patterns
- Technical sophistication
- Cryptocurrency usage patterns

---

## 🔧 Troubleshooting

### Tor Connection Issues

```bash
# Check Tor status
sudo service tor status

# Restart Tor
sudo service tor restart

# Verify SOCKS port
netstat -tuln | grep 9050

# Test connection
curl -x socks5://127.0.0.1:9050 https://check.torproject.org
```

### Database Locked

```python
# Always close connections
db.close()

# Or use context manager
with Database() as db:
    db.get_stats()
```

### Timeout/Connection Errors

```python
# Increase timeout
crawler = DarkCrawler(timeout=60, delay=(5, 15))

# Verify site is alive first
checker = AliveChecker(timeout=30)
result = checker.check('http://example.onion')
```

### Import Errors

```bash
source venv/bin/activate
pip install -r requirements.txt --force-reinstall
```

---

## ⚖️ Legal Notice

**This tool must ONLY be used for:**
✅ Authorized law enforcement operations
✅ Government agency authorized research
✅ Authorized corporate security research
✅ Penetration testing with written permission
✅ Academic research with IRB approval

**This tool must NOT be used for:**
❌ Unauthorized network access
❌ Data theft or privacy violations
❌ Harassment or targeting of individuals
❌ Illegal intelligence gathering
❌ Violating CFAA or international law

**Disclaimer**: Users are solely responsible for compliance. Developers assume no liability for misuse.

---

## 📚 Resources

- [Tor Documentation](https://www.torproject.org/)
- [OSINT Framework](https://osintframework.com/)
- [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/)
- [SQLite3 Docs](https://www.sqlite.org/docs.html)
- [Python Requests](https://docs.python-requests.org/)

---

**Version:** 3.0  
**Last Updated:** September 2026  
**Maintainer:** [@raaj7z](https://github.com/raaj7z)  
**License:** Authorized Use Only
