from pathlib import Path

import httpx
import pytest

from scanner.fetchers import freelancermap

FIXTURES = Path(__file__).parent / "fixtures"


def _transport(pages: dict[int, str]):
    """Fake transport: page 1 returns `pages[1]`, everything else `pages["rest"]`."""

    def handler(request: httpx.Request) -> httpx.Response:
        query = dict(pair.split("=") for pair in request.url.query.decode().split("&") if pair)
        page = int(query.get("pagenr", "1"))
        html = pages.get(page, pages["rest"])
        return httpx.Response(200, text=html)

    return httpx.MockTransport(handler)


@pytest.fixture
def page1_html() -> str:
    return (FIXTURES / "freelancermap_page1.html").read_text(encoding="utf-8")


@pytest.fixture
def empty_html() -> str:
    return (FIXTURES / "freelancermap_empty.html").read_text(encoding="utf-8")


def test_fetch_parses_real_result_shape(page1_html, empty_html):
    transport = _transport({1: page1_html, "rest": empty_html})
    with httpx.Client(transport=transport) as client:
        postings = freelancermap.fetch(
            client, {"search_url": "https://www.freelancermap.de/projekte?query=x", "max_pages": 3}
        )

    assert len(postings) == 3
    first = postings[0]
    assert first.id == "freelancermap-3024636"
    assert first.portal == "freelancermap"
    assert first.contract_type == "contracting"
    assert first.remote_percent == 100
    assert first.company == "Formation Search GmbH"
    assert first.url.startswith("https://www.freelancermap.de/projekt/")
    assert "<div" not in first.posting_text  # HTML stripped


def test_fetch_stops_on_empty_page(empty_html):
    transport = _transport({"rest": empty_html})
    with httpx.Client(transport=transport) as client:
        postings = freelancermap.fetch(
            client, {"search_url": "https://www.freelancermap.de/projekte?query=x", "max_pages": 5}
        )

    assert postings == []
