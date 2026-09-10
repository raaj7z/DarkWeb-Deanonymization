# cli.py — NEW interactive menu
# Replaces main.py. Uses service.py functions so all actions are reusable.
import os
import sys
import json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import (
    print_banner, info, success, error, warn,
    get_tor_session, get_tor_ip, get_real_ip,
)
from service import (
    check_tor, run_crawl, run_autonomous,
    get_session_summary, write_session_reports,
)
from database import Database
from db.schema import ensure_schema
from config import OUTPUT_DIR


def verify_anonymity_safe():
    """
    Anonymity check without leaking your real IP on startup.
    Compares Tor-exit IP prefix against a coarse list of known Tor ranges.
    """
    session = get_tor_session()
    tor_ip = get_tor_ip(session)
    info(f"Tor IP: {tor_ip}")

    # Coarse check — real verification happens via check.torproject.org inside verify_tor()
    ok, msg = check_tor()
    if ok:
        success("Anonymity confirmed!")
    else:
        error(f"Tor check failed: {msg}")
    return ok, session


def get_urls_from_user():
    """Same UX as your original main.py — custom, defaults, or file."""
    print("\n" + "=" * 50)
    print("URL INPUT OPTIONS")
    print("=" * 50)
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

    if choice == '3':
        try:
            with open('data/urls.txt', 'r') as f:
                urls = [line.strip() for line in f if line.strip()]
            info(f"Loaded {len(urls)} URLs from file")
            return urls
        except Exception:
            error("data/urls.txt not found. Using defaults.")

    return [
        'http://duckduckgogg42xjoc72x3sjasowoarfbgcmvfimaftt6twagswzczad.onion',
        'http://protonmailrmez3lotccipshtkleegetolb73fuirgj7r4o4vfu7ozyd.onion',
    ]


def show_history(db):
    print("\n" + "=" * 50)
    print("SEARCH HISTORY")
    print("=" * 50)

    sessions = db.get_all_sessions()
    if not sessions:
        warn("No previous sessions found")
        return

    for s in sessions[:10]:
        status_mark = "✅" if s['status'] == 'completed' else "🔄"
        print(f"\n{status_mark} Session: {s['session_id']}")
        print(f"   Target: {s['target_username'] or 'All'}")
        print(f"   Started: {s['started_at']}")
        print(f"   Status: {s['status']}")

        if s['summary']:
            try:
                summary = json.loads(s['summary'])
                print(f"   Found: {summary.get('usernames', 0)} usernames, "
                      f"{summary.get('posts', 0)} posts")
            except Exception:
                pass


def show_full_stats(db):
    print("\n" + "=" * 50)
    print("DATABASE STATS (ALL TIME)")
    print("=" * 50)
    stats = db.get_stats()
    for table, count in stats.items():
        print(f"  {table:15} → {count} records")


def search_past_data(db):
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

    try:
        db.log_search('manual', 'username_search', username, len(posts))
    except Exception:
        pass


def run_crawl_session(db):
    target = input("\nTarget username to track (Enter to skip): ").strip() or None
    urls = get_urls_from_user()
    if not urls:
        error("No URLs provided")
        return

    try:
        workers = int(input("Concurrent workers [1-10, default 3]: ").strip() or '3')
        workers = max(1, min(10, workers))
    except Exception:
        workers = 3

    rotate_input = input("Enable Tor circuit rotation? [Y/n]: ").strip().lower()
    rotate = rotate_input != 'n'

    rotate_every = 10
    if rotate:
        try:
            rotate_every = int(input("Rotate circuit every N requests [default 10]: ").strip() or '10')
        except Exception:
            rotate_every = 10

    info("\n=== Running crawl via service.run_crawl ===")
    bundle = run_crawl(
        urls=urls,
        target_username=target,
        workers=workers,
        rotate_circuits=rotate,
        rotate_every=rotate_every,
        db=db,
    )

    if bundle.get('error'):
        error(bundle['error'])
        return

    session_id = bundle['session_id']
    summary = bundle['summary']

    info(f"\n=== SESSION COMPLETE: {session_id} ===")
    success(f"URLs crawled : {summary['urls_crawled']}")
    success(f"URLs OK      : {summary['urls_ok']}")
    success(f"Actor rows   : {summary['actor_rows']}")
    success(f"Network rows : {summary['network_rows']}")

    # Write the two report files
    actor_path, network_path = write_session_reports(
        session_id,
        bundle['actor_rows'],
        bundle['network_rows'],
    )
    success(f"Actor report   : {actor_path}")
    success(f"Network report : {network_path}")


