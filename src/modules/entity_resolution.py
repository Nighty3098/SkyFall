"""Entity resolution for the investigation graph.

Transforms regularly create the same real-world entity more than once: the
same person under different spellings, the same phone number with different
formatting, or the same profile reached through two modules.  This module
provides the matching engine behind SkyFall's automatic deduplication:

* identifiers are extracted and canonicalised (e-mail, phone, URL, username,
  IP, MAC, hashes, crypto wallets, social profiles);
* titles are normalised (Unicode, accents, Cyrillic transliteration) and
  compared with name/token aware similarity;
* candidate pairs are found with blocking so a large graph is not compared
  quadratically;
* matches are clustered with a complete-link guard so a weak transitive match
  cannot merge two unrelated records;
* the merge itself preserves every alias, content line and evidence item.

The module is deliberately Qt-free.  ``GraphWidget`` adapts the result to its
``NodeItem`` objects, while tests and MCP/CLI consumers can work on plain graph
dictionaries (``{"nodes": [...], "edges": [...]}``).
"""

from __future__ import annotations

import ipaddress
import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from difflib import SequenceMatcher
from typing import Any

try:  # phonenumbers is an optional runtime dependency
    import phonenumbers
except Exception:  # pragma: no cover - dependency is present in SkyFall
    phonenumbers = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResolutionConfig:
    """Thresholds and weights used by the matcher.

    ``auto_threshold`` is intentionally conservative.  Pairs between that and
    ``review_threshold`` are reported to the analyst but never merged without
    confirmation.
    """

    auto_threshold: float = 0.94
    review_threshold: float = 0.70
    min_title_similarity: float = 0.55
    name_weight: float = 0.90
    content_weight: float = 0.08
    identifier_bonus: float = 0.02
    max_bucket_size: int = 250
    max_pairs: int = 250_000


DEFAULT_CONFIG = ResolutionConfig()

# Entity types whose identity is defined by the value itself.  Two different
# e-mail addresses (or domains, IPs, ...) are never the same entity, even when
# their titles look alike.
_UNIQUE_IDENTITY_TYPES = {
    "Email",
    "Phone",
    "Domain",
    "URL",
    "IP",
    "MAC",
    "Hash",
    "Crypto",
    "Username",
    "SocialMedia",
    "Nameserver",
    "ASN",
    "Netblock",
}

# Types where an identical normalised title is a strong enough duplicate
# signal to be merged automatically even without a shared identifier.
_TITLE_AUTO_TYPES = {"Person", "Organization", "Custom"}

_HONORIFICS = {
    "mr",
    "mrs",
    "ms",
    "miss",
    "dr",
    "prof",
    "sir",
    "madam",
    "г",
    "гн",
    "гжа",
    "господин",
    "госпожа",
    "др",
    "проф",
}

_ORG_SUFFIXES = {
    "llc",
    "ltd",
    "limited",
    "inc",
    "corp",
    "corporation",
    "company",
    "co",
    "llp",
    "pllc",
    "gmbh",
    "plc",
    "ag",
    "sa",
    "ооо",
    "оао",
    "зао",
    "пао",
    "ип",
    "ао",
}

_CYRILLIC_TRANSLIT = str.maketrans(
    {
        "а": "a",
        "б": "b",
        "в": "v",
        "г": "g",
        "д": "d",
        "е": "e",
        "ё": "e",
        "ж": "zh",
        "з": "z",
        "и": "i",
        "й": "y",
        "к": "k",
        "л": "l",
        "м": "m",
        "н": "n",
        "о": "o",
        "п": "p",
        "р": "r",
        "с": "s",
        "т": "t",
        "у": "u",
        "ф": "f",
        "х": "kh",
        "ц": "ts",
        "ч": "ch",
        "ш": "sh",
        "щ": "shch",
        "ъ": "",
        "ы": "y",
        "ь": "",
        "э": "e",
        "ю": "yu",
        "я": "ya",
    }
)

_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")
_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}\b", re.I)
_URL_RE = re.compile(r"https?://[^\s<>\"'`]+", re.I)
_DOMAIN_RE = re.compile(
    r"(?<![\w@.])(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}\b",
    re.I,
)
_MAC_RE = re.compile(r"\b(?:[0-9a-f]{2}[:-]){5}[0-9a-f]{2}\b", re.I)
_PHONE_RE = re.compile(
    r"(?<![\w])(?:\+|00)?\d(?:[\d\s().\-]{4,18}\d)(?![\w])",
)
_HANDLE_RE = re.compile(r"(?<![\w@])@[A-Za-z0-9_]{2,64}\b")
_BTC_RE = re.compile(r"\b(?:bc1[a-z0-9]{25,62}|[13][a-km-zA-HJ-NP-Z1-9]{25,34})\b")
_ETH_RE = re.compile(r"\b0x[a-fA-F0-9]{40}\b")
_TRON_RE = re.compile(r"\bT[1-9A-HJ-NP-Za-km-z]{33}\b")
_HASH_RE = re.compile(r"\b[a-fA-F0-9]{32}(?:[a-fA-F0-9]{8}|[a-fA-F0-9]{32})?\b")

