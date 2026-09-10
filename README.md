# DarkWeb-Deanonymization

**SIH26151 — NTRO Dark Web Threat Actor De-anonymization**

Advanced Tor hidden service crawler with AI-based entity triage, network infrastructure analysis, and structured reporting for OSINT handoff.

---

## Pipeline

```
Crawler → AI Cleaner → 2 buckets → 3 report tiers
```

1. **Crawler** collects pages via Tor, extracts raw intelligence
2. **AI Cleaner** classifies findings into actor + network buckets
3. **Three report tiers** produced for every session

| Tier | Output | Purpose |
|------|--------|---------|
| 1 | `reports/report_<id>.json` | Full DB snapshot (all tables) — audit trail |
| 2 | `output/session_<id>/actor_report.json` | **Report 1** — handoff to OSINT engine |
| 2 | `output/session_<id>/network_report.json` | **Report 2** — network infrastructure |
| 3 | `output/session_<id>/*.csv / *.jsonl` | Exports for spreadsheets / external tools |

---

## Quick Start

### One-shot setup (Linux / WSL)

```bash
bash setup.sh
```

### Manual setup

```bash
# System packages
sudo apt install -y python3 python3-venv tor
sudo service tor start

# Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Folders
mkdir -p data output logs reports
```

### Run

```bash
source venv/bin/activate
python src/cli.py
```

---

## Features

### Crawling
- Tor-routed HTTP via SOCKS5
- Multi-threaded (configurable workers, thread-safe)
- Circuit rotation (via stem, optional)
- CAPTCHA / block detection (no bypass — honest)
- Optional JS rendering (Selenium + Chromium)
- Autonomous mode: continuous crawl with URL discovery

### Extraction
- Usernames, handles, aliases
- Crypto wallets (BTC, BTC-bech32, ETH, XMR, LTC, DASH, Zcash)
- Base58 checksum validation for BTC/LTC/DASH
- PGP keys, emails, Telegram, Jabber, Session IDs
- Posts with timestamps + preserved raw HTML (for stylometry)
- Trust links (vouches, wallet associations, PGP signature chains)

### Network Intelligence (SIH Capability 1)
- SOCKS-based **banner grabbing** (SSH/HTTP/FTP/SMTP/MySQL)
- SOCKS-based **TLS certificate fetch** (SANs, CN, issuer, fingerprint)
- **Server-status probing**: `/server-status`, `/nginx_status`, `/phpinfo`, `/.env`, `/.git/config`, `/backup.sql`
- **Descriptor leak analysis**: clearnet URLs, exposed IPs, clearnet emails, server date leakage
- Default banner detection (Apache/2.4.41, nginx/1.18.0, OpenSSH_7.9)

### AI Filter
- Rule-based 2-bucket classifier (actor / network)
- Username deduplication + blacklist
- Boilerplate stripping
- Category tagging: `drugs`, `arms`, `data`, `hacking`, `finance`, `unknown`
- Confidence scoring: `LOW`, `MEDIUM`, `HIGH`, `VERY_HIGH`
- Optional ML layer (scikit-learn hook, disabled by default)

### Reporting
- **Tier 1**: full DB snapshot (via `report_generator.py`)
- **Tier 2**: two focused JSON reports (actor + network)
- **Tier 3**: CSV + JSONL exports
- Timeline queries
- Actor relationship graph data

---

## Module Map

