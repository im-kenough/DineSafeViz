"""The search reference describes the count query and pagination (#353)."""
from helpers import ROOT

DOC = ROOT / "docs-new" / "ref" / "3-11-search.md"


def test_search_doc_describes_count_and_pages():
    text = DOC.read_text()
    for phrase in ("COUNT(DISTINCT establishment_id)", "`page`", "50 per page", "pager"):
        assert phrase in text
    for stale in ("Up to 50", "first 51", "51 IDs", "50+"):
        assert stale not in text
