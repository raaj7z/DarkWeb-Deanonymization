# ai_cleaner.py — Two-bucket classifier
# Takes raw intel_extractor output, returns (actor_rows, network_rows).
# Rules first; ML toggle exists but is off by default.
import re
from typing import Dict, List, Any, Tuple
from config import (
    USERNAME_BLACKLIST, BOILERPLATE_PATTERNS, CATEGORY_KEYWORDS,
    confidence_level,
)
from models import OsintEntity, StyloPost, NetworkArtifact
from logging_setup import get_logger
# Local ML, no API needed
from sklearn.naive_bayes import MultinomialNB
from sklearn.feature_extraction.text import TfidfVectorizer

class MLRefiner:
    def __init__(self):
        self.vec = TfidfVectorizer(max_features=500)
        self.clf = MultinomialNB()
        self.trained = False

    def train(self, samples, labels):
        # samples: list of text; labels: 'actor' / 'network' / 'trash'
        X = self.vec.fit_transform(samples)
        self.clf.fit(X, labels)
        self.trained = True

    def predict(self, text):
        if not self.trained:
            return None
        X = self.vec.transform([text])
        return self.clf.predict(X)[0], self.clf.predict_proba(X).max()

log = get_logger('ai_cleaner')

_BOILER_RE = [re.compile(p, re.IGNORECASE) for p in BOILERPLATE_PATTERNS]


