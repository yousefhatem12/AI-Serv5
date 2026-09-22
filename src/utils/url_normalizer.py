from __future__ import annotations

import re
from urllib.parse import urlsplit

_SCHEMELESS_WEB_URL = re.compile(
    r"^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}(?::\d{1,5})?(?:[/?#][^\s]*)?$",
    re.IGNORECASE,
)
_WEB_URL_CANDIDATE = re.compile(
    r"(?<![\w@])(?:https?://)?(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}(?::\d{1,5})?(?:[/?#][^\s<>'\"]*)?",
    re.IGNORECASE,
)


def normalize_web_url(value: object) -> str | None:
    """Return an explicit HTTP(S) web URL, adding HTTPS only to valid schemeless URLs."""
    if not isinstance(value, str):
        return None

    candidate = value.strip()
    if not candidate:
        return None

    parsed = urlsplit(candidate)
    if parsed.scheme:
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
            return None
        return candidate

    if not _SCHEMELESS_WEB_URL.fullmatch(candidate):
        return None

    normalized = f"https://{candidate}"
    parsed = urlsplit(normalized)
    return normalized if parsed.netloc else None


def extract_web_url_candidates(text: str) -> list[str]:
    """Find URL-shaped source tokens; callers must normalize each value before use."""
    if not text:
        return []
    return [match.group(0) for match in _WEB_URL_CANDIDATE.finditer(text)]
