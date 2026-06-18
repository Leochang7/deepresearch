import httpx

from deepresearch.llm.http import _retry_delay


def test_retry_delay_uses_retry_after_for_429():
    request = httpx.Request("POST", "https://example.com/v1/chat/completions")
    response = httpx.Response(429, request=request, headers={"Retry-After": "3"})
    error = httpx.HTTPStatusError("rate limited", request=request, response=response)

    assert _retry_delay(error, attempt=0) == 3.0


def test_retry_delay_backs_off_for_429_without_retry_after():
    request = httpx.Request("POST", "https://example.com/v1/chat/completions")
    response = httpx.Response(429, request=request)
    error = httpx.HTTPStatusError("rate limited", request=request, response=response)

    assert _retry_delay(error, attempt=0) == 1.0
    assert _retry_delay(error, attempt=2) == 4.0
