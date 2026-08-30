
import requests
import logging
import random
from colorama import Fore, Style, init
from datetime import datetime
import sqlite3
import os

init(autoreset=True)

# colours
def success(msg): print(f"{Fore.GREEN}[+]{Style.RESET_ALL} {msg}")
def error(msg):   print(f"{Fore.RED}[-]{Style.RESET_ALL} {msg}")
def info(msg):    print(f"{Fore.CYAN}[*]{Style.RESET_ALL} {msg}")
def warn(msg):    print(f"{Fore.YELLOW}[!]{Style.RESET_ALL} {msg}")

# sessions
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; rv:102.0) Gecko/20100101 Firefox/102.0',
    'Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0',
    'Mozilla/5.0 (X11; Linux x86_64; rv:102.0) Gecko/20100101 Firefox/102.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:102.0) Gecko/20100101 Firefox/102.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:115.0) Gecko/20100101 Firefox/115.0',
]

def get_tor_session(retries=3):
    """Create a requests session routed through Tor"""
    session = requests.Session()
    session.proxies = {
        'http':  'socks5h://127.0.0.1:9050',
        'https': 'socks5h://127.0.0.1:9050'
    }
    session.headers.update({
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
    })
    return session

def verify_tor(session):
    try:
        r = session.get('http://check.torproject.org', timeout=15)
        if 'Congratulations' in r.text:
            success("Tor connection verified!")
            return True
        else:
            warn("Connected but Tor verification failed")
            return False
    except Exception as e:
        error(f"Tor connection failed: {e}")
        return False

def get_real_ip():
    try:
        r = requests.get('https://api.ipify.org', timeout=5)
        return r.text.strip()
    except:
        return "Unknown"

def get_tor_ip(session):
    try:
        r = session.get('http://ifconfig.me', timeout=15)
        return r.text.strip()
    except:
        return "Unknown"

# ── LOGGING ──
def setup_logger(name='DarkCrawler'):
    os.makedirs('logs', exist_ok=True)
    log_file = f"logs/crawl_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(name)

# ── BANNER ──
def print_banner():
    banner = f"""
{Fore.RED}
██████╗  █████╗ ██████╗ ██╗  ██╗     ██████╗██████╗  █████╗ ██╗    ██╗██╗     ███████╗██████╗
██╔══██╗██╔══██╗██╔══██╗██║ ██╔╝    ██╔════╝██╔══██╗██╔══██╗██║    ██║██║     ██╔════╝██╔══██╗
██║  ██║███████║██████╔╝█████╔╝     ██║     ██████╔╝███████║██║ █╗ ██║██║     █████╗  ██████╔╝
██║  ██║██╔══██║██╔══██╗██╔═██╗     ██║     ██╔══██╗██╔══██║██║███╗██║██║     ██╔══╝  ██╔══██╗
██████╔╝██║  ██║██║  ██║██║  ██╗    ╚██████╗██║  ██║██║  ██║╚███╔███╔╝███████╗███████╗██║  ██║
╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝    ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚══╝╚══╝ ╚══════╝╚══════╝╚═╝  ╚═╝
{Style.RESET_ALL}
{Fore.CYAN}         Dark Web Threat Actor De-anonymization Framework
        IIT Patna Team 
{Style.RESET_ALL}
    """
    print(banner)
