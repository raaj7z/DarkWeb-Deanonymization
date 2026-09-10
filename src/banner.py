# banner.py — NEW FILE
# SOCKS-based service banner grabbing.
# This replaces the broken grab_service_banner() in your original crawler.py,
# which used raw socket.connect() on .onion hosts (always failed).
import re
import socks
from config import TOR_SOCKS_HOST, TOR_SOCKS_PORT
from utils import success, warn

# Minimal probes per port — empty bytes means the service sends its banner on connect
PROBES = {
    80:  b'HEAD / HTTP/1.0\r\nHost: localhost\r\n\r\n',
    443: b'HEAD / HTTP/1.0\r\nHost: localhost\r\n\r\n',
    22:  b'',
    21:  b'',
    25:  b'',
    3306: b'',
}

# Banners that reveal default/misconfigured installs
DEFAULT_BANNERS = [
    'Apache/2.4.41',
    'nginx/1.18.0',
    'OpenSSH_7.9',
    'ProFTPD',
    'Postfix ESMTP',
]


def grab_banner(host, port, timeout=8):
    """
    Connect to host:port through the Tor SOCKS5 proxy and read the banner.

    Returns dict:
      {host, port, banner, service, version, vulnerabilities, error?}
    """
    result = {
        'host': host,
        'port': port,
        'banner': '',
        'service': '',
        'version': '',
        'vulnerabilities': [],
    }

    try:
        s = socks.socksocket()
        s.set_proxy(socks.SOCKS5, TOR_SOCKS_HOST, TOR_SOCKS_PORT, rdns=True)
        s.settimeout(timeout)
        s.connect((host, port))

        probe = PROBES.get(port, b'')
        if probe:
            s.send(probe)

        banner = s.recv(1024).decode('utf-8', errors='ignore').strip()
        s.close()
        result['banner'] = banner[:1000]

        # Parse service + version from banner
        if 'SSH' in banner:
            m = re.search(r'SSH-[\d\.]+-(.+)', banner)
            result['service'] = 'SSH'
            result['version'] = m.group(1) if m else ''

        elif 'HTTP' in banner or 'Server:' in banner:
            m = re.search(r'Server:\s*(.+)', banner)
            result['service'] = 'HTTP'
            result['version'] = m.group(1).strip() if m else ''

        elif '220' in banner and 'FTP' in banner.upper():
            result['service'] = 'FTP'

        elif '220' in banner and 'SMTP' in banner.upper():
            result['service'] = 'SMTP'

        elif 'mysql' in banner.lower():
            result['service'] = 'MySQL'

        # Flag default banners as vulnerabilities
        for d in DEFAULT_BANNERS:
            if d.lower() in banner.lower():
                result['vulnerabilities'].append(f'Default banner: {d}')

        if result['banner']:
            success(f"Banner [{port}] {banner[:60]}")

    except Exception as e:
        result['error'] = str(e)[:200]
        warn(f"Banner grab failed {host}:{port}: {str(e)[:60]}")

    return result