_KEY_ALIASES = {
    "email": "email",
    "e-mail": "email",
    "e_mail": "email",
    "email_address": "email",
    "mail": "email",
    "почта": "email",
    "pochta": "email",
    "элпочта": "email",
    "elpochta": "email",
    "phone": "phone",
    "phone_number": "phone",
    "telephone": "phone",
    "tel": "phone",
    "mobile": "phone",
    "msisdn": "phone",
    "телефон": "phone",
    "telefon": "phone",
    "номер": "phone",
    "nomer": "phone",
    "username": "username",
    "user": "username",
    "login": "username",
    "nick": "username",
    "nickname": "username",
    "handle": "username",
    "telegram": "username",
    "tg": "username",
    "логин": "username",
    "ник": "username",
    "url": "url",
    "uri": "url",
    "link": "url",
    "website": "url",
    "site": "url",
    "domain": "domain",
    "host": "domain",
    "hostname": "domain",
    "ip": "ip",
    "ip_address": "ip",
    "ipv4": "ip",
    "ipv6": "ip",
    "mac": "mac",
    "mac_address": "mac",
    "bssid": "mac",
    "wallet_address": "crypto",
    "btc": "crypto",
    "eth": "crypto",
    "tron": "crypto",
    "wallet": "crypto",
    "crypto": "crypto",
    "hash": "hash",
    "md5": "hash",
    "sha1": "hash",
    "sha256": "hash",
    "inn": "document",
    "passport": "document",
    "snils": "document",
    "ogrn": "document",
    "document": "document",
    "asn": "asn",
    "netblock": "netblock",
    "cidr": "netblock",
    "nameserver": "domain",
    "ns": "domain",
}

_IDENTIFIER_TYPES = {
    "email",
    "phone",
    "username",
    "url",
    "domain",
    "ip",
    "mac",
    "crypto",
    "hash",
    "document",
    "asn",
    "netblock",
}

_TITLE_TYPE_IDENTIFIER = {
    "Email": "email",
    "Phone": "phone",
    "Domain": "domain",
    "Nameserver": "domain",
    "URL": "url",
    "IP": "ip",
    "MAC": "mac",
    "Username": "username",
    "SocialMedia": "username",
    "Crypto": "crypto",
    "Hash": "hash",
    "ASN": "asn",
    "Netblock": "netblock",
}


# ---------------------------------------------------------------------------
# Parsing and canonicalisation
# ---------------------------------------------------------------------------


def normalize_text(value: Any) -> str:
    """Fold arbitrary text into a comparable ASCII-ish lower-case form."""
    if value is None:
        return ""
    text = str(value).strip().casefold().translate(_CYRILLIC_TRANSLIT)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = _NON_ALNUM_RE.sub(" ", text)
    return " ".join(text.split())


def normalize_title(value: Any) -> str:
    """Normalise a title for exact comparison (keeps punctuation out)."""
    return normalize_text(value)


def normalize_name(value: Any) -> str:
    """Normalise a human/organisation name.

    Word order is preserved here; :func:`name_similarity` also compares token
    sets, so "Ivan Petrov" and "Petrov Ivan" still match.
    """
    tokens = [tok for tok in normalize_text(value).split() if tok not in _HONORIFICS]
    return " ".join(tokens)


def _normalize_org(value: Any) -> str:
    tokens = normalize_text(value).split()
    tokens = [tok for tok in tokens if tok not in _ORG_SUFFIXES]
    return " ".join(tokens)


def normalize_email(value: Any) -> str:
    text = str(value or "").strip().strip("<>()[]{}.,;:").casefold()
    if "mailto:" in text:
        text = text.split("mailto:", 1)[1]
    return text


def normalize_phone(value: Any) -> str:
    """Return an E.164-like canonical phone number.

    ``phonenumbers`` is used when the value parses unambiguously.  The fallback
    keeps the last 10 significant digits, which makes common local formats
    (``8 999 ...``, ``+7 999 ...``, ``999-...``) match each other.
    """
    raw = str(value or "").strip()
    if not raw:
        return ""
    if phonenumbers is not None:
        for region in ("RU", "US", "GB", None):
            try:
                number = phonenumbers.parse(raw, region)
                if phonenumbers.is_possible_number(
                    number
                ) and phonenumbers.is_valid_number(number):
                    return phonenumbers.format_number(
                        number, phonenumbers.PhoneNumberFormat.E164
                    )
            except Exception:
                continue

    digits = re.sub(r"\D", "", raw)
    if not digits:
        return ""
    if len(digits) == 11 and digits.startswith("8"):
        digits = "7" + digits[1:]
    if len(digits) > 10:
        return digits
    return digits.zfill(10)


def normalize_url(value: Any) -> str:
    text = str(value or "").strip().strip("<>()[]{}\"'.,;").casefold()
    if not text:
        return ""
    text = re.sub(r"^[a-z][a-z0-9+.-]*://", "", text)
    text = re.sub(r"^www\d*\.", "", text)
    text = text.split("#", 1)[0].split("?", 1)[0].rstrip("/")
    return text


def normalize_domain(value: Any) -> str:
    text = normalize_url(value)
    if "/" in text:
        text = text.split("/", 1)[0]
    if ":" in text and not text.startswith("["):
        text = text.split(":", 1)[0]
    return text.strip(".").casefold()


def normalize_username(value: Any) -> str:
    text = normalize_url(value)
    text = text.rstrip("/")
    if "/" in text:
        text = text.rsplit("/", 1)[-1]
    text = text.lstrip("@")
    text = re.sub(r"^(?:u/|user/|users/)", "", text)
    return text.casefold()


