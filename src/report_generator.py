# report_generator.py — Complete Intelligence Report
# Covers ALL database tables
# Generates PDF + JSON + HTML reports

import json
import os
from datetime import datetime
from database import Database
from utils import success, error, info, warn

class ReportGenerator:

    def __init__(self, db=None):
        self.db = db or Database()
        os.makedirs('reports', exist_ok=True)

    # ── FETCH ALL DATA FROM ALL TABLES ──

    def _get_session_data(self, session_id):
        """Get complete session info"""
        cursor = self.db.conn.cursor()
        cursor.execute(
            'SELECT * FROM sessions WHERE session_id=?',
            (session_id,)
        )
        return cursor.fetchone()

    def _get_search_history(self, session_id):
        cursor = self.db.conn.cursor()
        cursor.execute(
            'SELECT * FROM search_history WHERE session_id=? ORDER BY searched_at',
            (session_id,)
        )
        return cursor.fetchall()

    def _get_sites(self, session_id):
        cursor = self.db.conn.cursor()
        cursor.execute('''
            SELECT DISTINCT sc.url, s.title, s.alive, s.server,
                   s.status_code, sc.response_time_ms, sc.checked_at
            FROM site_checks sc
            LEFT JOIN sites s ON sc.url = s.url
            WHERE sc.session_id=?
            ORDER BY sc.checked_at
        ''', (session_id,))
        return cursor.fetchall()

    def _get_usernames(self, session_id):
        cursor = self.db.conn.cursor()
        cursor.execute('''
            SELECT username, source_url, pattern_matched,
                   COUNT(*) as occurrences, MIN(found_at) as first_seen
            FROM usernames
            WHERE session_id=?
            GROUP BY username
            ORDER BY occurrences DESC
        ''', (session_id,))
        return cursor.fetchall()

    def _get_posts(self, session_id):
        cursor = self.db.conn.cursor()
        cursor.execute('''
            SELECT username, content, word_count,
                   timestamp_found, source_url, extracted_at
            FROM posts
            WHERE session_id=?
            ORDER BY extracted_at DESC
            LIMIT 100
        ''', (session_id,))
        return cursor.fetchall()

    def _get_timed_posts(self, session_id):
        cursor = self.db.conn.cursor()
        cursor.execute('''
            SELECT username, content, word_count, timestamps,
                   hour_of_day, timezone_estimate, has_crypto,
                   has_links, source_url, extracted_at
            FROM timed_posts
            WHERE session_id=?
            ORDER BY extracted_at DESC
            LIMIT 50
        ''', (session_id,))
        return cursor.fetchall()

    def _get_timing_analysis(self, session_id):
        cursor = self.db.conn.cursor()
        cursor.execute('''
            SELECT target_username, peak_hours, average_hour,
                   timezone_estimate, activity_pattern, total_posts
            FROM timing_analysis
            WHERE session_id=?
        ''', (session_id,))
        return cursor.fetchall()

    def _get_crypto(self, session_id):
        cursor = self.db.conn.cursor()
        cursor.execute('''
            SELECT currency, address, context, source_url, found_at
            FROM crypto_addresses
            WHERE session_id=?
            ORDER BY currency, found_at
        ''', (session_id,))
        return cursor.fetchall()

    def _get_misconfigs(self, session_id):
        cursor = self.db.conn.cursor()
        cursor.execute('''
            SELECT url, misconfig_type, severity, detail, found_at
            FROM misconfigs
            WHERE session_id=?
            ORDER BY severity DESC, found_at
        ''', (session_id,))
        return cursor.fetchall()

    def _get_server_fingerprints(self, session_id):
        cursor = self.db.conn.cursor()
        cursor.execute('''
            SELECT url, server_software, backend_language,
                   framework, database_hints, os_hints, cdn, found_at
            FROM server_fingerprints
            WHERE session_id=?
        ''', (session_id,))
        return cursor.fetchall()

    def _get_profiles(self, session_id):
        cursor = self.db.conn.cursor()
        cursor.execute('''
            SELECT source_url, pgp_keys, contact_methods,
                   communication_channels, aliases, found_at
            FROM profiles
            WHERE session_id=?
        ''', (session_id,))
        return cursor.fetchall()

    def _get_trust_links(self, session_id):
        cursor = self.db.conn.cursor()
        cursor.execute('''
            SELECT source_url, from_actor, to_actor,
                   link_type, wallet_address, trust_score, found_at
            FROM trust_links
            WHERE session_id=?
            ORDER BY link_type, found_at
        ''', (session_id,))
        return cursor.fetchall()

    def _get_links(self, session_id):
        cursor = self.db.conn.cursor()
        cursor.execute('''
            SELECT source_url, target_url, link_type, found_at
            FROM links
            WHERE session_id=?
            ORDER BY link_type
        ''', (session_id,))
        return cursor.fetchall()

    def _get_descriptor_checks(self, session_id):
        cursor = self.db.conn.cursor()
        cursor.execute('''
            SELECT onion_address, reachable, inconsistencies,
                   clearnet_refs, exposed_ips, metadata, checked_at
            FROM descriptor_checks
            WHERE session_id=?
        ''', (session_id,))
        return cursor.fetchall()

    def _get_timeline(self, session_id):
        cursor = self.db.conn.cursor()
        cursor.execute('''
            SELECT url, crawled_at, date, hour, day_of_week,
                   week_number, descriptor_issues, trust_links_found
            FROM timeline_crawls
            WHERE session_id=?
            ORDER BY crawled_at
        ''', (session_id,))
        return cursor.fetchall()

    def _get_behavioral_fingerprints(self, session_id):
        cursor = self.db.conn.cursor()
        try:
            cursor.execute('''
                SELECT username, platform, post_count,
                       avg_sentence_length, vocabulary_richness,
                       technical_level, timezone_estimate,
                       activity_pattern, slang_words_found,
                       peak_hours, writing_sample, created_at
                FROM behavioral_fingerprints
                WHERE session_id=?
            ''', (session_id,))
            return cursor.fetchall()
        except:
            return []

    def _get_persona_comparisons(self, session_id):
        cursor = self.db.conn.cursor()
        try:
            cursor.execute('''
                SELECT username_a, username_b, platform_a, platform_b,
                       similarity_score, confidence_level,
                       is_same_person, evidence, compared_at
                FROM persona_comparisons
                WHERE session_id=?
                ORDER BY similarity_score DESC
            ''', (session_id,))
            return cursor.fetchall()
        except:
            return []

    def _get_persona_clusters(self, session_id):
        cursor = self.db.conn.cursor()
        try:
            cursor.execute('''
                SELECT cluster_id, usernames, platforms,
                       avg_similarity, primary_username,
                       evidence_summary, created_at
                FROM persona_clusters
                WHERE session_id=?
            ''', (session_id,))
            return cursor.fetchall()
        except:
            return []

    # ── BUILD COMPLETE REPORT DICT ──

    def build_report(self, session_id):
        """
        Builds complete report dict from ALL database tables
        Returns dict ready for JSON/PDF/HTML export
        """
        info(f"Building complete report for session: {session_id}")

        session   = self._get_session_data(session_id)
        if not session:
            error(f"Session not found: {session_id}")
            return None

        # Fetch everything
        sites        = self._get_sites(session_id)
        usernames    = self._get_usernames(session_id)
        posts        = self._get_posts(session_id)
        timed_posts  = self._get_timed_posts(session_id)
        timing       = self._get_timing_analysis(session_id)
        crypto       = self._get_crypto(session_id)
        misconfigs   = self._get_misconfigs(session_id)
        fingerprints = self._get_server_fingerprints(session_id)
        profiles     = self._get_profiles(session_id)
        trust        = self._get_trust_links(session_id)
        links        = self._get_links(session_id)
        descriptors  = self._get_descriptor_checks(session_id)
        timeline     = self._get_timeline(session_id)
        behavior     = self._get_behavioral_fingerprints(session_id)
        comparisons  = self._get_persona_comparisons(session_id)
        clusters     = self._get_persona_clusters(session_id)
        history      = self._get_search_history(session_id)

        # Group crypto by currency
        crypto_grouped = {}
        for row in crypto:
            curr = row['currency']
            if curr not in crypto_grouped:
                crypto_grouped[curr] = []
            crypto_grouped[curr].append({
                'address': row['address'],
                'context': row['context'],
                'source':  row['source_url'],
                'found':   row['found_at'],
            })

        # Group misconfigs by severity
        misconfigs_grouped = {'CRITICAL': [], 'HIGH': [], 'MEDIUM': [], 'LOW': []}
        for row in misconfigs:
            sev = row['severity'] if row['severity'] in misconfigs_grouped else 'LOW'
            misconfigs_grouped[sev].append({
                'url':    row['url'],
                'type':   row['misconfig_type'],
                'detail': row['detail'],
                'found':  row['found_at'],
            })

        # Group links by type
        links_grouped = {'onion': [], 'surface': [], 'relative': []}
        for row in links:
            lt = row['link_type'] if row['link_type'] in links_grouped else 'onion'
            links_grouped[lt].append({
                'source': row['source_url'],
                'target': row['target_url'],
                'found':  row['found_at'],
            })

        # Build complete report
        report = {
            # ── HEADER ──
            'report_id':      f"RPT-{session_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            'generated_at':   datetime.utcnow().isoformat(),
            'session_id':     session_id,
            'problem_stmt':   'SIH26151 — NTRO Dark Web Threat Actor De-anonymization',
            'team':           'IIT Patna',

            # ── SESSION ──
            'session': {
                'target_username': session['target_username'],
                'started_at':      session['started_at'],
                'completed_at':    session['completed_at'],
                'status':          session['status'],
                'urls_crawled':    json.loads(session['urls_crawled'] or '[]'),
                'summary':         json.loads(session['summary'] or '{}'),
            },

            # ── SITES ──
            'sites': {
                'total':    len(sites),
                'alive':    sum(1 for s in sites if s['alive']),
                'dead':     sum(1 for s in sites if not s['alive']),
                'details':  [dict(s) for s in sites],
            },

            # ── USERNAMES ──
            'usernames': {
                'total_unique': len(usernames),
                'details': [{
                    'username':    row['username'],
                    'occurrences': row['occurrences'],
                    'source_url':  row['source_url'],
                    'pattern':     row['pattern_matched'],
                    'first_seen':  row['first_seen'],
                } for row in usernames],
            },

            # ── POSTS ──
            'posts': {
                'total': len(posts),
                'details': [{
                    'username':   row['username'],
                    'content':    row['content'][:500],
                    'word_count': row['word_count'],
                    'timestamp':  row['timestamp_found'],
                    'source':     row['source_url'],
                } for row in posts],
            },

            # ── TIMED POSTS ──
            'timed_posts': {
                'total': len(timed_posts),
                'details': [{
                    'username':          row['username'],
                    'content':           row['content'][:300],
                    'word_count':        row['word_count'],
                    'timestamps':        json.loads(row['timestamps'] or '[]'),
                    'hour_of_day':       row['hour_of_day'],
                    'timezone_estimate': row['timezone_estimate'],
                    'has_crypto':        bool(row['has_crypto']),
                    'has_links':         bool(row['has_links']),
                    'source':            row['source_url'],
                } for row in timed_posts],
            },

            # ── TIMING ANALYSIS ──
            'timing_analysis': [{
                'target':           row['target_username'],
                'peak_hours':       json.loads(row['peak_hours'] or '[]'),
                'average_hour':     row['average_hour'],
                'timezone':         row['timezone_estimate'],
                'activity_pattern': row['activity_pattern'],
                'total_posts':      row['total_posts'],
            } for row in timing],

            # ── CRYPTO ADDRESSES ──
            'crypto_addresses': {
                'total_found': sum(len(v) for v in crypto_grouped.values()),
                'by_currency': crypto_grouped,
                'currencies_found': list(crypto_grouped.keys()),
            },

            # ── MISCONFIGURATIONS ──
            'misconfigurations': {
                'total':      len(misconfigs),
                'critical':   len(misconfigs_grouped['CRITICAL']),
                'high':       len(misconfigs_grouped['HIGH']),
                'medium':     len(misconfigs_grouped['MEDIUM']),
                'low':        len(misconfigs_grouped['LOW']),
                'by_severity': misconfigs_grouped,
            },

            # ── SERVER FINGERPRINTS ──
            'server_fingerprints': [{
                'url':       row['url'],
                'server':    row['server_software'],
                'language':  row['backend_language'],
                'framework': row['framework'],
                'databases': json.loads(row['database_hints'] or '[]'),
                'os':        json.loads(row['os_hints'] or '[]'),
                'cdn':       row['cdn'],
                'found':     row['found_at'],
            } for row in fingerprints],

            # ── PROFILES ──
            'profiles': [{
                'source_url':   row['source_url'],
                'pgp_keys':     json.loads(row['pgp_keys'] or '[]'),
                'contacts':     json.loads(row['contact_methods'] or '{}'),
                'channels':     json.loads(row['communication_channels'] or '[]'),
                'aliases':      json.loads(row['aliases'] or '[]'),
                'found':        row['found_at'],
            } for row in profiles],

            # ── TRUST LINKS ──
            'trust_links': {
                'total':    len(trust),
                'details': [{
                    'from':         row['from_actor'],
                    'to':           row['to_actor'],
                    'type':         row['link_type'],
                    'wallet':       row['wallet_address'],
                    'trust_score':  row['trust_score'],
                    'source':       row['source_url'],
                    'found':        row['found_at'],
                } for row in trust],
            },

            # ── LINKS ──
            'links': {
                'onion_count':   len(links_grouped['onion']),
                'surface_count': len(links_grouped['surface']),
                'by_type':       links_grouped,
            },

            # ── HIDDEN SERVICE METADATA ──
            'hidden_service_metadata': [{
                'address':    row['onion_address'],
                'reachable':  bool(row['reachable']),
                'indicators': json.loads(row['inconsistencies'] or '[]'),
                'clearnet':   json.loads(row['clearnet_refs'] or '[]'),
                'exposed_ips':json.loads(row['exposed_ips'] or '[]'),
                'checked':    row['checked_at'],
            } for row in descriptors],

            # ── TIMELINE ──
            'timeline': [{
                'url':         row['url'],
                'crawled_at':  row['crawled_at'],
                'date':        row['date'],
                'hour':        row['hour'],
                'day_of_week': row['day_of_week'],
                'week':        row['week_number'],
                'desc_issues': row['descriptor_issues'],
                'trust_found': row['trust_links_found'],
            } for row in timeline],

            # ── BEHAVIORAL ANALYSIS ──
            'behavioral_fingerprints': [{
                'username':          row['username'],
                'platform':          row['platform'],
                'post_count':        row['post_count'],
                'avg_sentence_len':  row['avg_sentence_length'],
                'vocab_richness':    row['vocabulary_richness'],
                'technical_level':   row['technical_level'],
                'timezone':          row['timezone_estimate'],
                'activity_pattern':  row['activity_pattern'],
                'slang':             json.loads(row['slang_words_found'] or '[]'),
                'peak_hours':        json.loads(row['peak_hours'] or '[]'),
                'writing_sample':    row['writing_sample'],
                'analyzed':          row['created_at'],
            } for row in behavior],

            # ── PERSONA COMPARISONS ──
            'persona_comparisons': [{
                'username_a':   row['username_a'],
                'username_b':   row['username_b'],
                'platform_a':   row['platform_a'],
                'platform_b':   row['platform_b'],
                'similarity':   row['similarity_score'],
                'confidence':   row['confidence_level'],
                'same_person':  bool(row['is_same_person']),
                'evidence':     json.loads(row['evidence'] or '[]'),
                'compared':     row['compared_at'],
            } for row in comparisons],

            # ── PERSONA CLUSTERS ──
            'persona_clusters': [{
                'cluster_id':      row['cluster_id'],
                'usernames':       json.loads(row['usernames'] or '[]'),
                'platforms':       json.loads(row['platforms'] or '[]'),
                'avg_similarity':  row['avg_similarity'],
                'primary':         row['primary_username'],
                'summary':         row['evidence_summary'],
                'created':         row['created_at'],
            } for row in clusters],

            # ── SEARCH HISTORY ──
            'search_history': [{
                'type':    row['query_type'],
                'query':   row['query_value'],
                'results': row['results_count'],
                'time':    row['searched_at'],
            } for row in history],

            # ── STATISTICS SUMMARY ──
            'statistics': {
                'sites_crawled':         len(sites),
                'unique_usernames':      len(usernames),
                'posts_found':           len(posts),
                'crypto_wallets':        sum(len(v) for v in crypto_grouped.values()),
                'crypto_currencies':     len(crypto_grouped),
                'misconfigs_found':      len(misconfigs),
                'critical_misconfigs':   len(misconfigs_grouped['CRITICAL']),
                'profiles_found':        len(profiles),
                'trust_relationships':   len(trust),
                'onion_links_found':     len(links_grouped['onion']),
                'surface_links_found':   len(links_grouped['surface']),
                'personas_compared':     len(comparisons),
                'same_person_matches':   sum(1 for r in comparisons if r['is_same_person']),
                'clusters_found':        len(clusters),
                'behavioral_profiles':   len(behavior),
            }
        }

        success(f"Report built — {len(report)} sections")
        return report

    # ── EXPORT METHODS ──

    def save_json(self, session_id):
        """Save complete report as JSON"""
        report = self.build_report(session_id)
        if not report:
            return None

        filename = f"reports/report_{session_id}.json"
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        success(f"JSON report: {filename}")
        return filename

    def save_pdf(self, session_id):
        """Save complete report as PDF"""
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.platypus import (
                SimpleDocTemplate, Paragraph, Spacer,
                Table, TableStyle, PageBreak
            )
            from reportlab.lib import colors
            from reportlab.lib.units import mm
        except ImportError:
            error("reportlab not installed: pip3 install reportlab")
            return None

        report = self.build_report(session_id)
        if not report:
            return None

        filename = f"reports/report_{session_id}.pdf"
        doc = SimpleDocTemplate(filename, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []

        def h1(text):
            return Paragraph(f"<b>{text}</b>", styles['Title'])

        def h2(text):
            return Paragraph(f"<b>{text}</b>", styles['Heading2'])

        def h3(text):
            return Paragraph(f"<b>{text}</b>", styles['Heading3'])

        def p(text):
            return Paragraph(str(text)[:500], styles['Normal'])

        def spacer():
            return Spacer(1, 5*mm)

        def make_table(data, col_widths=None):
            t = Table(data, colWidths=col_widths)
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.darkblue),
                ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
                ('FONTSIZE',   (0,0), (-1,0), 8),
                ('FONTSIZE',   (0,1), (-1,-1), 7),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.lightgrey]),
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ]))
            return t

        # ── COVER PAGE ──
        story.append(h1("INTELLIGENCE REPORT"))
        story.append(p(f"Problem Statement: {report['problem_stmt']}"))
        story.append(p(f"Report ID: {report['report_id']}"))
        story.append(p(f"Generated: {report['generated_at']}"))
        story.append(p(f"Session: {report['session_id']}"))
        story.append(p(f"Team: {report['team']}"))
        story.append(spacer())

        # Session info
        sess = report['session']
        story.append(h2("Session Information"))
        story.append(p(f"Target: {sess['target_username'] or 'All usernames'}"))
        story.append(p(f"Started: {sess['started_at']}"))
        story.append(p(f"Status: {sess['status']}"))
        story.append(spacer())

        # ── STATISTICS SUMMARY ──
        story.append(PageBreak())
        story.append(h2("Executive Summary"))
        stats = report['statistics']
        summary_data = [['Metric', 'Count']] + [
            [k.replace('_', ' ').title(), str(v)]
            for k, v in stats.items()
        ]
        story.append(make_table(summary_data, [100*mm, 50*mm]))
        story.append(spacer())

        # ── SITES ──
        story.append(PageBreak())
        story.append(h2("Sites Crawled"))
        story.append(p(f"Total: {report['sites']['total']} | "
                       f"Alive: {report['sites']['alive']} | "
                       f"Dead: {report['sites']['dead']}"))
        if report['sites']['details']:
            site_data = [['URL', 'Title', 'Status', 'Server', 'Response(ms)']]
            for s in report['sites']['details'][:20]:
                site_data.append([
                    str(s.get('url',''))[:40],
                    str(s.get('title',''))[:30],
                    str(s.get('status_code','')),
                    str(s.get('server',''))[:20],
                    str(s.get('response_time_ms','')),
                ])
            story.append(make_table(site_data))
        story.append(spacer())

        # ── USERNAMES ──
        story.append(PageBreak())
        story.append(h2("Usernames Discovered"))
        story.append(p(f"Unique usernames: {report['usernames']['total_unique']}"))
        if report['usernames']['details']:
            un_data = [['Username', 'Occurrences', 'Pattern', 'First Seen']]
            for u in report['usernames']['details'][:30]:
                un_data.append([
                    u['username'][:25],
                    str(u['occurrences']),
                    u.get('pattern','')[:20],
                    str(u.get('first_seen',''))[:16],
                ])
            story.append(make_table(un_data))
        story.append(spacer())

        # ── CRYPTO ADDRESSES ──
        story.append(PageBreak())
        story.append(h2("Cryptocurrency Addresses"))
        story.append(p(f"Total wallets: {report['crypto_addresses']['total_found']}"))
        story.append(p(f"Currencies: {', '.join(report['crypto_addresses']['currencies_found'])}"))
        for currency, addresses in report['crypto_addresses']['by_currency'].items():
            story.append(h3(f"{currency.upper()} ({len(addresses)} addresses)"))
            crypto_data = [['Address', 'Source URL', 'Found']]
            for addr in addresses[:10]:
                crypto_data.append([
                    addr['address'][:40],
                    addr['source'][:35],
                    str(addr['found'])[:16],
                ])
            story.append(make_table(crypto_data))
            story.append(spacer())

        # ── MISCONFIGURATIONS ──
        story.append(PageBreak())
        story.append(h2("Misconfigurations Found"))
        story.append(p(f"Total: {report['misconfigurations']['total']} | "
                       f"Critical: {report['misconfigurations']['critical']} | "
                       f"High: {report['misconfigurations']['high']}"))
        for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
            items = report['misconfigurations']['by_severity'][severity]
            if items:
                story.append(h3(f"{severity} ({len(items)})"))
                mc_data = [['URL', 'Type', 'Detail']]
                for m in items[:15]:
                    mc_data.append([
                        m['url'][:30],
                        m['type'][:25],
                        m['detail'][:40],
                    ])
                story.append(make_table(mc_data))
                story.append(spacer())

        # ── SERVER FINGERPRINTS ──
        story.append(PageBreak())
        story.append(h2("Server Fingerprints"))
        if report['server_fingerprints']:
            fp_data = [['URL', 'Server', 'Language', 'Framework', 'CDN']]
            for fp in report['server_fingerprints']:
                fp_data.append([
                    fp['url'][:30],
                    fp['server'][:15],
                    fp['language'][:15],
                    fp['framework'][:15],
                    fp['cdn'][:10],
                ])
            story.append(make_table(fp_data))
        story.append(spacer())

        # ── PROFILES ──
        story.append(PageBreak())
        story.append(h2("Threat Actor Profiles"))
        for prof in report['profiles'][:10]:
            story.append(h3(f"Source: {prof['source_url'][:50]}"))
            if prof['pgp_keys']:
                story.append(p(f"PGP Keys: {len(prof['pgp_keys'])} found"))
            if prof['contacts']:
                for contact_type, contacts in prof['contacts'].items():
                    story.append(p(f"{contact_type}: {contacts}"))
            if prof['channels']:
                for ch in prof['channels']:
                    story.append(p(f"Channel: {ch.get('type','')}: {ch.get('value','')}"))
            if prof['aliases']:
                story.append(p(f"Aliases: {', '.join(prof['aliases'])}"))
            story.append(spacer())

        # ── TRUST LINKS ──
        story.append(PageBreak())
        story.append(h2("Trust Links & Relationships"))
        story.append(p(f"Total relationships: {report['trust_links']['total']}"))
        if report['trust_links']['details']:
            tl_data = [['From', 'To', 'Type', 'Wallet', 'Score']]
            for tl in report['trust_links']['details'][:20]:
                tl_data.append([
                    str(tl['from'] or '')[:20],
                    str(tl['to'] or '')[:20],
                    str(tl['type'])[:15],
                    str(tl['wallet'] or '')[:20],
                    str(tl['trust_score'] or ''),
                ])
            story.append(make_table(tl_data))
        story.append(spacer())

        # ── TIMING ANALYSIS ──
        story.append(PageBreak())
        story.append(h2("Timing & Timezone Analysis"))
        for ta in report['timing_analysis']:
            story.append(h3(f"Target: {ta['target']}"))
            story.append(p(f"Posts analyzed: {ta['total_posts']}"))
            story.append(p(f"Average posting hour: {ta['average_hour']} (0-23)"))
            story.append(p(f"Peak hours: {ta['peak_hours']}"))
            story.append(p(f"Timezone estimate: {ta['timezone']}"))
            story.append(p(f"Activity pattern: {ta['activity_pattern']}"))
            story.append(spacer())

        # ── BEHAVIORAL FINGERPRINTS ──
        story.append(PageBreak())
        story.append(h2("Behavioral Fingerprints"))
        for bf in report['behavioral_fingerprints']:
            story.append(h3(f"Username: {bf['username']} ({bf['platform']})"))
            story.append(p(f"Posts analyzed: {bf['post_count']}"))
            story.append(p(f"Avg sentence length: {bf['avg_sentence_len']} words"))
            story.append(p(f"Vocabulary richness: {bf['vocab_richness']}"))
            story.append(p(f"Technical level: {bf['technical_level']}"))
            story.append(p(f"Timezone: {bf['timezone']}"))
            story.append(p(f"Activity: {bf['activity_pattern']}"))
            story.append(p(f"Slang used: {bf['slang']}"))
            story.append(p(f"Writing sample: {bf['writing_sample'][:200]}..."))
            story.append(spacer())

        # ── PERSONA COMPARISONS ──
        story.append(PageBreak())
        story.append(h2("Persona Comparisons"))
        if report['persona_comparisons']:
            pc_data = [['Username A', 'Username B', 'Similarity', 'Confidence', 'Same Person']]
            for pc in report['persona_comparisons']:
                pc_data.append([
                    pc['username_a'][:20],
                    pc['username_b'][:20],
                    f"{pc['similarity']}%",
                    pc['confidence'],
                    'YES' if pc['same_person'] else 'NO',
                ])
            story.append(make_table(pc_data))
            story.append(spacer())

            # Evidence for top matches
            story.append(h3("Evidence for High Confidence Matches"))
            for pc in report['persona_comparisons']:
                if pc['confidence'] in ['HIGH', 'VERY_HIGH']:
                    story.append(p(f"{pc['username_a']} = {pc['username_b']} "
                                   f"({pc['similarity']}% — {pc['confidence']})"))
                    for ev in pc['evidence'][:5]:
                        story.append(p(f"  → {ev}"))
                    story.append(spacer())

        # ── PERSONA CLUSTERS ──
        story.append(PageBreak())
        story.append(h2("Persona Clusters"))
        for cluster in report['persona_clusters']:
            story.append(h3(f"Cluster: {cluster['cluster_id']}"))
            story.append(p(f"Primary actor: {cluster['primary']}"))
            story.append(p(f"Usernames: {', '.join(cluster['usernames'])}"))
            story.append(p(f"Avg similarity: {cluster['avg_similarity']}%"))
            story.append(p(f"Summary: {cluster['summary']}"))
            story.append(spacer())

        # ── HIDDEN SERVICE METADATA ──
        story.append(PageBreak())
        story.append(h2("Hidden Service Metadata"))
        for desc in report['hidden_service_metadata'][:10]:
            story.append(h3(f"{desc['address'][:50]}"))
            story.append(p(f"Reachable: {desc['reachable']}"))
            if desc['indicators']:
                for ind in desc['indicators']:
                    story.append(p(f"  ⚠ {ind}"))
            if desc['clearnet']:
                story.append(p(f"Clearnet refs: {desc['clearnet']}"))
            if desc['exposed_ips']:
                story.append(p(f"Exposed IPs: {desc['exposed_ips']}"))
            story.append(spacer())

        # ── TIMELINE ──
        story.append(PageBreak())
        story.append(h2("Crawl Timeline"))
        if report['timeline']:
            tl_data = [['URL', 'Date', 'Hour', 'Day', 'Desc Issues', 'Trust Found']]
            for tl in report['timeline']:
                tl_data.append([
                    tl['url'][:30],
                    tl['date'],
                    str(tl['hour']),
                    tl['day_of_week'][:3],
                    str(tl['desc_issues']),
                    str(tl['trust_found']),
                ])
            story.append(make_table(tl_data))

        # Build PDF
        doc.build(story)
        success(f"PDF report: {filename}")
        return filename

    def save_html(self, session_id):
        """Save complete report as HTML"""
        report = self.build_report(session_id)
        if not report:
            return None

        stats = report['statistics']

        html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Intelligence Report — {report['report_id']}</title>
