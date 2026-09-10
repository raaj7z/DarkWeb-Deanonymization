# reports/actor_report.py — NEW
# Report 1 — Actor Intelligence. Sent to the OSINT engine.
import json
from datetime import datetime
from pathlib import Path
from config import OUTPUT_DIR
from logging_setup import get_logger

log = get_logger('reports.actor')


def build_actor_report(session_id, actor_rows):
    """
    Takes actor_rows from ai_cleaner (or DB) and builds a structured report.
    Splits into 'entities' and 'posts' for the OSINT engine to consume.
    """
    entities = [r for r in actor_rows if r.get('entity_type')]
    posts    = [r for r in actor_rows if 'content' in r and not r.get('entity_type')]

    # Group entities by type for easier reading
    by_type = {}
    for e in entities:
        t = e.get('entity_type', 'unknown')
        by_type.setdefault(t, []).append(e)

    # Group posts by username
    by_actor = {}
    for p in posts:
        u = p.get('username') or 'unknown'
        by_actor.setdefault(u, []).append(p)

    return {
        'report_type': 'actor_intelligence',
        'report_id': f'ACT-RPT-{session_id}',
        'session_id': session_id,
        'generated_at': datetime.utcnow().isoformat(),
        'summary': {
            'total_entities': len(entities),
            'total_posts': len(posts),
            'unique_actors': len(by_actor),
            'entity_types': {k: len(v) for k, v in by_type.items()},
        },
        'entities': entities,
        'entities_by_type': by_type,
        'posts': posts,
        'posts_by_actor': by_actor,
    }


def save_actor_report(session_id, actor_rows):
    """Writes actor_report.json under output/session_<id>/."""
    report = build_actor_report(session_id, actor_rows)
    out_dir = Path(OUTPUT_DIR) / f'session_{session_id}'
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / 'actor_report.json'
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)
    log.info(f"actor report -> {path}")
    return str(path)
