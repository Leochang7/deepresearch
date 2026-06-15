from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from deepresearch.retrieval.fetcher import FetchResult, WebFetcher


def _mock_http_response(html: str) -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.text = html
    resp.raise_for_status = MagicMock()
    return resp


class TestWebFetcher:
    @pytest.fixture
    def fetcher(self):
        return WebFetcher(timeout=10.0, max_retries=0)

    @pytest.mark.asyncio
    async def test_fetch_extracts_text(self, fetcher):
        html = "<html><head><title>Test</title></head><body><p>Hello world</p></body></html>"
        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get.return_value = _mock_http_response(html)
            mock_cls.return_value = mock_client

            result = await fetcher.fetch("https://example.com")
            assert isinstance(result, FetchResult)
            assert result.url == "https://example.com"

    @pytest.mark.asyncio
    async def test_fetch_returns_failure_on_error(self, fetcher):
        with patch("httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get.side_effect = Exception("timeout")
            mock_cls.return_value = mock_client

            result = await fetcher.fetch("https://example.com")
            assert not result.success
            assert "timeout" in result.error

    @pytest.mark.asyncio
    async def test_fetch_result_fields(self, fetcher):
        assert FetchResult(url="u", title="t", content="c", success=True).success
        assert not FetchResult(url="u", title="", content="", success=False).success