def normalize_crypto(value: Any) -> str:
    text = str(value or "").strip().strip("<>()[]{}\"'.,;")
    # Ethereum/TRON are case-insensitive in practice; Bitcoin base58 is not,
    # but lower-casing still gives a stable key for duplicate detection.
    return text.casefold()


def normalize_hash(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or "")).casefold()


def normalize_ip(value: Any) -> str:
    try:
        return str(ipaddress.ip_address(str(value).strip().strip("[]")))
    except ValueError:
        return ""


def normalize_netblock(value: Any) -> str:
    try:
        return str(ipaddress.ip_network(str(value).strip(), strict=False))
    except ValueError:
        return ""


def _clean_value(value: str) -> str:
    return value.strip().strip("<>()[]{}\"'`.,;")


def _identifier(kind: str, raw: Any) -> str:
    """Canonicalise and validate a raw value for an identifier kind.

    Validation matters because key-value extraction is intentionally liberal:
    ``mail: alice@example.com`` must not turn the rest of the line into an
    e-mail identifier, and a URL path that happens to contain digits must not
    become a phone number.
    """
    if raw is None:
        return ""
    text = str(raw).strip()
    if not text:
        return ""
    if kind == "email":
        val = normalize_email(text)
        if not _EMAIL_RE.fullmatch(val):
            return ""
    elif kind == "phone":
        val = normalize_phone(text)
        digits = re.sub(r"\D", "", val)
        if not 7 <= len(digits) <= 15:
            return ""
        val = f"+{digits}" if val.startswith("+") else digits
    elif kind == "username":
        val = normalize_username(text)
        if not re.fullmatch(r"[a-z0-9_.\-]{2,64}", val):
            return ""
    elif kind == "url":
        val = normalize_url(text)
        if not val or any(ch.isspace() for ch in val):
            return ""
    elif kind == "domain":
        val = normalize_domain(text)
        if not _DOMAIN_RE.fullmatch(val):
            return ""
    elif kind == "ip":
        val = normalize_ip(text)
    elif kind == "mac":
        val = text.casefold().replace("-", ":")
        if not _MAC_RE.fullmatch(val):
            return ""
    elif kind == "crypto":
        val = normalize_crypto(text)
        if not any(pattern.fullmatch(val) for pattern in (_BTC_RE, _ETH_RE, _TRON_RE)):
            return ""
    elif kind == "hash":
        val = normalize_hash(text)
        if len(val) not in (32, 40, 64) or not re.fullmatch(r"[0-9a-f]+", val):
            return ""
    elif kind == "document":
        val = re.sub(r"\s+", "", text).casefold()
        if not re.fullmatch(r"[0-9a-z\-]{4,32}", val):
            return ""
    elif kind == "asn":
        digits = re.sub(r"\D", "", text)
        val = f"as{digits}" if digits else ""
    elif kind == "netblock":
        val = normalize_netblock(text)
    else:
        val = normalize_text(text)
    return f"{kind}:{val}" if val else ""


def _add_identifier(bucket: set[str], kind: str, raw: Any) -> None:
    value = _identifier(kind, raw)
    if value:
        value = value.replace("\x00", "")
        if len(value.split(":", 1)[1]) >= 2:
            bucket.add(value)


def _split_key_value(line: str) -> tuple[str, str] | None:
    for sep in (":", "="):
        if sep not in line:
            continue
        key, value = line.split(sep, 1)
        key = normalize_text(key).replace(" ", "_")
        if not key or not value.strip():
            continue
        # ``https://...`` and similar lines start with a "key" that is not an
        # entity field.  Only accept keys we actually understand, otherwise a
        # URL would be parsed as a field named ``https`` (and the whole URL as
        # its value).
        if key not in _KEY_ALIASES and key.replace("_", "") not in _KEY_ALIASES:
            return None
        return key, value.strip()
    return None


def extract_identifiers(text: Any) -> set[str]:
    """Extract canonical identifiers from free-form text."""
    source = str(text or "")
    found: set[str] = set()

    for match in _EMAIL_RE.findall(source):
        _add_identifier(found, "email", match)
    for match in _URL_RE.findall(source):
        _add_identifier(found, "url", _clean_value(match))
    for match in _MAC_RE.findall(source):
        _add_identifier(found, "mac", match)
    for match in _HANDLE_RE.findall(source):
        _add_identifier(found, "username", match)
    for match in _BTC_RE.findall(source):
        _add_identifier(found, "crypto", match)
    for match in _ETH_RE.findall(source):
        _add_identifier(found, "crypto", match)
    for match in _TRON_RE.findall(source):
        _add_identifier(found, "crypto", match)

    # Bare domains and phone numbers are useful, but not when they are merely
    # parts of a URL or an e-mail (identity is already covered there).  Without
    # masking, a URL path such as ``/1234567890`` looks like a phone number.
    masked = _URL_RE.sub(" ", source)
    masked = _EMAIL_RE.sub(" ", masked)
    for match in _DOMAIN_RE.findall(masked):
        _add_identifier(found, "domain", _clean_value(match))

    # Phone numbers: validate digit count to avoid dates and tiny numbers.
    for match in _PHONE_RE.findall(masked):
        digits = re.sub(r"\D", "", match)
        if 7 <= len(digits) <= 15:
            _add_identifier(found, "phone", _clean_value(match))

    # Hashes are only meaningful when labelled; a random 32-char hex string is
    # more often an internal id than a hash.
    for line in source.splitlines():
        pair = _split_key_value(line)
        if pair is None:
            continue
        key, value = pair
        if _KEY_ALIASES.get(key) != "hash":
            continue
        for part in re.split(r"[,;|\s]+", value):
            match = _clean_value(part)
            if len(match) in (32, 40, 64) and re.fullmatch(r"[0-9a-fA-F]+", match):
                found.add(f"hash:{match.casefold()}")

    for line in source.splitlines():
        pair = _split_key_value(line)
        if pair is None:
            continue
        key, value = pair
        kind = _KEY_ALIASES.get(key)
        if kind is None:
            kind = _KEY_ALIASES.get(key.replace("_", ""))
        if kind is None:
            continue
        # A labelled value may be a comma/semicolon/pipe separated list.  Do
        # not split on whitespace: ``mail: alice@example.com +7 ...`` should
        # only contribute the e-mail, not every token after it.
        parts = [
            _clean_value(part)
            for part in re.split(r"[,;|]+", value)
            if _clean_value(part)
        ]
        for part in parts:
            _add_identifier(found, kind, part)
        # Some sources wrap a URL in prose ("site: see https://..."); keep the
        # embedded value as well when the direct field did not validate.
        if kind in {"url", "domain", "email"}:
            _add_identifier(found, kind, _clean_value(value))

    return found


