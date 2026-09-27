import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from config import DATA_DIR
from database import Database
from db.schema import ensure_schema
from service import (
    check_tor,
    get_session_summary,
    run_crawl,
    run_autonomous,
    write_session_reports,
)
from utils import error, info, print_banner, success, warn


def validate_onion_url(value):
    """Accept only explicit HTTP(S) v3 onion URLs."""
    value = (value or "").strip()
    if not value:
        raise ValueError("URL is empty.")

    if "://" not in value:
        value = "http://" + value

    try:
        parsed = urlsplit(value)
        hostname = (parsed.hostname or "").lower()
        port = parsed.port
    except ValueError as exc:
        raise ValueError(f"Invalid URL: {exc}") from exc

    if parsed.scheme.lower() not in ("http", "https"):
        raise ValueError("Only http:// or https:// URLs are accepted.")

    if parsed.username or parsed.password:
        raise ValueError("URLs must not contain embedded credentials.")

    if not re.fullmatch(r"[a-z2-7]{56}\.onion", hostname):
        raise ValueError(
            "Enter a valid v3 onion hostname (56 base32 characters + .onion)."
        )

    if port is not None and not (1 <= port <= 65535):
        raise ValueError("Port must be between 1 and 65535.")

    path = parsed.path or "/"
    return urlunsplit(
        (parsed.scheme.lower(), parsed.netloc.lower(), path, parsed.query, "")
    )


def get_urls_from_user():
    print("\n" + "=" * 54)
    print("TARGET INPUT")
    print("=" * 54)
    print("1. Enter authorized v3 onion URL(s)")
    print(f"2. Load authorized URL(s) from {DATA_DIR / 'urls.txt'}")

    choice = input("Choice [1/2]: ").strip()
    raw_urls = []

    if choice == "1":
        print("Paste one URL per line. Submit an empty line to finish.")
        while True:
            value = input("URL: ").strip()
            if not value:
                break
            raw_urls.append(value)

    elif choice == "2":
        url_file = DATA_DIR / "urls.txt"
        if not url_file.is_file():
            error(f"URL list not found: {url_file}")
            return []

        raw_urls = [
            line.strip()
            for line in url_file.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]

    else:
        error("Invalid choice. No targets loaded.")
        return []

    valid_urls = []
    seen = set()

    for raw in raw_urls:
        try:
            url = validate_onion_url(raw)
        except ValueError as exc:
            warn(f"Skipped input: {exc}")
            continue

        if url not in seen:
            seen.add(url)
            valid_urls.append(url)

    info(f"Validated {len(valid_urls)} unique target URL(s).")
    return valid_urls


def show_history(db):
    sessions = db.get_all_sessions()
    if not sessions:
        warn("No previous sessions found.")
        return

    print("\nRecent crawl sessions:")
    for session in sessions[:15]:
        print(
            f"- {session['session_id']} | "
            f"target={session['target_username'] or 'not specified'} | "
            f"status={session['status']} | "
            f"started={session['started_at']}"
        )


def show_database_stats(db):
    print("\nDatabase statistics:")
    for table, count in db.get_stats().items():
        print(f"  {table}: {count}")


def search_past_data(db):
    username = input("Username/handle to search: ").strip()
    if not username:
        return

    posts = db.get_posts_by_username(username)
    print(f"\nSaved posts for {username}: {len(posts)}")
    for post in posts[:10]:
        print(f"\nTime: {post['extracted_at']}")
        print(f"Source: {post['source_url']}")
        print(f"Text: {post['content'][:300]}")


def query_timeline(db):
    start_date = input("Start date (YYYY-MM-DD): ").strip()
    end_date = input("End date (YYYY-MM-DD): ").strip()

    try:
        results = db.query_timeline(start_date, end_date)
    except Exception as exc:
        error(f"Timeline query failed: {exc}")
        return

    print(f"\nTimeline records found: {len(results)}")
    for row in results[:30]:
        print(
            f"{row['crawled_at']} | {row['url']} | "
            f"page-level indicators={row['descriptor_issues']} | "
            f"recorded links={row['trust_links_found']}"
        )


def show_relationships(db):
    handle = input("Handle filter (Enter for all): ").strip() or None
    try:
        rows = db.get_actor_relationships(handle)
    except Exception as exc:
        error(f"Relationship query failed: {exc}")
        return

    print(f"\nSaved relationship records: {len(rows)}")
    for row in rows[:30]:
        print(
            f"{row['from_actor'] or '—'} -> {row['to_actor'] or '—'} "
            f"[{row['link_type']}] | source={row['source_url']}"
        )


