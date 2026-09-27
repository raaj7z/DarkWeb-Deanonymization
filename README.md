# DarkWeb-Deanonymization

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Tor](https://img.shields.io/badge/Tor-SOCKS5-purple.svg)](https://www.torproject.org/)
[![Playwright](https://img.shields.io/badge/Playwright-Async-green.svg)](https://playwright.dev/)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)]()

> Autonomous Dark Web Onion Crawler & Operational Security (OPSEC) Exposure Analyzer.

---

## 📋 Table of Contents
- [Overview](#overview)
- [Architecture & Modules](#architecture--modules)
- [Repository Structure](#repository-structure)
- [Key Features](#key-features)
- [Environment Requirements](#environment-requirements)
- [Installation & Setup](#installation--setup)
- [Usage & CLI Reference](#usage--cli-reference)
  - [Windows Command Line](#windows-command-line)
  - [Linux / WSL with Native Tor](#linux--wsl-with-native-tor)
- [OPSEC Misconfiguration Categories](#opsec-misconfiguration-categories)
- [Output Data Formats](#output-data-formats)

---

## 🔍 Overview

**DarkWeb-Deanonymization** is a command-line dark web intelligence crawler designed to de-anonymize `.onion` hidden services by detecting technical misconfigurations and operational security exposures. It harvests PGP keys, cryptocurrency wallet addresses, clearnet domain references, exposed Apache `/server-status` pages, SSL/TLS certificate Subject Alternative Names (SANs), and default SSH/Web service banners.

---

## 🏗️ Architecture & Modules

```
                        +----------------------------+
                        |      CLI Entry Point       |
                        |       (src/cli.py)         |
                        +-------------+--------------+
                                      |
                                      v
                        +----------------------------+
                        |     Onion Web Crawler      |
                        |     (src/crawler.py)       |
                        +-------------+--------------+
                                      | SOCKS5 Proxy
                                      v
                        +----------------------------+
                        |   Tor Proxy Controller     |
                        | (src/tor_controller.py)    |
                        +-------------+--------------+
                                      |
       +-----------------+------------+------------+-----------------+
       |                 |                         |                 |
       v                 v                         v                 v
+--------------+  +--------------+          +--------------+  +--------------+
| Server Status|  | TLS Cert     |          | Service      |  | Intel        |
| Detector     |  | Extractor    |          | Banner       |  | Harvester    |
| (src/server_ |  | (src/tls.py) |          | Scanner      |  | (src/intel_  |
|  status.py)  |  +--------------+          | (src/banner. |  |  extractor.  |
+--------------+                            |  py)         |  |  py)         |
                                            +--------------+  +--------------+
                                                                     |
                                                                     v
                                                            +----------------+
                                                            | Report Builder |
                                                            | (src/report_   |
                                                            |  generator.py) |
                                                            +----------------+
```

---

## 📁 Repository Structure

```
DarkWeb-Deanonymization/
├── src/
│   ├── cli.py                 # Main CLI command-line interface
│   ├── main.py                # Pipeline execution wrapper
│   ├── crawler.py             # Async onion website crawler
│   ├── tor_controller.py      # Tor SOCKS5 proxy status checker & connector
│   ├── server_status.py       # Exposed /server-status and /server-info detector
│   ├── tls.py                 # SSL/TLS Certificate CN & SAN clearnet link extractor
│   ├── banner.py              # Default SSH, FTP, Apache, Nginx banner scanner
│   ├── intel_extractor.py     # PGP key, Crypto wallet, Email, Handle harvester
│   ├── report_generator.py   # Exporters for JSON, JSONL, CSV reports
│   ├── captcha_handler.py     # Captcha detection and handling routines
│   ├── js_renderer.py         # Headless browser (Playwright) dynamic JS renderer
│   ├── ai_cleaner.py          # Noise reduction and text cleaner
│   ├── alive_checker.py       # Onion service HTTP/SOCKS reachability validator
│   ├── config.py              # Crawler settings and regex configurations
│   ├── database.py            # SQLite session storage
│   ├── models.py              # Data models for findings, pages, and targets
│   ├── db/
│   │   ├── schema.py          # SQLite database schema
│   │   └── queries.py         # Database query helpers
│   └── reports/
│       ├── actor_report.py    # Threat actor report formatter
│       ├── network_report.py  # Network exposure report formatter
│       └── exporters.py       # File export helper functions
├── data/                      # Session database files
├── logs/                      # Session execution log files
├── output/                    # Crawl session reports (JSON, JSONL, CSV)
├── .gitignore                 # Git ignore rules for outputs and logs
└── requirements.txt           # Python dependencies
```

---

## ✨ Key Features

- **Onion Crawling over Tor**: Crawls `.onion` hidden services via SOCKS5 proxy (`127.0.0.1:9050`).
- **Exposed Server-Status Detection**: Detects unauthenticated Apache `/server-status` and `/server-info` pages revealing client IP addresses.
- **SSL/TLS Certificate Leak Harvesting**: Extracts Subject Alternative Names (SANs) and Common Names (CNs) from TLS certificates to uncover associated clearnet domains.
- **Service Banner Fingerprinting**: Collects OpenSSH, Apache, Nginx, and FTP banners to match against clear-web server footprints.
- **Technical Intelligence Extraction**: Automatically harvests Bitcoin (BTC) addresses, PGP Public Keys, email addresses, and social handles.
- **Structured Exporting**: Generates standardized JSON, JSONL, CSV reports and updates SQLite database tables.

---

## 🔧 Environment Requirements

- **Python**: Python 3.10+
- **Tor Proxy**: Tor daemon running on `127.0.0.1:9050` (via Linux, WSL `sudo service tor start`, or Windows Tor SOCKS Bridge).
- **Playwright** (Optional for JS rendering): `playwright install chromium`

---

## 🚀 Installation & Setup

1. **Clone Repository**:
   ```bash
   git clone https://github.com/raaj7z/DarkWeb-Deanonymization.git
   cd DarkWeb-Deanonymization
   ```

2. **Set up Virtual Environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\Activate.ps1
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

---

## 💻 Usage & CLI Reference

### Windows Command Line

```powershell
# Run a single target crawl via local SOCKS proxy
python -m src.cli scan --url "http://darkmarket-v2.onion" --socks 127.0.0.1:9050
```

### Linux / WSL with Native Tor

```bash
# Start Tor daemon
sudo service tor start

# Execute crawler with depth=2
python -m src.cli crawl --url "http://darkmarket-v2.onion" --depth 2 --output output/
```

### CLI Command Options

| Argument | Description | Default |
| :--- | :--- | :--- |
| `--url` | Target `.onion` service URL | Required |
| `--socks` | SOCKS5 proxy address | `127.0.0.1:9050` |
| `--depth` | Maximum crawling depth | `2` |
| `--output` | Output report directory | `output/` |

---

## 🛡️ OPSEC Misconfiguration Categories

1. **Exposed Server Status**: Publicly accessible `/server-status` exposing active HTTP connections and internal IP addresses.
2. **Clearnet SSL/TLS Certificate**: Certificates sharing common SAN/CN fields between `.onion` hidden services and clearnet `.com`/`.org` domains.
3. **Default Service Banners**: Server software banners exposing specific OS build versions (e.g. `OpenSSH_7.9p1 Debian 10`).
4. **Descriptor & Metadata Inconsistency**: Clearnet emails, author handles, or PGP key signatures embedded in web source metadata.

---

## 📜 License

Proprietary — Dark Web OPSEC De-anonymization Module.
