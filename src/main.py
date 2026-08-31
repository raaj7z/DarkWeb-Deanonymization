# main.py — v2.0
# FIXED: Custom URL input, history viewing, session management
import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import print_banner, info, success, error, warn
from utils import get_tor_session, get_real_ip, get_tor_ip
from alive_checker import AliveChecker
from crawler import DarkCrawler
from database import Database

def verify_anonymity():
    session = get_tor_session()
    real_ip = get_real_ip()
    tor_ip  = get_tor_ip(session)
    
    info(f"Real IP : {real_ip}")
    info(f"Tor IP  : {tor_ip}")
    
    if real_ip == tor_ip:
        error("DANGER: Same IP! Start Tor first: sudo service tor start")
        return False, session
    
    success("Anonymity confirmed!")
    return True, session

def get_urls_from_user():
    """FIXED: Let user enter custom onion URLs"""
    print("\n" + "="*50)
    print("URL INPUT OPTIONS")
    print("="*50)
    print("1. Enter custom onion URL(s)")
    print("2. Use default test URLs")
    print("3. Load from file (data/urls.txt)")
    
    choice = input("\nChoice [1/2/3]: ").strip()
    
    if choice == '1':
        urls = []
        print("\nEnter onion URLs (one per line, empty line to finish):")
        while True:
            url = input("URL: ").strip()
            if not url:
                break
            if not url.startswith('http'):
                url = 'http://' + url
            urls.append(url)
        return urls
    
    elif choice == '3':
        try:
            with open('data/urls.txt', 'r') as f:
                urls = [line.strip() for line in f if line.strip()]
            info(f"Loaded {len(urls)} URLs from file")
            return urls
        except:
            error("data/urls.txt not found. Using defaults.")
    
    # Default test URLs
    return [
        'http://duckduckgogg42xjoc72x3sjasowoarfbgcmvfimaftt6twagswzczad.onion',
        'http://protonmailrmez3lotccipshtkleegetolb73fuirgj7r4o4vfu7ozyd.onion',
    ]

def show_history(db):
    """Show past sessions and searches"""
    print("\n" + "="*50)
    print("SEARCH HISTORY")
    print("="*50)
    
    sessions = db.get_all_sessions()
    if not sessions:
        warn("No previous sessions found")
        return
    
    for s in sessions[:10]:
        status_color = "✅" if s['status'] == 'completed' else "🔄"
        print(f"\n{status_color} Session: {s['session_id']}")
        print(f"   Target: {s['target_username'] or 'All'}")
        print(f"   Started: {s['started_at']}")
        print(f"   Status: {s['status']}")
        
        if s['summary']:
            summary = json.loads(s['summary'])
            print(f"   Found: {summary.get('usernames', 0)} usernames, "
                  f"{summary.get('posts', 0)} posts")

def show_full_stats(db):
    """Show complete database statistics"""
    print("\n" + "="*50)
    print("DATABASE STATS (ALL TIME)")
    print("="*50)
    stats = db.get_stats()
    for table, count in stats.items():
        print(f"  {table:15} → {count} records")

def main_menu(db):
    """Main interactive menu"""
    print("\n" + "="*50)
    print("MAIN MENU")
    print("="*50)
    print("1. Start new crawl session")
    print("2. View session history")
    print("3. View database stats")
    print("4. Search past data by username")
    print("5. Exit")
    
    return input("\nChoice [1-5]: ").strip()

def search_past_data(db):
    """Search existing database for a username"""
    username = input("Enter username to search: ").strip()
    if not username:
        return
    
    posts = db.get_posts_by_username(username)
    usernames = db.get_all_usernames()
    
    print(f"\nFound {len(posts)} posts for '{username}'")
    print(f"Total unique usernames in DB: {len(usernames)}")
    
    if posts:
        print("\nRecent posts:")
        for post in posts[:3]:
            print(f"\n  [{post['extracted_at']}]")
            print(f"  Source: {post['source_url'][:50]}")
            print(f"  Content: {post['content'][:200]}...")
    
    # Log this search
    db.log_search('manual', 'username_search', username, len(posts))