def show_session_summary(db):
    session_id = input("Session ID: ").strip()
    if not session_id:
        return

    try:
        summary = get_session_summary(session_id, db=db)
    except Exception as exc:
        error(f"Could not read session summary: {exc}")
        return

    print(f"\nSession {session_id}")
    for table, count in summary.items():
        print(f"  {table}: {count}")


def run_crawl_session(db):
    urls = get_urls_from_user()
    if not urls:
        warn("No valid targets; crawl not started.")
        return

    print(
        "\nConfirm that these are approved targets and that you are "
        "authorized to collect their publicly accessible pages."
    )
    confirmation = input("Type YES to continue: ").strip()
    if confirmation != "YES":
        warn("Confirmation not provided; crawl cancelled.")
        return

    try:
        workers = int(input("Workers [1-3, default 2]: ").strip() or "2")
    except ValueError:
        workers = 2
    workers = max(1, min(3, workers))

    info("Starting crawler service...")
    bundle = run_crawl(
        urls=urls,
        workers=workers,
        use_js=False,
        rotate_circuits=False,
        db=db,
    )

    session_id = bundle.get("session_id")
    summary = bundle.get("summary") or {}

    if bundle.get("status") == "ERROR" or bundle.get("error"):
        error(f"Crawl failed: {bundle.get('error', 'Unknown error')}")
        return

    print(f"\nCrawl run: {session_id}")
    print(f"Status: {bundle.get('status', 'UNKNOWN')}")
    print(f"URLs submitted: {summary.get('urls_crawled', 0)}")
    print(f"URLs successful: {summary.get('urls_ok', 0)}")
    print(f"Actor records: {summary.get('actor_rows', 0)}")
    print(f"Network records: {summary.get('network_rows', 0)}")

    try:
        report_paths = write_session_reports(
            session_id,
            bundle.get("actor_rows", []),
            bundle.get("network_rows", []),
        )
        success(f"Focused reports created: {len(report_paths)}")
    except Exception as exc:
        warn(f"Focused report generation failed: {exc}")

    try:
        from report_generator import ReportGenerator

        report_path = ReportGenerator(db).save_json(session_id)
        if report_path:
            success(f"Full JSON snapshot: {report_path}")
        else:
            warn("Full JSON snapshot was not created.")
    except Exception as exc:
        warn(f"Full report generation failed: {exc}")


def run_autonomous_mode(db):
    urls = get_urls_from_user()
    if not urls:
        warn("No valid targets; scheduled run not started.")
        return

    confirmation = input(
        "Confirm these targets are approved for recurring collection "
        "(type YES): "
    ).strip()
    if confirmation != "YES":
        warn("Confirmation not provided; recurring run cancelled.")
        return

    try:
        hours = float(input("Run duration in hours [default 1]: ").strip() or "1")
        interval = int(
            input("Interval in minutes [default 30]: ").strip() or "30"
        )
    except ValueError:
        error("Duration and interval must be numeric.")
        return

    if not (0 < hours <= 24 * 7):
        error("Duration must be greater than 0 and no more than 7 days.")
        return
    if not (1 <= interval <= 1440):
        error("Interval must be between 1 minute and 24 hours.")
        return

    result = run_autonomous(
        urls=urls,
        hours=hours,
        interval_minutes=interval,
        workers=1,
        db=db,
    )
    print(json.dumps(result, indent=2, default=str))


def main_menu():
    print("\n" + "=" * 54)
    print("PRALAYX CRAWLER · CONTROL MENU")
    print("=" * 54)
    print("1. Start authorized crawl")
    print("2. View session history")
    print("3. View database statistics")
    print("4. Search saved posts by handle")
    print("5. Query crawl timeline")
    print("6. View saved relationship records")
    print("7. View normalized-table counts")
    print("8. Autonomous crawl (approved target list)")
    print("9. Exit")
    return input("Select [1-9]: ").strip()


def main():
    print_banner()

    db = Database()
    try:
        ensure_schema(db.conn)

        ok, message = check_tor()
        if not ok:
            error(f"Tor check failed: {message}")
            error("Crawler stopped; verify the local Tor SOCKS proxy, then retry.")
            return

        success("Tor proxy verification passed.")

        while True:
            choice = main_menu()
            if choice == "1":
                run_crawl_session(db)
            elif choice == "2":
                show_history(db)
            elif choice == "3":
                show_database_stats(db)
            elif choice == "4":
                search_past_data(db)
            elif choice == "5":
                query_timeline(db)
            elif choice == "6":
                show_relationships(db)
            elif choice == "7":
                show_session_summary(db)
            elif choice == "8":
                run_autonomous_mode(db)
            elif choice == "9":
                success("Closing crawler.")
                break
            else:
                warn("Invalid choice.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