def _title_identity(entity_type: str, title: str) -> set[str]:
    kind = _TITLE_TYPE_IDENTIFIER.get(entity_type)
    if not kind or not title:
        return set()
    found: set[str] = set()
    _add_identifier(found, kind, title)
    return found


# ---------------------------------------------------------------------------
# Records and profiles
# ---------------------------------------------------------------------------


@dataclass
class EntityRecord:
    """A Qt-free view of a graph node."""

    id: str
    title: str = ""
    entity_type: str = "Custom"
    content: str = ""
    evidence: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EntityRecord:
        return cls(
            id=str(data.get("id", "")),
            title=str(data.get("title", "") or ""),
            entity_type=str(data.get("entity_type", "Custom") or "Custom"),
            content=str(data.get("content", "") or ""),
            evidence=[str(item) for item in (data.get("evidence") or [])],
            metadata=dict(data.get("metadata") or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "entity_type": self.entity_type,
            "content": self.content,
            "evidence": list(self.evidence),
            "metadata": dict(self.metadata),
        }


@dataclass
class EntityProfile:
    record: EntityRecord
    normalized_title: str
    tokens: tuple[str, ...]
    identifiers: set[str]
    strong_identifiers: set[str]
    identity_prefixes: set[str]
    content_text: str

    @property
    def entity_type(self) -> str:
        return self.record.entity_type


def build_profile(record: EntityRecord) -> EntityProfile:
    entity_type = record.entity_type or "Custom"
    if entity_type == "Person":
        title_text = normalize_name(record.title)
    elif entity_type == "Organization":
        title_text = _normalize_org(record.title)
    else:
        title_text = normalize_title(record.title)

    identifiers = extract_identifiers(record.title)
    identifiers |= extract_identifiers(record.content)
    identifiers |= _title_identity(entity_type, record.title)

    # Evidence paths can contain identifiers as well (e.g. a profile URL used
    # as an evidence link); include the basename/full path in the extraction.
    for item in record.evidence:
        identifiers |= extract_identifiers(item)

    strong = {
        item
        for item in identifiers
        if item.split(":", 1)[0]
        in {
            "email",
            "phone",
            "username",
            "url",
            "domain",
            "ip",
            "mac",
            "crypto",
            "hash",
        }
    }
    prefixes = {item.split(":", 1)[0] for item in identifiers}
    tokens = tuple(token for token in title_text.split() if token)
    return EntityProfile(
        record=record,
        normalized_title=title_text,
        tokens=tokens,
        identifiers=identifiers,
        strong_identifiers=strong,
        identity_prefixes=prefixes,
        content_text=normalize_text(record.content),
    )


# ---------------------------------------------------------------------------
# Similarity
# ---------------------------------------------------------------------------


def _sequence_similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    if left == right:
        return 1.0
    # SequenceMatcher is quadratic; cap long inputs so pathological log
    # content cannot stall a transform batch.
    return SequenceMatcher(None, left[:400], right[:400], autojunk=False).ratio()


def name_similarity(left: str, right: str) -> float:
    """Compare names in a spelling- and word-order-tolerant way."""
    a = normalize_name(left)
    b = normalize_name(right)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    if sorted(a.split()) == sorted(b.split()):
        return 0.99

    at = a.split()
    bt = b.split()
    if not at or not bt:
        return 0.0

    # Token match with initials: "j smith" should match "john smith".
    matched = 0.0
    used: set[int] = set()
    for token in at:
        best_index = None
        best = 0.0
        for index, other in enumerate(bt):
            if index in used:
                continue
            if token == other:
                score = 1.0
            elif len(token) == 1 and other.startswith(token):
                score = 0.88
            elif len(other) == 1 and token.startswith(other):
                score = 0.88
            elif len(token) >= 3 and len(other) >= 3:
                score = _sequence_similarity(token, other)
                if score < 0.82:
                    score = 0.0
            else:
                score = 0.0
            if score > best:
                best = score
                best_index = index
        if best_index is not None and best:
            matched += best
            used.add(best_index)

    token_score = matched / max(len(at), len(bt))
    char_score = _sequence_similarity(a, b)
    return max(token_score, char_score * 0.96)


def title_similarity(profile_a: EntityProfile, profile_b: EntityProfile) -> float:
    left = profile_a.normalized_title
    right = profile_b.normalized_title
    if not left or not right:
        return 0.0
    if left == right:
        return 1.0
    if profile_a.entity_type in {"Person", "Organization"} or (
        profile_b.entity_type in {"Person", "Organization"}
    ):
        return name_similarity(profile_a.record.title, profile_b.record.title)

    # Containment catches "Acme Ltd." vs "Acme Ltd. (official)" without
    # accepting short generic prefixes.
    short, long = (left, right) if len(left) <= len(right) else (right, left)
    if len(short) >= 4 and short in long:
        containment = len(short) / len(long)
        if containment >= 0.6:
            return max(0.9, containment)
    return _sequence_similarity(left, right)


def content_similarity(profile_a: EntityProfile, profile_b: EntityProfile) -> float:
    a = profile_a.content_text
    b = profile_b.content_text
    if not a or not b:
        return 0.0
    sa = set(a.split())
    sb = set(b.split())
    if not sa or not sb:
        return 0.0
    jaccard = len(sa & sb) / len(sa | sb)
    # Long shared blocks (e.g. the same address in two profile dumps) matter
    # more than scattered common words.
    seq = _sequence_similarity(a, b)
    return max(jaccard, seq)


def _identity_conflict(profile_a: EntityProfile, profile_b: EntityProfile) -> str:
    """Return a reason when two nodes are provably different entities."""
    etype = profile_a.entity_type
    if etype not in _UNIQUE_IDENTITY_TYPES:
        return ""
    # Same entity type with a populated identity space but no overlap.
    if (
        profile_a.strong_identifiers
        and profile_b.strong_identifiers
        and not (profile_a.strong_identifiers & profile_b.strong_identifiers)
    ):
        return "different " + etype.casefold() + " identifiers"
    return ""


def _shared_identifiers(
    profile_a: EntityProfile, profile_b: EntityProfile
) -> list[str]:
    return sorted(profile_a.strong_identifiers & profile_b.strong_identifiers)


@dataclass(frozen=True)
class EntityMatch:
    left_id: str
    right_id: str
    score: float
    auto: bool
    reasons: tuple[str, ...]
    shared_identifiers: tuple[str, ...] = ()
    conflict: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "left_id": self.left_id,
            "right_id": self.right_id,
            "score": round(float(self.score), 4),
            "auto": bool(self.auto),
            "reasons": list(self.reasons),
            "shared_identifiers": list(self.shared_identifiers),
            "conflict": self.conflict,
        }


