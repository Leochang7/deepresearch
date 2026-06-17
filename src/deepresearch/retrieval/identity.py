from __future__ import annotations

import hashlib
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from deepresearch.schemas.evidence import RetrievedDocument

_TRACKING_QUERY_KEYS = {
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "ref",
    "source",
}


def content_fingerprint(content: str, *, length: int = 32) -> str:
    return hashlib.sha256(content.encode()).hexdigest()[:length]


def canonicalize_url(url: str) -> str:
    parsed = urlsplit(url.strip())
    scheme = parsed.scheme.lower()
    hostname = (parsed.hostname or "").lower()
    port = parsed.port
    if port and not (
        (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
    ):
        hostname = f"{hostname}:{port}"
    path = parsed.path.rstrip("/") or "/"
    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.lower().startswith("utm_")
        and key.lower() not in _TRACKING_QUERY_KEYS
    ]
    query.sort()
    return urlunsplit((scheme, hostname, path, urlencode(query), ""))


def document_key(doc: RetrievedDocument, *, include_content_hash: bool = False) -> str:
    content_hash = content_fingerprint(doc.content)
    if doc.url:
        url_key = canonicalize_url(doc.url)
        return (
            f"url:{url_key}:{content_hash}"
            if include_content_hash
            else f"url:{url_key}"
        )
    return f"title:{doc.title}:{content_hash}"
