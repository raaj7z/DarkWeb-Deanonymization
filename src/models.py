# models.py — Dataclasses for entities
# Every entity produced by the crawler is one of these.
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime

def _now_iso() -> str:
    return datetime.utcnow().isoformat(timespec='seconds')

@dataclass
class BaseEntity:
    session_id: str
    source: str = 'crawler'
    confidence: float = 0.0
    confidence_level: str = 'LOW'
    created_at: str = field(default_factory=_now_iso)
    updated_at: Optional[str] = None
    actor_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

# ── Stream 1: OSINT entities (goes to actor report) ──
@dataclass
class OsintEntity(BaseEntity):
    entity_type: str = ''      # username/email/wallet/pgp/telegram/jabber/session_id
    value: str = ''
    normalized: str = ''
    platform: str = 'darkweb'
    source_url: str = ''
    category: str = 'unknown'  # drugs/arms/data/hacking/finance/unknown
    context: str = ''
    occurrences: int = 1

# ── Stream 1: Posts (also goes to actor report — for stylometry) ──
@dataclass
class StyloPost(BaseEntity):
    username: str = ''
    handle: str = ''
    platform: str = 'darkweb'
    source_url: str = ''
    content: str = ''
    raw_html_ref: str = ''
    word_count: int = 0
    char_count: int = 0
    lang: str = 'en'
    timestamp_raw: str = ''
    timestamp_parsed: str = ''
    category: str = 'unknown'

# ── Stream 2: Network artifacts (stays with crawler) ──
@dataclass
class NetworkArtifact(BaseEntity):
    artifact_type: str = ''    # tls_cert/banner/server_status/header/exposed_path/descriptor_leak
    source_url: str = ''
    host: str = ''
    ip_address: str = ''
    domain: str = ''
    port: int = 0
    protocol: str = 'tcp'
    banner: str = ''
    server_software: str = ''
    ssl_issuer: str = ''
    ssl_san: List[str] = field(default_factory=list)
    raw_data: Dict[str, Any] = field(default_factory=dict)