def compare_profiles(
    profile_a: EntityProfile,
    profile_b: EntityProfile,
    config: ResolutionConfig = DEFAULT_CONFIG,
) -> EntityMatch | None:
    """Score two profiles, returning ``None`` when they cannot be the same."""
    if profile_a.entity_type != profile_b.entity_type:
        return None
    if not profile_a.normalized_title and not profile_a.identifiers:
        return None
    if not profile_b.normalized_title and not profile_b.identifiers:
        return None

    conflict = _identity_conflict(profile_a, profile_b)
    if conflict:
        return None

    shared = _shared_identifiers(profile_a, profile_b)
    title_score = title_similarity(profile_a, profile_b)
    content_score = content_similarity(profile_a, profile_b)

    if shared:
        # A shared strong identifier is the strongest possible signal.  A
        # different spelling of the title must not prevent the merge.
        score = 0.90 + 0.10 * title_score
        if len(shared) > 1:
            score += min(0.04, 0.01 * (len(shared) - 1))
        score = min(0.99, score)
        reasons = [f"shared {item}" for item in shared[:4]]
        if title_score >= 0.7:
            reasons.append("similar title")
        auto = score >= config.auto_threshold
    else:
        if title_score < config.min_title_similarity:
            return None
        score = (
            config.name_weight * title_score
            + config.content_weight * content_score
            + config.identifier_bonus
            * min(1.0, len(profile_a.identifiers & profile_b.identifiers) / 2.0)
        )
        # Exact normalised titles (and the same name in a different word order)
        # are a clean duplicate signal for safe types.
        same_tokens = bool(profile_a.tokens) and sorted(profile_a.tokens) == sorted(
            profile_b.tokens
        )
        if (
            profile_a.normalized_title == profile_b.normalized_title or same_tokens
        ) and profile_a.entity_type in _TITLE_AUTO_TYPES:
            score = max(score, 0.97 if content_score >= 0.25 else 0.955)
        reasons = []
        if title_score >= 0.99:
            reasons.append("identical normalised title")
        elif title_score >= 0.9:
            reasons.append(f"name/title similarity {title_score:.0%}")
        else:
            reasons.append(f"partial title similarity {title_score:.0%}")
        if content_score >= 0.4:
            reasons.append(f"content overlap {content_score:.0%}")
        common = sorted(profile_a.identifiers & profile_b.identifiers)
        if common:
            reasons.append(f"shared {common[0]}")
        # Automatic merging without a shared identifier stays restricted to
        # very high-confidence pairs, and never for free-form types.
        auto = bool(
            score >= config.auto_threshold
            and (title_score >= 0.98 or (title_score >= 0.94 and content_score >= 0.45))
            and profile_a.entity_type in _TITLE_AUTO_TYPES
        )

    score = max(0.0, min(1.0, score))
    if score < config.review_threshold:
        return None
    return EntityMatch(
        left_id=profile_a.record.id,
        right_id=profile_b.record.id,
        score=score,
        auto=auto,
        reasons=tuple(reasons),
        shared_identifiers=tuple(shared),
    )


