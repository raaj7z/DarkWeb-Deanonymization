# DarkWeb-Deanonymization
 Dark web intelligence system for Tor hidden service deanonymizantion, cross-platform threat actor profiling, and clearnet entity attribution.

## What it does
Integrated OSINT framework that automatically identifies and 
de-anonymizes threat actors operating on the dark web.

## Modules
- `crawler.py` — Dark web crawler through Tor
- `alive_checker.py` — Check if onion sites are alive
- `database.py` — SQLite storage for all data
- `utils.py` — Tor connection + utilities
- `main.py` — Run full investigation

## How to run
```bash
# Start Tor first
sudo service tor start

# Install dependencies
pip3 install -r requirements.txt

# Run
cd src
python3 main.py
