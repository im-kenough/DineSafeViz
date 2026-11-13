"""The search reference describes the count query and pagination (#353)."""
from helpers import ROOT

DOC = ROOT / "docs-new" / "ref" / "3-11-search.md"


def test_search_doc_describes_count_and_pages():
    text = DOC.read_text()
    for phrase in ("COUNT(DISTINCT establishment_id)", "`page`", "50 per page", "pager"):
        assert phrase in text
    for stale in ("Up to 50", "first 51", "51 IDs", "50+"):
        assert stale not in text


def test_search_doc_describes_the_map():
    text = DOC.read_text()
    for phrase in ("## Map", "SEARCH_MAP_LIMIT", "1,000", "tile.openstreetmap.org", "IP address"):
        assert phrase in text
    assert "filters, or maps" not in text


def test_search_doc_describes_the_restaurant_map():
    text = " ".join(DOC.read_text().split())
    assert "restaurant page shows a map with one pin" in text
    assert "newest row that has coordinates" in text
    assert "`establishment_pin()`" in text