# ---------------------------------------------------------------------------
# Candidate search and clustering
# ---------------------------------------------------------------------------


def _blocking_keys(profile: EntityProfile) -> set[str]:
    keys = {f"type:{profile.entity_type}"}
    for identifier in profile.identifiers:
        keys.add(f"id:{identifier}")
    tokens = profile.tokens
    for token in tokens[:6]:
        if len(token) >= 3:
            keys.add(f"tok:{token[:12]}")
    if profile.normalized_title:
        keys.add(f"pre:{profile.normalized_title[:5]}")
        keys.add(f"pre:{profile.normalized_title[-5:]}")
    return keys


def _candidate_pairs(
    profiles: list[EntityProfile], config: ResolutionConfig
) -> list[tuple[EntityProfile, EntityProfile]]:
    count = len(profiles)
    if count <= 1:
        return []
    # For small graphs every pair is affordable and finds the best matches.
    if count <= 400:
        return [
            (profiles[i], profiles[j])
            for i in range(count)
            for j in range(i + 1, count)
        ]

    buckets: dict[str, list[int]] = {}
    for index, profile in enumerate(profiles):
        for key in _blocking_keys(profile):
            buckets.setdefault(key, []).append(index)

    pairs: set[tuple[int, int]] = set()
    for members in buckets.values():
        if len(members) < 2 or len(members) > config.max_bucket_size:
            continue
        for offset, left in enumerate(members):
            for right in members[offset + 1 :]:
                pairs.add((left, right) if left < right else (right, left))
                if len(pairs) >= config.max_pairs:
                    break
            if len(pairs) >= config.max_pairs:
                break
        if len(pairs) >= config.max_pairs:
            break
    return [(profiles[i], profiles[j]) for i, j in pairs]


@dataclass
class DuplicateGroup:
    """A set of records that should be merged into one entity."""

    node_ids: tuple[str, ...]
    score: float
    auto: bool
    reasons: tuple[str, ...]
    primary_id: str
    aliases: tuple[str, ...]
    pairs: tuple[EntityMatch, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "node_ids": list(self.node_ids),
            "score": round(float(self.score), 4),
            "auto": bool(self.auto),
            "reasons": list(self.reasons),
            "primary_id": self.primary_id,
            "aliases": list(self.aliases),
            "pairs": [pair.as_dict() for pair in self.pairs],
        }


def _pick_primary(
    records: list[EntityRecord],
    profiles: dict[str, EntityProfile],
    degrees: dict[str, int] | None = None,
) -> str:
    degrees = degrees or {}

    def rank(record: EntityRecord) -> tuple:
        profile = profiles[record.id]
        return (
            degrees.get(record.id, 0),
            len(record.evidence),
            len(profile.identifiers),
            len(record.content or ""),
            record.title or "",
            record.id,
        )

    return max(records, key=rank).id


def _build_groups(
    profiles: dict[str, EntityProfile],
    matches: list[EntityMatch],
    config: ResolutionConfig,
    include_review: bool,
    degrees: dict[str, int] | None = None,
) -> list[DuplicateGroup]:
    threshold = config.review_threshold if include_review else config.auto_threshold
    eligible = [match for match in matches if match.score >= threshold]
    eligible.sort(key=lambda match: match.score, reverse=True)
    score_map = {
        tuple(sorted((match.left_id, match.right_id))): match for match in eligible
    }

    parent: dict[str, str] = {}

    def find(node_id: str) -> str:
        parent.setdefault(node_id, node_id)
        while parent[node_id] != node_id:
            parent[node_id] = parent[parent[node_id]]
            node_id = parent[node_id]
        return node_id

    clusters: dict[str, set[str]] = {}
    pair_records: dict[str, list[EntityMatch]] = {}

    def cluster_of(node_id: str) -> str:
        root = find(node_id)
        return root

    def can_join(cluster: set[str], node_id: str) -> bool:
        # Complete-link guard: every existing member must have an eligible
        # score with the new node, otherwise weak transitivity can chain
        # unrelated records into one cluster.
        for member in cluster:
            key = tuple(sorted((member, node_id)))
            score = score_map.get(key)
            if score is None or score.score < threshold:
                return False
        return True

    for match in eligible:
        left_root = cluster_of(match.left_id)
        right_root = cluster_of(match.right_id)
        if left_root == right_root:
            pair_records.setdefault(left_root, []).append(match)
            continue
        left_members = clusters.get(left_root, {match.left_id})
        right_members = clusters.get(right_root, {match.right_id})
        if can_join(left_members, match.right_id) and can_join(
            right_members, match.left_id
        ):
            parent[right_root] = left_root
            merged = left_members | right_members
            clusters[left_root] = merged
            clusters.pop(right_root, None)
            pair_records.setdefault(left_root, []).extend(
                pair_records.pop(right_root, [])
            )
            pair_records[left_root].append(match)

    groups: list[DuplicateGroup] = []
    for root, members in clusters.items():
        if len(members) < 2:
            continue
        group_matches = [
            match
            for match in eligible
            if match.left_id in members and match.right_id in members
        ]
        if not group_matches:
            continue
        min_score = min(match.score for match in group_matches)
        auto = (
            all(match.auto for match in group_matches)
            and min_score >= config.auto_threshold
        )
        reasons: list[str] = []
        for match in sorted(group_matches, key=lambda item: item.score, reverse=True):
            for reason in match.reasons:
                if reason not in reasons:
                    reasons.append(reason)
        records = [profiles[node_id].record for node_id in members]
        primary = _pick_primary(records, profiles, degrees)
        aliases = []
        for record in records:
            if record.title and record.title not in aliases:
                aliases.append(record.title)
        groups.append(
            DuplicateGroup(
                node_ids=tuple(sorted(members)),
                score=min_score,
                auto=auto,
                reasons=tuple(reasons),
                primary_id=primary,
                aliases=tuple(aliases),
                pairs=tuple(
                    sorted(group_matches, key=lambda item: item.score, reverse=True)
                ),
            )
        )
    groups.sort(key=lambda group: (group.auto, group.score), reverse=True)
    return groups


