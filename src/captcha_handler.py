import re
from utils import warn

class CaptchaHandler:
    """Detect access challenges without attempting to bypass them."""
    CAPTCHA_PATTERNS = [
        r"\bcaptcha\b", r"\brecaptcha\b", r"\bhcaptcha\b",
        r"cloudflare", r"ddos-guard", r"are you human",
        r"prove you are human", r"security check", r"access denied",
        r"bot detection", r"please verify", r"i am not a robot", r"ray id",
    ]

    def __init__(self):
        self.detection_count = 0

    def is_captcha(self, html, status_code=200):
        if status_code in (403, 429, 503):
            self.detection_count += 1
            return True, f"HTTP {status_code} — possible access challenge/block"
        html_lower = (html or "").lower()
        for pattern in self.CAPTCHA_PATTERNS:
            if re.search(pattern, html_lower):
                self.detection_count += 1
                return True, f"Pattern detected: {pattern}"
        return False, None

    def record_detection(self, url, reason):
        warn(f"Access challenge detected: {reason} | {url[:80]}")

    def get_stats(self):
        return {"detections": self.detection_count}
