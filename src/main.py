
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import print_banner, info, success, error, get_tor_session, verify_tor, get_real_ip, get_tor_ip
from alive_checker import AliveChecker
from crawler import DarkCrawler
from database import Database
import json

def main():
    print_banner()
    
    info("Starting Dark Web Crawler...")
    session = get_tor_session()
  
    info("Verifying Tor connection...")
    real_ip = get_real_ip()
    tor_ip = get_tor_ip(session)
    
    info(f"Real IP:  {real_ip}")
    info(f"Tor IP:   {tor_ip}")
    
    if real_ip == tor_ip:
        error("WARNING: Real IP and Tor IP are the same — Tor may not be working!")
        return
    
    success("Anonymity confirmed — IPs are different!")
    

    db = Database()
    checker = AliveChecker(timeout=30, retries=3)
    crawler = DarkCrawler(db=db, delay=(2, 5), timeout=30)
    
    # ── TEST URLS — Legal .onion sites ──
    test_urls = [
        'http://duckduckgogg42xjoc72x3sjasowoarfbgcmvfimaftt6twagswzczad.onion',
        'http://protonmailrmez3lotccipshtkleegetolb73fuirgj7r4o4vfu7ozyd.onion',
    ]
    
    # ── STEP 1: Check alive ──
    info("\n=== STEP 1: Checking which URLs are alive ===")
    alive_results = checker.check_multiple(test_urls)
    alive_urls = [r['url'] for r in alive_results['alive']]
    
    if not alive_urls:
        error("No alive URLs found. Check your Tor connection.")
        return
    
    success(f"Found {len(alive_urls)} alive URLs")
    
    # ── STEP 2: Crawl ──
    info("\n=== STEP 2: Crawling alive URLs ===")
    target = input("\nEnter target username to search (or press Enter to crawl all): ").strip()
    target = target if target else None
    
    results = crawler.crawl_multiple(alive_urls, target_username=target)
    
    # ── STEP 3: Show database stats ──
    info("\n=== STEP 3: Database Stats ===")
    stats = db.get_stats()
    for table, count in stats.items():
        info(f"{table}: {count} records")
    
    # ── STEP 4: Save results ──
    import os
    os.makedirs('reports', exist_ok=True)
    report_file = f"reports/crawl_results.json"
    
    with open(report_file, 'w') as f:
        # Convert to serializable format
        serializable = []
        for r in results:
            serializable.append({
                'url': r['url'],
                'title': r.get('title', ''),
                'usernames': r.get('usernames', []),
                'emails': r.get('emails', []),
                'posts_count': len(r.get('posts', [])),
                'timestamps': r.get('timestamps', []),
                'crypto': r.get('crypto_addresses', {}),
                'success': r.get('success', False)
            })
        json.dump(serializable, f, indent=2)
    
    success(f"\nResults saved to {report_file}")
    success("Crawl session complete!")
    
    db.close()

if __name__ == '__main__':
    main()