| File | Purpose |
|------|---------|
| `config.py` | Paths, toggles, categories, blacklist |
| `logging_setup.py` | Structured logger (console + file) |
| `models.py` | Entity dataclasses (`OsintEntity`, `StyloPost`, `NetworkArtifact`) |
| `utils.py` | Tor session, colored output, IP checks |
| `ai_cleaner.py` | Two-bucket classifier |
| `intel_extractor.py` | Extraction + checksum validation + raw HTML preservation |
| `banner.py` | SOCKS-based banner grabbing |
| `tls.py` | SOCKS-based TLS cert fetch |
| `server_status.py` | Misconfiguration endpoint probing |
| `crawler.py` | Main crawler (v3.1, thread-safe) |
| `alive_checker.py` | URL liveness check |
| `captcha_handler.py` | CAPTCHA / block detection |
| `tor_controller.py` | Circuit rotation via stem |
| `js_renderer.py` | Optional Selenium rendering |
| `database.py` | Original DB layer (all tables) |
| `db/schema.py` | New tables + standard columns |
| `db/queries.py` | New-table read/write helpers |
| `service.py` | Pure functions (CLI + future UI) |
| `cli.py` | Interactive menu |
| `report_generator.py` | Full DB snapshot (Tier 1) |
| `reports/actor_report.py` | Report 1 — Actor intelligence |
| `reports/network_report.py` | Report 2 — Network infrastructure |
| `reports/exporters.py` | CSV / JSON / JSONL export |
| `reports/report_builder.py` | One-shot report pipeline |

---

## Database Schema

### Original tables (from `database.py`)
`sessions`, `sites`, `site_checks`, `pages`, `usernames`, `posts`, `links`, `investigations`, `crypto_addresses`, `misconfigs`, `server_fingerprints`, `profiles`, `timed_posts`, `timing_analysis`, `service_banners`, `descriptor_checks`, `trust_links`, `timeline_crawls`

### New tables (from `db/schema.py`)
| Table | Purpose |
|-------|---------|
| `osint_entities` | Handles, wallets, PGP, emails, channels |
| `stylo_posts` | Author-tagged posts + raw HTML refs |
| `network_artifacts` | TLS, banners, server-status, headers, paths |
| `actor_ids` | Actor ID registry (`ACT-001`, etc.) |
| `jobs` | Background job tracking |

---

## CLI Menu

```
1. Start new crawl session    → runs all 3 report tiers
2. View session history
3. View database stats
4. Search past data by username
5. Exit
6. Autonomous crawl mode
7. Query timeline
8. View actor relationships
9. Session summary (new tables)
```

---

## SIH26151 Capability Mapping

| PS Requirement | Implementation |
|----------------|----------------|
| Misconfiguration detection (server-status, banners, TLS) | `server_status.py`, `banner.py`, `tls.py` |
| SSL cert SAN analysis | `intel_extractor.get_ssl_info` |
| Relationship graph data | `crawler.extract_trust_links()` → `trust_links` table |
| Actor profiles (handles, wallets, PGP) | `ai_cleaner.py` → `osint_entities` table |
| Timeline query | `cli.py` option 7 |
| Autonomous mode | `crawler.autonomous_crawl()` |
| CSV / JSON export | `reports/exporters.py` + `report_generator.py` |
| AI-based analysis | `ai_cleaner.py` (rules + confidence scoring) |

**Future work (OSINT engine repo):**
- Stylometric persona linkage
- Cross-marketplace actor resolution
- Blockchain enrichment (wallet clustering)
- Threat feed correlation
- Analytical dashboard (Flask / Streamlit)

---

## Testing

```bash
# Full pipeline sanity check (no Tor needed)
python test_pipeline.py

# CLI (needs Tor running)
python src/cli.py
```

---

## Output Structure

```
output/
  session_<id>/
    raw_pages/             # Full HTML per crawled page
    raw_posts/             # Preserved post HTML (for stylometry)
    actor_report.json      # Report 1
    network_report.json    # Report 2
    actor.json             # Raw rows for OSINT
    actor.jsonl
    actor.csv
    network.json
    network.jsonl
    network.csv
reports/
  report_<id>.json         # Tier 1 full snapshot
logs/
  crawl_YYYYMMDD.log
data/
  crawler.db               # SQLite (WAL mode)
```

---

## Legal & Ethical Notice

This tool is designed for **authorized law enforcement, government agencies, and authorized security research only**. Unauthorized access to computer systems is illegal under the Computer Fraud & Abuse Act (CFAA) and applicable international law. All users are responsible for compliance.

---

**Version:** 4.0
**Last Updated:** September 2026
**Maintainer:** @raaj7z
**License:** Authorized Use Only
