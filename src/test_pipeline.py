# test_pipeline.py — End-to-end sanity check
# Runs a fake "crawl result" through the full pipeline and verifies outputs.
import os
import sys
import json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from ai_cleaner import AICleaner
from db.schema import ensure_schema
from db import queries as dbq
from reports.report_builder import produce_all_reports
from config import OUTPUT_DIR


# ── Fake raw intel output (mimics intel_extractor.full_extract) ──
FAKE_INTEL = {
    'url': 'http://example.onion/thread/42',
    'text': ('Selling mdma and cocaine. Contact @dealer_xyz at dealer@riseup.net. '
             'BTC: 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa. '
             'Also known as "The Chemist". Telegram: t.me/chemist_official'),
    'usernames': ['dealer_xyz', 'admin', 'user', 'dealer_xyz', 'The Chemist'],
    'emails': ['dealer@riseup.net'],
    'crypto_addresses': {'bitcoin': ['1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa']},
    'crypto_validated': {'1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa': True},
    'crypto_context': {'1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa':
                       'Pay to 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa for orders'},
    'posts_with_timing': [
        {
            'username': 'dealer_xyz',
            'text': 'Selling mdma and cocaine. Contact @dealer_xyz. BTC only.',
            'timestamps': ['2026-09-07 14:30 UTC'],
            'raw_html_ref': 'raw_posts/post_000.html',
        },
        {
            'username': 'dealer_xyz',
            'text': 'Fresh batch of mdma in stock. Stealth shipping worldwide.',
            'timestamps': ['2026-09-07 22:15 UTC'],
            'raw_html_ref': 'raw_posts/post_001.html',
        },
    ],
    'profiles': {
        'pgp_keys': ['-----BEGIN PGP PUBLIC KEY BLOCK-----\nFAKE\n-----END PGP PUBLIC KEY BLOCK-----'],
        'contact_methods': {'email_riseup': ['dealer@riseup.net']},
        'social_presence': {},
        'communication_channels': [{'type': 'telegram', 'value': 'chemist_official'}],
        'aliases': ['The Chemist'],
    },
    'headers': {'Server': 'Apache/2.4.41', 'X-Powered-By': 'PHP/7.4'},
    'misconfigs': {
        'found': ['Server header: Apache/2.4.41', 'Missing header: X-Frame-Options'],
        'severity': {'server_header': 'MEDIUM', 'X-Frame-Options': 'LOW'},
        'server_disclosure': {},
        'exposed_paths': [],
    },
    'server_fingerprint': {
        'server_software': 'Apache 2.4.41',
        'backend_language': 'PHP 7.4',
        'framework': '',
        'database_hints': [],
        'os_hints': [],
        'cdn': '',
    },
    'ssl_info': {'ssl_available': False},
    'service_banners': {
        80: {'host': 'example.onion', 'port': 80, 'banner': 'Apache/2.4.41',
             'service': 'HTTP', 'version': 'Apache/2.4.41', 'vulnerabilities': []},
    },
    'server_status_hits': [],
    'descriptor': {'inconsistencies': ['Server date exposed: Wed, 07 Sep 2026 14:30:00 GMT']},
    'timing_analysis': {
        'timezone_estimate': 'Likely UTC+0 to UTC+5 (Europe/South Asia)',
        'average_hour': 18.4,
        'activity_pattern': 'Day active',
    },
}


def main():
    print("=" * 60)
    print("PIPELINE TEST")
    print("=" * 60)

    session_id = 'testpipeline'

    # 1. Ensure new tables exist
    print("\n[1/5] Ensuring schema...")
    ensure_schema()
    print("      OK")

    # 2. AI Cleaner
    print("\n[2/5] Running AI cleaner...")
    cleaner = AICleaner(session_id=session_id)
    actor_rows, network_rows = cleaner.clean(FAKE_INTEL)
    print(f"      actor rows:   {len(actor_rows)}")
    print(f"      network rows: {len(network_rows)}")

    # 3. DB write
    print("\n[3/5] Writing to DB...")
    a = dbq.write_actor_rows(actor_rows)
    n = dbq.write_network_rows(network_rows)
    print(f"      wrote actor:   {a}")
    print(f"      wrote network: {n}")

    # 4. Report builder
    print("\n[4/5] Building reports (Tier 2 + 3)...")
    paths = produce_all_reports(session_id, actor_rows, network_rows)
    for k, v in paths.items():
        print(f"      {k:15} -> {v}")

    # 5. Verify files exist
    print("\n[5/5] Verifying outputs...")
    out_dir = os.path.join(OUTPUT_DIR, f'session_{session_id}')
    expected = [
        'actor_report.json',
        'network_report.json',
        'actor.json',
        'network.json',
        'actor.jsonl',
        'network.jsonl',
        'actor.csv',
        'network.csv',
    ]
    missing = []
    for f in expected:
        p = os.path.join(out_dir, f)
        if os.path.exists(p):
            size = os.path.getsize(p)
            print(f"      OK  {f:22} ({size} bytes)")
        else:
            missing.append(f)
            print(f"      MISSING  {f}")

    print("\n" + "=" * 60)
    if missing:
        print(f"FAILED — missing {len(missing)} files")
        return 1
    print("ALL TESTS PASSED")
    print("=" * 60)
    return 0


if __name__ == '__main__':
    sys.exit(main())
