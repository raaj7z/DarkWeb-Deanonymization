# reports/report_builder.py
# One function to produce BOTH reports + exports for a session.
from reports.actor_report import save_actor_report
from reports.network_report import save_network_report
from reports.exporters import export_session
from logging_setup import get_logger

log = get_logger('reports.builder')


def produce_all_reports(session_id, actor_rows, network_rows):
    """
    Writes:
      output/session_<id>/actor_report.json
      output/session_<id>/network_report.json
      output/session_<id>/actor.json / .jsonl / .csv
      output/session_<id>/network.json / .jsonl / .csv
    Returns dict of paths.
    """
    paths = {}
    paths['actor_report'] = save_actor_report(session_id, actor_rows)
    paths['network_report'] = save_network_report(session_id, network_rows)
    paths.update(export_session(session_id, actor_rows, network_rows))
    log.info(f"all reports written for session {session_id}")
    return paths