def find_duplicate_groups(
    records: Iterable[EntityRecord | dict[str, Any]],
    config: ResolutionConfig = DEFAULT_CONFIG,
    include_review: bool = True,
    degrees: dict[str, int] | None = None,
) -> list[DuplicateGroup]:
    """Find duplicate clusters in ``records``.

    ``include_review`` keeps medium-confidence pairs that need analyst review;
    set it to ``False`` to get only groups safe for automatic merging.
    """
    normalized_records = [
        record if isinstance(record, EntityRecord) else EntityRecord.from_dict(record)
        for record in records
        if (record.id if isinstance(record, EntityRecord) else record.get("id"))
    ]
    profiles = {record.id: build_profile(record) for record in normalized_records}
    by_type: dict[str, list[EntityProfile]] = {}
    for profile in profiles.values():
        by_type.setdefault(profile.entity_type, []).append(profile)

    matches: list[EntityMatch] = []
    for group_profiles in by_type.values():
        for left, right in _candidate_pairs(group_profiles, config):
            match = compare_profiles(left, right, config)
            if match is not None:
                matches.append(match)

    return _build_groups(profiles, matches, config, include_review, degrees)


def find_duplicate_groups_from_graph(
    graph: dict[str, Any],
    config: ResolutionConfig = DEFAULT_CONFIG,
    include_review: bool = True,
) -> list[DuplicateGroup]:
    """Find duplicates in a SkyFall graph dictionary, using live degrees."""
    records = [EntityRecord.from_dict(node) for node in graph.get("nodes", [])]
    degrees: dict[str, int] = {}
    for edge in graph.get("edges", []):
        source = str(edge.get("source", ""))
        target = str(edge.get("target", ""))
        degrees[source] = degrees.get(source, 0) + 1
        degrees[target] = degrees.get(target, 0) + 1
    return find_duplicate_groups(
        records, config=config, include_review=include_review, degrees=degrees
    )


# ---------------------------------------------------------------------------
# Merging
# ---------------------------------------------------------------------------


def _merge_text(primary: str, others: Iterable[str]) -> str:
    lines: list[str] = []
    seen: set[str] = set()
    for text in [primary, *others]:
        for line in str(text or "").splitlines():
            key = line.strip()
            if not key or key in seen:
                continue
            seen.add(key)
            lines.append(line.rstrip())
    return "\n".join(lines)


