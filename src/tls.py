# tls.py — NEW FILE
# Thin wrapper around IntelExtractor.get_ssl_info.
# Used by the crawler to fetch TLS certificates over Tor SOCKS5.
from intel_extractor import IntelExtractor

_extractor = IntelExtractor()


def fetch_tls(hostname, port=443):
    """
    Fetch TLS certificate info for hostname:port through Tor.

    Returns the same dict shape as IntelExtractor.get_ssl_info:
      {hostname, port, ssl_available, certificate, vulnerabilities, server_info, error?}
    """
    return _extractor.get_ssl_info(hostname, port)
