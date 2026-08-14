from pathlib import Path

from bs4 import BeautifulSoup

from scanner.fetchers import hays

FIXTURES = Path(__file__).parent / "fixtures"


def _blocks() -> list:
    html = (FIXTURES / "hays_page.html").read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")
    return soup.select(".search__result")


def test_to_posting_parses_real_result_shape():
    blocks = _blocks()
    assert len(blocks) == 2

    first = hays._to_posting(blocks[0])
    assert first.id == "hays-882526/1"
    assert first.portal == "hays"
    assert first.title == "Platform Engineer AI Security (m/w/d)"
    assert first.url.startswith("https://www.hays.de/jobsuche/stellenangebote-jobs-detail-")
    assert first.contract_type == "Festanstellung durch unseren Kunden"
    assert first.location == "Karlsruhe"
