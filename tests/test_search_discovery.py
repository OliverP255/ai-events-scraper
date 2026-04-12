from __future__ import annotations

from ai_events.sources.search_discovery import _extract_duckduckgo_urls, _extract_google_urls


def test_extract_google_url_q_param() -> None:
    html = (
        '<html><body><a href="/url?q=https%3A%2F%2Fexample.com%2Fevent&sa=U">x</a></body></html>'
    )
    urls = _extract_google_urls(html, 10)
    assert urls
    assert urls[0].startswith("https://example.com/event")


def test_extract_duckduckgo_uddg_redirect() -> None:
    html = (
        '<a rel="nofollow" class="result__a" '
        'href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fluma.co%2Feb%2Fxyz">e</a>'
    )
    urls = _extract_duckduckgo_urls(html, 10)
    assert urls
    assert "luma.co" in urls[0]
