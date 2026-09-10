#!/usr/bin/env bash
# setup.sh — system-level dependencies for DarkWeb-Deanonymization
# Run once:  bash setup.sh

set -e

echo "==> Installing system packages..."
sudo apt update
sudo apt install -y python3 python3-pip python3-venv tor

echo "==> Starting Tor service..."
sudo service tor start

echo "==> Enabling Tor control port (for circuit rotation)..."
if ! grep -q "^ControlPort 9051" /etc/tor/torrc; then
    echo "ControlPort 9051" | sudo tee -a /etc/tor/torrc
    echo "CookieAuthentication 1" | sudo tee -a /etc/tor/torrc
    sudo service tor restart
fi

echo "==> Creating Python virtualenv..."
python3 -m venv venv
source venv/bin/activate

echo "==> Installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

echo "==> Creating data folders..."
mkdir -p data output logs reports

echo "==> Verifying..."
python3 -c "import requests, socks, bs4, cryptography, base58, stem, reportlab; print('Python packages OK')"
curl -s -x socks5://127.0.0.1:9050 https://check.torproject.org/api/ip | grep -q '"IsTor":true' \
    && echo "Tor OK" \
    || echo "WARNING: Tor check failed"

echo ""
echo "=========================================="
echo "Setup complete."
echo "Run:  source venv/bin/activate && python src/cli.py"
echo "=========================================="