def merge_record_group(
    records: Iterable[EntityRecord | dict[str, Any]],
    group: DuplicateGroup,
    degrees: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Build the merged representation for one :class:`DuplicateGroup`.

    The return value contains the primary record fields plus provenance:
    ``aliases``, ``merged_from`` and a ``resolution`` metadata block.
    """
    by_id = {
        (
            record.id if isinstance(record, EntityRecord) else str(record.get("id", ""))
        ): (
            record
            if isinstance(record, EntityRecord)
            else EntityRecord.from_dict(record)
        )
        for record in records
    }
    members = [by_id[node_id] for node_id in group.node_ids if node_id in by_id]
    if not members:
        return {}
    profiles = {record.id: build_profile(record) for record in members}
    primary = (
        by_id.get(group.primary_id) or by_id[_pick_primary(members, profiles, degrees)]
    )
    others = [record for record in members if record.id != primary.id]

    aliases: list[str] = []
    for record in members:
        for alias in [record.title, *record.metadata.get("aliases", [])]:
            alias = str(alias or "").strip()
            if alias and alias not in aliases:
                aliases.append(alias)

    merged_from: list[dict[str, Any]] = []
    for record in others:
        merged_from.append(
            {
                "id": record.id,
                "title": record.title,
                "entity_type": record.entity_type,
                "content": record.content,
                "evidence": list(record.evidence),
                "metadata": dict(record.metadata),
            }
        )

    metadata = dict(primary.metadata)
    previous_aliases = list(metadata.get("aliases") or [])
    metadata["aliases"] = list(dict.fromkeys([*previous_aliases, *aliases]))
    metadata["merged_from"] = [
        *(metadata.get("merged_from") or []),
        *merged_from,
    ]
    metadata["resolution"] = {
        "score": round(float(group.score), 4),
        "reasons": list(group.reasons),
        "auto": bool(group.auto),
        "merged_at": datetime.now(UTC).isoformat(),
        "node_ids": list(group.node_ids),
    }

    evidence: list[str] = []
    for record in members:
        for item in record.evidence:
            if item and item not in evidence:
                evidence.append(item)

    return {
        "id": primary.id,
        "title": primary.title,
        "entity_type": primary.entity_type,
        "content": _merge_text(primary.content, (r.content for r in others)),
        "evidence": evidence,
        "metadata": metadata,
        "aliases": aliases,
        "merged_from": merged_from,
        "removed_ids": [record.id for record in others],
        "score": group.score,
        "reasons": list(group.reasons),
        "auto": group.auto,
    }


def merge_graph_dict(
    graph: dict[str, Any],
    groups: Iterable[DuplicateGroup | Iterable[str]],
    degrees: dict[str, int] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Apply duplicate groups to a graph dictionary.

    Returns ``(merged_graph, merge_reports)``.  Nodes and edges are copied, so
    the input graph remains untouched.
    """
    import copy

    result = copy.deepcopy(graph)
    records = [EntityRecord.from_dict(node) for node in result.get("nodes", [])]
    id_to_record = {record.id: record for record in records}
    if degrees is None:
        degrees = {}
        for edge in result.get("edges", []):
            source = str(edge.get("source", ""))
            target = str(edge.get("target", ""))
            degrees[source] = degrees.get(source, 0) + 1
            degrees[target] = degrees.get(target, 0) + 1

    normalized_groups: list[DuplicateGroup] = []
    for group in groups:
        if isinstance(group, DuplicateGroup):
            normalized_groups.append(group)
            continue
        ids = tuple(str(node_id) for node_id in group)
        if len(ids) < 2:
            continue
        present = [id_to_record[node_id] for node_id in ids if node_id in id_to_record]
        if len(present) < 2:
            continue
        profiles = {record.id: build_profile(record) for record in present}
        normalized_groups.append(
            DuplicateGroup(
                node_ids=tuple(sorted(record.id for record in present)),
                score=1.0,
                auto=False,
                reasons=("manual selection",),
                primary_id=_pick_primary(present, profiles, degrees),
                aliases=tuple(record.title for record in present if record.title),
            )
        )

    merged_reports: list[dict[str, Any]] = []
    removed_map: dict[str, str] = {}
    replacements: dict[str, dict[str, Any]] = {}
    for group in normalized_groups:
        report = merge_record_group(records, group, degrees)
        if not report:
            continue
        primary_id = report["id"]
        replacements[primary_id] = report
        for removed_id in report["removed_ids"]:
            removed_map[removed_id] = primary_id
        merged_reports.append(
            {
                "primary_id": primary_id,
                "removed_ids": report["removed_ids"],
                "score": report["score"],
                "auto": report["auto"],
                "reasons": report["reasons"],
                "aliases": report["aliases"],
            }
        )

    nodes: list[dict[str, Any]] = []
    for node in result.get("nodes", []):
        node_id = str(node.get("id", ""))
        if node_id in removed_map:
            continue
        if node_id in replacements:
            merged = replacements[node_id]
            node = {
                **node,
                "title": merged["title"],
                "content": merged["content"],
                "evidence": merged["evidence"],
                "metadata": merged["metadata"],
                "aliases": merged["aliases"],
                "merged_from": merged["merged_from"],
            }
        nodes.append(node)
    result["nodes"] = nodes

    edges: list[dict[str, Any]] = []
    seen_edges: set[tuple[str, str, str, str]] = set()
    for edge in result.get("edges", []):
        source = removed_map.get(
            str(edge.get("source", "")), str(edge.get("source", ""))
        )
        target = removed_map.get(
            str(edge.get("target", "")), str(edge.get("target", ""))
        )
        if not source or not target or source == target:
            continue
        relationship = str(edge.get("relationship_type", "") or "")
        label = str(edge.get("label", "") or "")
        key = (source, target, relationship, label)
        if key in seen_edges:
            continue
        seen_edges.add(key)
        edges.append({**edge, "source": source, "target": target})
    result["edges"] = edges
    return result, merged_reports


def auto_merge_graph_dict(
    graph: dict[str, Any],
    config: ResolutionConfig = DEFAULT_CONFIG,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Merge only groups that are safe to merge automatically."""
    groups = find_duplicate_groups_from_graph(
        graph, config=config, include_review=False
    )
    auto_groups = [group for group in groups if group.auto]
    return merge_graph_dict(graph, auto_groups)


def summarize_groups(groups: Iterable[DuplicateGroup]) -> dict[str, Any]:
    """Small JSON-friendly summary used by the bridge/UI status line."""
    items = list(groups)
    return {
        "groups": len(items),
        "records": sum(len(group.node_ids) for group in items),
        "auto_groups": sum(1 for group in items if group.auto),
        "review_groups": sum(1 for group in items if not group.auto),
        "items": [group.as_dict() for group in items],
    }


__all__ = [
    "DEFAULT_CONFIG",
    "DuplicateGroup",
    "EntityMatch",
    "EntityProfile",
    "EntityRecord",
    "ResolutionConfig",
    "auto_merge_graph_dict",
    "build_profile",
    "compare_profiles",
    "content_similarity",
    "extract_identifiers",
    "find_duplicate_groups",
    "find_duplicate_groups_from_graph",
    "merge_graph_dict",
    "merge_record_group",
    "name_similarity",
    "normalize_domain",
    "normalize_email",
    "normalize_hash",
    "normalize_ip",
    "normalize_name",
    "normalize_netblock",
    "normalize_phone",
    "normalize_text",
    "normalize_title",
    "normalize_url",
    "normalize_username",
    "summarize_groups",
    "title_similarity",
]
