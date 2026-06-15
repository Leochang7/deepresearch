from __future__ import annotations

import hashlib
from dataclasses import dataclass

import httpx
import trafilatura


@dataclass
class FetchResult:
    url: str
    title: str
    content: str
    success: bool
    error: str = ""


class WebFetcher:
    def __init__(
        self,
        *,
        timeout: float = 20.0,
        max_retries: int = 2,
        user_agent: str = "DeepResearchAgent/0.1",
    ) -> None:
        self._timeout = timeout
        self._max_retries = max_retries
        self._user_agent = user_agent

    async def fetch(self, url: str) -> FetchResult:
        last_error: str = ""
        for attempt in range(self._max_retries + 1):
            try:
                async with httpx.AsyncClient(
                    timeout=self._timeout,
                    follow_redirects=True,
                    headers={"User-Agent": self._user_agent},
                ) as client:
                    resp = await client.get(url)
                    resp.raise_for_status()
                    html = resp.text

                text = trafilatura.extract(html, include_comments=False)
                if not text:
                    return FetchResult(
                        url=url,
                        title="",
                        content="",
                        success=False,
                        error="trafilatura returned empty content",
                    )

                title = ""
                doc = trafilatura.extract(
                    html, include_comments=False, output_format="xml"
                )
                if doc:
                    import re

                    title_match = re.search(r"<title>(.*?)</title>", doc)
                    if title_match:
                        title = title_match.group(1)

                return FetchResult(
                    url=url,
                    title=title,
                    content=text,
                    success=True,
                )
            except Exception as e:
                last_error = str(e)
                if attempt < self._max_retries:
                    continue

        return FetchResult(
            url=url,
            title="",
            content="",
            success=False,
            error=last_error,
        )


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()