def run_crawl_session(db, session):
    """Run a complete crawl session"""
    
    # Get target username
    target = input("\nTarget username to track (Enter to skip): ").strip()
    target = target if target else None
    
    # Get URLs
    urls = get_urls_from_user()
    if not urls:
        error("No URLs provided")
        return
    
    # Get crawl depth
    try:
        depth = int(input("Crawl depth [1=single page, 2=follow links]: ").strip() or '1')
    except:
        depth = 1
    
    # Get workers
    try:
        workers = int(input("Concurrent workers [1-10, default 3]: ").strip() or '3')
        workers = max(1, min(10, workers))
    except:
        workers = 3
    
    # Ask about JS rendering
    use_js_input = input("Enable JS rendering for dynamic pages? [y/N]: ").strip().lower()
    use_js = use_js_input == 'y'
    
    # Ask about circuit rotation
    rotate_input = input("Enable Tor circuit rotation? [Y/n]: ").strip().lower()
    rotate = rotate_input != 'n'
    
    # Ask rotation frequency
    rotate_every = 10
    if rotate:
        try:
            rotate_every = int(input("Rotate circuit every N requests [default 10]: ").strip() or '10')
        except:
            rotate_every = 10
    
    # Create session in DB FIRST (before using session_id)
    session_id = db.create_session(target, urls)
    
    # Log the search
    db.log_search(session_id, 'url_crawl', 
                  json.dumps(urls), len(urls))
    
    # Initialize components
    checker = AliveChecker(timeout=30, retries=3)
    crawler = DarkCrawler(
        db=db,
        session_id=session_id,
        delay=(1, 3),
        timeout=30,
        max_workers=workers,
        use_js=use_js,
        rotate_circuits=rotate,
        rotate_every=rotate_every
    )
    
    # Step 1: Check alive
    info("\n=== STEP 1: Checking alive URLs ===")
    alive_results = checker.check_multiple(urls)
    alive_urls = [r['url'] for r in alive_results['alive']]
    
    if not alive_urls:
        error("No alive URLs. Check Tor connection.")
        return
    
    success(f"Alive: {len(alive_urls)}/{len(urls)}")
    
    # Step 2: Crawl concurrently
    info(f"\n=== STEP 2: Crawling ({workers} workers) ===")
    results = crawler.crawl_concurrent(alive_urls, target_username=target, use_js=use_js)
    
    # Step 3: Summary
    total_usernames = sum(len(r.get('usernames', [])) for r in results)
    total_posts     = sum(len(r.get('posts', [])) for r in results)
    total_emails    = sum(len(r.get('emails', [])) for r in results)
    
    summary = {
        'usernames': total_usernames,
        'posts': total_posts,
        'emails': total_emails,
        'urls_crawled': len(alive_urls)
    }
    
    db.complete_session(session_id, summary)
    
    # Step 4: Show results
    info(f"\n=== SESSION COMPLETE: {session_id} ===")
    success(f"Usernames found : {total_usernames}")
    success(f"Posts extracted : {total_posts}")
    success(f"Emails found    : {total_emails}")
    
    # Step 5: Save report
    os.makedirs('reports', exist_ok=True)
    report_file = f"reports/session_{session_id}.json"
    
    with open(report_file, 'w') as f:
        serializable = [{
            'url': r['url'],
            'title': r.get('title', ''),
            'usernames': r.get('usernames', []),
            'emails': r.get('emails', []),
            'posts_count': len(r.get('posts', [])),
            'timestamps': r.get('timestamps', []),
            'success': r.get('success', False)
        } for r in results]
        json.dump(serializable, f, indent=2)
    
    success(f"Report saved: {report_file}")

def main():
    print_banner()
    
    # Verify Tor
    info("Checking anonymity...")
    is_anonymous, session = verify_anonymity()
    if not is_anonymous:
        return
    
    # Initialize DB — single persistent database
    db = Database()
    
    # Show overall stats on startup
    stats = db.get_stats()
    info(f"Database loaded — {stats.get('sessions', 0)} previous sessions")
    
    # Main loop
    while True:
        choice = main_menu(db)
        
        if choice == '1':
            run_crawl_session(db, session)
        
        elif choice == '2':
            show_history(db)
        
        elif choice == '3':
            show_full_stats(db)
        
        elif choice == '4':
            search_past_data(db)
        
        elif choice == '5':
            info("Closing database...")
            db.close()
            success("Goodbye!")
            break
        
        else:
            warn("Invalid choice")

if __name__ == '__main__':
    main()
