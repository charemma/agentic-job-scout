from pathlib import Path

from scanner.fetchers import randstad

FIXTURES = Path(__file__).parent / "fixtures"


def _route_data(page_html: str) -> dict:
    return randstad._extract_route_data(page_html)


def test_extract_route_data_parses_real_result_shape():
    page_html = (FIXTURES / "randstad_page.html").read_text(encoding="utf-8")
    data = _route_data(page_html)
    hits = data["searchResults"]["hits"]["hits"]

    assert len(hits) == 2
    first = randstad._to_posting(hits[0]["_source"])
    assert first.id == "randstad-c01322436"
    assert first.portal == "randstad"
    assert first.title == "Platform Engineer AI Security (m/w/d)"
    assert first.url == "https://www.randstad.de/jobs/platform-engineer-ai-security-mwd_hannover_c01322436/"
    assert first.contract_type == "Festanstellung"
    assert first.company == "Acme Research GmbH"
    assert first.location == "Hannover, Niedersachsen"

    second = randstad._to_posting(hits[1]["_source"])
    assert second.company == "Randstad Deutschland"  # ClientName null -> falls back to agency name


def test_extract_route_data_returns_empty_dict_when_no_route_data():
    assert _route_data("<html></html>") == {}
