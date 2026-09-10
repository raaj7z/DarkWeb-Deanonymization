# server_status.py — NEW FILE
# Probes common misconfiguration endpoints through Tor.
# Feeds the network report bucket in ai_cleaner.
from utils import get_tor_session, info, warn

# Paths commonly left exposed on misconfigured hidden services
STATUS_PATHS = [
    ('/server-status',      'apache_server_status'),
    ('/server-status?auto', 'apache_server_status_auto'),
    ('/nginx_status',       'nginx_status'),
    ('/phpinfo.php',        'phpinfo'),
    ('/info.php',           'phpinfo_alt'),
    ('/test.php',           'php_test'),
    ('/phpMyAdmin/',        'phpmyadmin'),
    ('/.git/config',        'git_config'),
    ('/.env',               'dotenv'),
    ('/backup.sql',         'backup_sql'),
]


class ServerStatusChecker:
    """Probes a base URL for common misconfiguration endpoints."""

    def __init__(self):
        self.session = get_tor_session()

    def check(self, base_url, timeout=15):
        """
        Returns a list of hits. Each hit is a dict:
          {url, type, status, snippet, length}
        Empty list if nothing found.
        """
        hits = []
        base = base_url.rstrip('/')

        for path, label in STATUS_PATHS:
            url = base + path
            try:
                r = self.session.get(url, timeout=timeout, allow_redirects=False)
                # 200 with real content = hit
                if r.status_code == 200 and len(r.content) > 100:
                    hits.append({
                        'url': url,
                        'type': label,
                        'status': r.status_code,
                        'snippet': r.text[:500],
                        'length': len(r.content),
                    })
                    info(f"  server-status hit: {label} at {url[:60]}")
            except Exception as e:
                warn(f"  status check failed {url[:40]}: {str(e)[:40]}")

        return hits