<style>
  body {{ font-family: monospace; background: #0d0d0d; color: #e0e0e0; padding: 20px; }}
  h1 {{ color: #ff4444; border-bottom: 2px solid #ff4444; }}
  h2 {{ color: #44aaff; border-bottom: 1px solid #44aaff; margin-top: 30px; }}
  h3 {{ color: #44ff88; }}
  table {{ width: 100%; border-collapse: collapse; margin: 10px 0; font-size: 12px; }}
  th {{ background: #1a3a5c; color: white; padding: 6px; text-align: left; }}
  td {{ padding: 5px; border-bottom: 1px solid #333; }}
  tr:nth-child(even) {{ background: #111; }}
  .stat-grid {{ display: grid; grid-template-columns: repeat(4,1fr); gap: 10px; margin: 10px 0; }}
  .stat-card {{ background: #111; border: 1px solid #333; padding: 15px; text-align: center; }}
  .stat-val {{ font-size: 28px; font-weight: bold; color: #44aaff; }}
  .stat-lbl {{ font-size: 11px; color: #888; }}
  .critical {{ color: #ff4444; }} .high {{ color: #ff8844; }}
  .medium {{ color: #ffcc44; }} .low {{ color: #44ff88; }}
  .badge {{ padding: 2px 8px; border-radius: 3px; font-size: 11px; }}
  .yes {{ background: #1a3a1a; color: #44ff88; }}
  .no  {{ background: #3a1a1a; color: #ff4444; }}
  pre {{ background: #111; padding: 10px; overflow-x: auto; font-size: 11px; }}
</style>
</head>
<body>
<h1>INTELLIGENCE REPORT — SIH26151</h1>
<p>Report ID: {report['report_id']}</p>
<p>Generated: {report['generated_at']}</p>
<p>Session: {report['session_id']}</p>
<p>Target: {report['session']['target_username'] or 'All'}</p>

<h2>Executive Summary</h2>
<div class="stat-grid">
  <div class="stat-card"><div class="stat-val">{stats['sites_crawled']}</div><div class="stat-lbl">Sites Crawled</div></div>
  <div class="stat-card"><div class="stat-val">{stats['unique_usernames']}</div><div class="stat-lbl">Unique Usernames</div></div>
  <div class="stat-card"><div class="stat-val">{stats['crypto_wallets']}</div><div class="stat-lbl">Crypto Wallets</div></div>
  <div class="stat-card"><div class="stat-val critical">{stats['critical_misconfigs']}</div><div class="stat-lbl">Critical Misconfigs</div></div>
  <div class="stat-card"><div class="stat-val">{stats['profiles_found']}</div><div class="stat-lbl">Profiles Found</div></div>
  <div class="stat-card"><div class="stat-val">{stats['trust_relationships']}</div><div class="stat-lbl">Trust Links</div></div>
  <div class="stat-card"><div class="stat-val">{stats['same_person_matches']}</div><div class="stat-lbl">Persona Matches</div></div>
  <div class="stat-card"><div class="stat-val">{stats['clusters_found']}</div><div class="stat-lbl">Actor Clusters</div></div>
</div>

<h2>Usernames ({report['usernames']['total_unique']})</h2>
<table>
<tr><th>Username</th><th>Occurrences</th><th>Pattern</th><th>First Seen</th></tr>
{''.join(f"<tr><td>{u['username']}</td><td>{u['occurrences']}</td><td>{u.get('pattern','')}</td><td>{str(u.get('first_seen',''))[:16]}</td></tr>" for u in report['usernames']['details'][:30])}
</table>

<h2>Cryptocurrency Addresses ({report['crypto_addresses']['total_found']})</h2>
{''.join(f"<h3>{curr.upper()} ({len(addrs)})</h3><table><tr><th>Address</th><th>Source</th><th>Context</th></tr>{''.join(f'<tr><td><code>{a[\"address\"]}</code></td><td>{a[\"source\"][:40]}</td><td>{a[\"context\"][:50]}</td></tr>' for a in addrs[:10])}</table>" for curr, addrs in report['crypto_addresses']['by_currency'].items())}

<h2>Misconfigurations ({report['misconfigurations']['total']})</h2>
{''.join(f"<h3 class='{sev.lower()}'>{sev} ({len(items)})</h3><table><tr><th>URL</th><th>Type</th><th>Detail</th></tr>{''.join(f'<tr><td>{m[\"url\"][:40]}</td><td>{m[\"type\"][:30]}</td><td>{m[\"detail\"][:50]}</td></tr>' for m in items[:10])}</table>" for sev, items in report['misconfigurations']['by_severity'].items() if items)}

<h2>Persona Comparisons</h2>
<table>
<tr><th>Username A</th><th>Username B</th><th>Similarity</th><th>Confidence</th><th>Same Person</th></tr>
{''.join(f"<tr><td>{pc['username_a']}</td><td>{pc['username_b']}</td><td>{pc['similarity']}%</td><td>{pc['confidence']}</td><td><span class=\"badge {'yes' if pc['same_person'] else 'no'}\">{'YES' if pc['same_person'] else 'NO'}</span></td></tr>" for pc in report['persona_comparisons'][:20])}
</table>

<h2>Trust Links ({report['trust_links']['total']})</h2>
<table>
<tr><th>From</th><th>To</th><th>Type</th><th>Wallet</th></tr>
{''.join(f"<tr><td>{tl['from'] or ''}</td><td>{tl['to'] or ''}</td><td>{tl['type']}</td><td><code>{tl['wallet'] or ''}</code></td></tr>" for tl in report['trust_links']['details'][:20])}
</table>

<h2>Timing Analysis</h2>
{''.join(f"<div><h3>Target: {ta['target']}</h3><p>Posts: {ta['total_posts']} | Avg Hour: {ta['average_hour']} | Timezone: {ta['timezone']} | Pattern: {ta['activity_pattern']}</p></div>" for ta in report['timing_analysis'])}

<h2>Full Report (JSON)</h2>
<pre>{json.dumps(report['statistics'], indent=2)}</pre>

</body></html>"""

        filename = f"reports/report_{session_id}.html"
        with open(filename, 'w') as f:
            f.write(html)

        success(f"HTML report: {filename}")
        return filename

    def generate_all(self, session_id):
        """Generate JSON + PDF + HTML in one call"""
        info(f"Generating all report formats for session: {session_id}")

        json_file = self.save_json(session_id)
        pdf_file  = self.save_pdf(session_id)
        html_file = self.save_html(session_id)

        success("All reports generated:")
        success(f"  JSON: {json_file}")
        success(f"  PDF:  {pdf_file}")
        success(f"  HTML: {html_file}")

        return {
            'json': json_file,
            'pdf':  pdf_file,
            'html': html_file
}