class AICleaner:
    def __init__(self, session_id: str):
        self.session_id = session_id

    # ── Public API ──
    def clean(self, raw: Dict[str, Any]) -> Tuple[List[Dict], List[Dict]]:
        """
        raw: merged intel_extractor output + crawler result
        Returns: (actor_rows, network_rows)
        """
        source_url = raw.get('url', '')

        osint_entities = self._build_osint_entities(raw, source_url)
        stylo_posts    = self._build_stylo_posts(raw, source_url)
        network_arts   = self._build_network_artifacts(raw, source_url)

        actor_rows   = [e.to_dict() for e in osint_entities] + \
                       [p.to_dict() for p in stylo_posts]
        network_rows = [n.to_dict() for n in network_arts]

        log.info(
            f"cleaned {source_url[:50]} -> "
            f"osint={len(osint_entities)} posts={len(stylo_posts)} "
            f"network={len(network_arts)}"
        )
        return actor_rows, network_rows

    # ── OSINT bucket ──
    def _build_osint_entities(self, raw: Dict, url: str) -> List[OsintEntity]:
        entities: List[OsintEntity] = []
        seen = set()

        # Usernames
        for u in raw.get('usernames', []) or []:
            n = (u or '').strip().lower()
            if not n or n in USERNAME_BLACKLIST or len(n) < 3:
                continue
            if n in seen:
                continue
            seen.add(n)
            conf = 55.0
            entities.append(OsintEntity(
                session_id=self.session_id,
                entity_type='username',
                value=u, normalized=n,
                source_url=url,
                category=self._classify_category(raw.get('text', '')),
                confidence=conf,
                confidence_level=confidence_level(conf),
            ))

        # Emails
        for e in raw.get('emails', []) or []:
            n = (e or '').strip().lower()
            if not n or n in seen:
                continue
            seen.add(n)
            conf = 80.0
            entities.append(OsintEntity(
                session_id=self.session_id,
                entity_type='email',
                value=e, normalized=n,
                source_url=url,
                confidence=conf,
                confidence_level=confidence_level(conf),
            ))

        # Wallets
        validated = raw.get('crypto_validated', {}) or {}
        for currency, addrs in (raw.get('crypto_addresses') or {}).items():
            for a in addrs:
                if a in seen:
                    continue
                seen.add(a)
                conf = 90.0 if validated.get(a) else 45.0
                entities.append(OsintEntity(
                    session_id=self.session_id,
                    entity_type='wallet',
                    value=a, normalized=a,
                    source_url=url,
                    context=(raw.get('crypto_context', {}).get(a, '') or '')[:300],
                    confidence=conf,
                    confidence_level=confidence_level(conf),
                ))

        # PGP keys
        profiles = raw.get('profiles') or {}
        for v in profiles.get('pgp_keys', []) or []:
            fingerprint = v[:200]
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            conf = 95.0
            entities.append(OsintEntity(
                session_id=self.session_id,
                entity_type='pgp',
                value=v, normalized=fingerprint,
                source_url=url,
                confidence=conf,
                confidence_level=confidence_level(conf),
            ))

        # Communication channels (telegram, wickr, session)
        for chan in profiles.get('communication_channels', []) or []:
            val = chan.get('value') if isinstance(chan, dict) else str(chan)
            if not val or val in seen:
                continue
            seen.add(val)
            conf = 75.0
            entities.append(OsintEntity(
                session_id=self.session_id,
                entity_type=chan.get('type', 'channel') if isinstance(chan, dict) else 'channel',
                value=val, normalized=val.lower(),
                source_url=url,
                confidence=conf,
                confidence_level=confidence_level(conf),
            ))

        return entities

    # ── Posts bucket ──
    def _build_stylo_posts(self, raw: Dict, url: str) -> List[StyloPost]:
        posts: List[StyloPost] = []
        for p in raw.get('posts_with_timing', []) or []:
            text = self._strip_boilerplate(p.get('text', ''))
            if len(text.split()) < 5:
                continue
            ts_list = p.get('timestamps') or ['']
            posts.append(StyloPost(
                session_id=self.session_id,
                username=p.get('username', 'unknown'),
                handle=(p.get('username') or '').lower(),
                source_url=url,
                content=text,
                raw_html_ref=p.get('raw_html_ref', ''),
                word_count=len(text.split()),
                char_count=len(text),
                timestamp_raw=ts_list[0] if ts_list else '',
                category=self._classify_category(text),
                confidence=70.0,
                confidence_level=confidence_level(70.0),
            ))
        return posts

    # ── Network bucket ──
    def _build_network_artifacts(self, raw: Dict, url: str) -> List[NetworkArtifact]:
        arts: List[NetworkArtifact] = []

        # TLS cert
        ssl_info = raw.get('ssl_info') or {}
        if ssl_info.get('ssl_available'):
            cert = ssl_info.get('certificate', {})
            arts.append(NetworkArtifact(
                session_id=self.session_id,
                artifact_type='tls_cert',
                source_url=url,
                host=(cert.get('subject', '') or '')[:200],
                ssl_issuer=cert.get('issuer', ''),
                ssl_san=cert.get('san', []) or [],
                raw_data=cert,
                confidence=90.0,
                confidence_level=confidence_level(90.0),
            ))

        # Server-status hits
        for hit in raw.get('server_status_hits', []) or []:
            arts.append(NetworkArtifact(
                session_id=self.session_id,
                artifact_type='server_status',
                source_url=url,
                raw_data=hit,
                confidence=85.0,
                confidence_level=confidence_level(85.0),
            ))

        # Banners
        for port, b in (raw.get('service_banners') or {}).items():
            arts.append(NetworkArtifact(
                session_id=self.session_id,
                artifact_type='banner',
                source_url=url,
                port=int(port) if str(port).isdigit() else 0,
                banner=(b.get('banner', '') or '')[:500],
                server_software=b.get('version', ''),
                raw_data=b,
                confidence=80.0,
                confidence_level=confidence_level(80.0),
            ))

        # Descriptor leak
        descriptor = raw.get('descriptor') or {}
        if descriptor.get('inconsistencies'):
            arts.append(NetworkArtifact(
                session_id=self.session_id,
                artifact_type='descriptor_leak',
                source_url=url,
                raw_data=descriptor,
                confidence=70.0,
                confidence_level=confidence_level(70.0),
            ))

        # Headers of interest
        headers = raw.get('headers') or {}
        interesting = {k: v for k, v in headers.items()
                       if k.lower() in ('server', 'x-powered-by', 'via',
                                        'x-generator', 'x-aspnet-version')}
        if interesting:
            arts.append(NetworkArtifact(
                session_id=self.session_id,
                artifact_type='header',
                source_url=url,
                server_software=interesting.get('Server', ''),
                raw_data=interesting,
                confidence=60.0,
                confidence_level=confidence_level(60.0),
            ))

        # Exposed paths
        for path in raw.get('exposed_paths', []) or []:
            arts.append(NetworkArtifact(
                session_id=self.session_id,
                artifact_type='exposed_path',
                source_url=url + path if path.startswith('/') else url,
                raw_data={'path': path},
                confidence=75.0,
                confidence_level=confidence_level(75.0),
            ))

        return arts

    # ── Helpers ──
    def _strip_boilerplate(self, text: str) -> str:
        lines = []
        for line in (text or '').split('\n'):
            s = line.strip()
            if not s or len(s) < 3:
                continue
            if any(rx.search(s) for rx in _BOILER_RE):
                continue
            lines.append(s)
        return ' '.join(lines)

    def _classify_category(self, text: str) -> str:
        if not text:
            return 'unknown'
        t = text.lower()
        scores = {cat: 0 for cat in CATEGORY_KEYWORDS}
        for cat, kws in CATEGORY_KEYWORDS.items():
            for kw in kws:
                if kw in t:
                    scores[cat] += 1
        best = max(scores, key=scores.get)
        return best if scores[best] > 0 else 'unknown'
