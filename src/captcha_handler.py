# captcha_handler.py — CAPTCHA detection and bypass strategies
import re
import time
import random
from utils import warn, info, success, error

class CaptchaHandler:
    
    # Common CAPTCHA indicators
    CAPTCHA_PATTERNS = [
        r'captcha',
        r'recaptcha',
        r'hcaptcha',
        r'cloudflare',
        r'ddos-guard',
        r'are you human',
        r'prove you are human',
        r'security check',
        r'access denied',
        r'bot detection',
        r'please verify',
        r'i am not a robot',
        r'challenge',
        r'ray id',  # Cloudflare
    ]
    
    def __init__(self):
        # Count of detected CAPTCHAs
        self.detection_count = 0
    
    def is_captcha(self, html, status_code=200):
        """Detect if page has CAPTCHA or bot detection"""
        if status_code in [403, 429, 503]:
            return True, f"HTTP {status_code} — likely bot block"
        
        html_lower = html.lower()
        for pattern in self.CAPTCHA_PATTERNS:
            if re.search(pattern, html_lower):
                return True, f"Pattern detected: {pattern}"
        
        # Check if page is suspiciously short
        if len(html.strip()) < 500:
            return True, "Page too short — possible redirect/block"
        
        return False, None
    
    def bypass_strategy(self, url, session):
        """
        Try multiple bypass strategies
        Returns response or None
        """
        strategies = [
            self._strategy_delay,
            self._strategy_new_identity,
            self._strategy_different_headers,
            self._strategy_slow_request,
        ]
        
        for strategy in strategies:
            # Use getattr to safely get the callable name
            strategy_name = getattr(strategy, '__name__', str(strategy))
            info(f"Trying bypass: {strategy_name}")
            try:
                result = strategy(url, session)
                if result:
                    success(f"Bypass worked: {strategy_name}")
                    return result
            except Exception as e:
                warn(f"Bypass strategy {strategy_name} raised: {e}")
            time.sleep(random.uniform(3, 8))
        
        error("All bypass strategies failed")
        return None
    
    def _strategy_delay(self, url, session):
        """Wait and retry — some CAPTCHAs are time-based"""
        wait = random.uniform(15, 30)
        info(f"Waiting {wait:.0f}s before retry...")
        time.sleep(wait)
        try:
            r = session.get(url, timeout=30)
            if r.status_code == 200:
                return r
        except Exception as e:
            warn(f"_strategy_delay failed: {e}")
        return None
    
    def _strategy_new_identity(self, url, session):
        """Get new Tor circuit — new exit node = new IP"""
        from tor_controller import TorController
        try:
            controller = TorController()
            controller.new_circuit()
            time.sleep(5)
            r = session.get(url, timeout=30)
            if r.status_code == 200:
                return r
        except Exception as e:
            warn(f"_strategy_new_identity failed: {e}")
        return None
    
    def _strategy_different_headers(self, url, session):
        """Try completely different browser fingerprint"""
        headers_list = [
            {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; rv:109.0) Gecko/20100101 Firefox/115.0',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-GB,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            },
            {
                'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Connection': 'keep-alive',
            }
        ]
        
        for headers in headers_list:
            try:
                session.headers.update(headers)
                r = session.get(url, timeout=30)
                if r.status_code == 200:
                    return r
                time.sleep(random.uniform(2, 5))
            except Exception as e:
                warn(f"_strategy_different_headers failed for headers {headers.get('User-Agent','')[:30]}: {e}")
                continue
        return None
    
    def _strategy_slow_request(self, url, session):
        """Simulate slow human browsing"""
        try:
            # Add referrer like a real browser
            session.headers.update({
                'Referer': 'http://duckduckgogg42xjoc72x3sjasowoarfbgcmvfimaftt6twagswzczad.onion/',
                'Cache-Control': 'max-age=0',
            })
            time.sleep(random.uniform(5, 10))
            r = session.get(url, timeout=45)
            if r.status_code == 200:
                return r
        except Exception as e:
            warn(f"_strategy_slow_request failed: {e}")
        return None
    
    def get_stats(self):
        return {'detections': self.detection_count}