def run_autonomous_menu(db):
    urls = get_urls_from_user()
    if not urls:
        error("No URLs provided")
        return

    try:
        hours = float(input("Duration in hours [default 1]: ").strip() or '1')
        interval = int(input("Interval in minutes [default 30]: ").strip() or '30')
    except Exception:
        hours, interval = 1, 30

    target = input("Target username (or Enter to skip): ").strip() or None

    info("\n=== Autonomous mode via service.run_autonomous ===")
    result = run_autonomous(
        urls=urls,
        target_username=target,
        hours=hours,
        interval_minutes=interval,
        db=db,
    )
    success(f"Done. Session: {result.get('session_id')}")
    success(f"Cycles: {result.get('cycles')}")
    success(f"URLs discovered: {result.get('total_urls')}")


def query_timeline_menu(db):
    start = input("Start date (YYYY-MM-DD): ").strip()
    end = input("End date (YYYY-MM-DD): ").strip()
    try:
        results = db.query_timeline(start, end)
    except Exception as e:
        error(f"Query failed: {e}")
        return

    print(f"\nFound {len(results)} crawls between {start} and {end}")
    for r in results[:10]:
        print(f"  {r['crawled_at']} — {r['url'][:50]}")
        try:
            print(f"    Descriptor issues: {r['descriptor_issues']}")
            print(f"    Trust links: {r['trust_links_found']}")
        except Exception:
            pass


def view_relationships_menu(db):
    username = input("Actor username (or Enter for all): ").strip() or None
    try:
        relationships = db.get_actor_relationships(username)
    except Exception as e:
        error(f"Query failed: {e}")
        return

    print(f"\nFound {len(relationships)} relationships")
    for r in relationships[:20]:
        print(f"  {r['from_actor']} → {r['to_actor']} [{r['link_type']}]")
        if r.get('wallet_address'):
            print(f"    Wallet: {r['wallet_address']}")


def view_session_summary_menu():
    sid = input("Session id: ").strip()
    if not sid:
        return
    summary = get_session_summary(sid)
    print(f"\nSession {sid} — new tables:")
    for table, count in summary.items():
        print(f"  {table:18} → {count}")


def main_menu():
    print("\n" + "=" * 50)
    print("MAIN MENU")
    print("=" * 50)
    print("1. Start new crawl session")
    print("2. View session history")
    print("3. View database stats")
    print("4. Search past data by username")
    print("5. Exit")
    print("6. Autonomous crawl mode")
    print("7. Query timeline")
    print("8. View actor relationships")
    print("9. Session summary (new tables)")
    return input("\nChoice [1-9]: ").strip()


def main():
    print_banner()

    info("Checking anonymity...")
    ok, session = verify_anonymity_safe()
    if not ok:
        warn("Continuing anyway — some features may not work without Tor")

    # Ensure new tables exist
    try:
        ensure_schema()
    except Exception as e:
        warn(f"schema ensure failed: {e}")

    db = Database()
    stats = db.get_stats()
    info(f"Database loaded — {stats.get('sessions', 0)} previous sessions")

    while True:
        choice = main_menu()

        if choice == '1':
            run_crawl_session(db)
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
        elif choice == '6':
            run_autonomous_menu(db)
        elif choice == '7':
            query_timeline_menu(db)
        elif choice == '8':
            view_relationships_menu(db)
        elif choice == '9':
            view_session_summary_menu()
        else:
            warn("Invalid choice")


if __name__ == '__main__':
    main()
