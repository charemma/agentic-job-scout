from pathlib import Path

from scanner.fetchers import freelancermap

FIXTURES = Path(__file__).parent / "fixtures"


def _results(html: str) -> list[dict]:
    return freelancermap._extract_results(html)


def test_extract_results_parses_real_result_shape():
    html = (FIXTURES / "freelancermap_page1.html").read_text(encoding="utf-8")
    raw_items = _results(html)
    assert len(raw_items) == 3

    first = freelancermap._to_posting(raw_items[0])
    assert first.id == "freelancermap-3024636"
    assert first.portal == "freelancermap"
    assert first.contract_type == "contracting"
    assert first.remote_percent == 100
    assert first.company == "Formation Search GmbH"
    assert first.url.startswith("https://www.freelancermap.de/projekt/")
    assert "<div" not in first.posting_text  # HTML stripped


def test_extract_results_returns_empty_list_for_empty_page():
    html = (FIXTURES / "freelancermap_empty.html").read_text(encoding="utf-8")
    assert _results(html) == []
