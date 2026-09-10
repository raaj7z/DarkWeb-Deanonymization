# reports/network_report.py — NEW
# Report 2 — Network Infrastructure. Kept by you (crawler-side analysis).
import json
from datetime import datetime
from pathlib import Path
from config import OUTPUT_DIR
from logging_setup import get_logger

log = get_logger('reports.network')


def build_network_report(session_id, network_rows):
    """
    Takes network_rows from ai_cleaner (or DB) and builds a structured report.
    Groups by artifact_type: tls_cert, banner, server_status, header,
                             exposed_path, descriptor_leak.
    """
    by_type = {}
    for a in network_rows:
        t = a.get('artifact_type', 'unknown')
        by_type.setdefault(t, []).append(a)

    # Count per type for quick glance
    type_counts = {k: len(v) for k, v in by_type.items()}

    return {
        'report_type': 'network_infrastructure',
        'report_id': f'NET-RPT-{session_id}',
        'session_id': session_id,
        'generated_at': datetime.utcnow().isoformat(),
        'summary': {
            'total_artifacts': len(network_rows),
            'by_type': type_counts,
        },
        'artifacts': network_rows,
        'artifacts_by_type': by_type,
    }


def save_network_report(session_id, network_rows):
    """Writes network_report.json under output/session_<id>/."""
    report = build_network_report(session_id, network_rows)
    out_dir = Path(OUTPUT_DIR) / f'session_{session_id}'
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / 'network_report.json'
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)
    log.info(f"network report -> {path}")
    return str(path)
