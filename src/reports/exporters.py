# reports/exporters.py
# CSV / JSON / JSONL exporters. Work on any list of dicts.
import csv
import json
from pathlib import Path
from config import OUTPUT_DIR
from logging_setup import get_logger

log = get_logger('reports.exporters')


def export_rows_to_csv(rows, filename, fields=None):
    """
    rows: list of dicts
    fields: optional explicit column order; if None, derived from union of keys
    """
    if not rows:
        return None
    if fields is None:
        keys = set()
        for r in rows:
            keys.update(r.keys())
        fields = sorted(keys)

    path = Path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        w.writeheader()
        for r in rows:
            flat = {}
            for k in fields:
                v = r.get(k, '')
                if isinstance(v, (list, dict)):
                    v = json.dumps(v, ensure_ascii=False)
                flat[k] = v
            w.writerow(flat)
    log.info(f"csv -> {path}")
    return str(path)


def export_rows_to_json(rows, filename):
    path = Path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(rows, f, indent=2, ensure_ascii=False, default=str)
    log.info(f"json -> {path}")
    return str(path)


def export_rows_to_jsonl(rows, filename):
    path = Path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, default=str))
            f.write('\n')
    log.info(f"jsonl -> {path}")
    return str(path)


def export_session(session_id, actor_rows, network_rows,
                   formats=('json', 'jsonl', 'csv')):
    """
    Exports both reports in all requested formats.
    Returns dict of created paths.
    """
    out_dir = Path(OUTPUT_DIR) / f'session_{session_id}'
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {}

    if 'json' in formats:
        paths['actor_json'] = export_rows_to_json(actor_rows, out_dir / 'actor.json')
        paths['network_json'] = export_rows_to_json(network_rows, out_dir / 'network.json')

    if 'jsonl' in formats:
        paths['actor_jsonl'] = export_rows_to_jsonl(actor_rows, out_dir / 'actor.jsonl')
        paths['network_jsonl'] = export_rows_to_jsonl(network_rows, out_dir / 'network.jsonl')

    if 'csv' in formats:
        paths['actor_csv'] = export_rows_to_csv(actor_rows, out_dir / 'actor.csv')
        paths['network_csv'] = export_rows_to_csv(network_rows, out_dir / 'network.csv')

    return paths
