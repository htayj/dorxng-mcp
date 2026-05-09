import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dorxng_mcp.core import SearchResult, normalize_servers, query_database, store_results
from dorxng_mcp.dorking import suggest_dorks
from dorxng_mcp.safety import assert_no_illegal_sexual_material


class CoreTests(unittest.TestCase):
    def test_normalize_servers_defaults_and_filters(self):
        self.assertEqual(normalize_servers(server="https://example/search"), ["https://example/search"])
        self.assertEqual(normalize_servers(servers=["", " https://one/search "]), ["https://one/search"])

    def test_suggest_dorks_scopes_target_and_file_types(self):
        guidance = suggest_dorks(target="https://example.com/app/", objective="files", file_types=["pdf", ".xlsx"])
        self.assertEqual(guidance["target"], "example.com/app")
        queries = [template["query"] for template in guidance["templates"]]
        self.assertTrue(any("site:example.com/app" in query for query in queries))
        self.assertTrue(any("filetype:pdf" in query for query in queries))
        self.assertTrue(any("filetype:xlsx" in query for query in queries))

    def test_illegal_sexual_material_guardrail_blocks_minor_sexual_inputs(self):
        with self.assertRaises(ValueError):
            assert_no_illegal_sexual_material("underage explicit material")

    def test_illegal_sexual_material_guardrail_allows_ordinary_pentest_terms(self):
        assert_no_illegal_sexual_material("site:example.com filetype:pdf intitle:index of")
        assert_no_illegal_sexual_material("adult content policy")

    def test_store_and_query_database(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Path(tmpdir) / "dorxng.db"
            count = store_results(
                db,
                [
                    SearchResult(query="site:example.com", title="Example", url="https://example.com"),
                    SearchResult(query="site:example.com", title="Example", url="https://example.com"),
                    SearchResult(query="other", title="Other", url="https://other.test"),
                ],
            )
            self.assertEqual(count, 2)
            matches = query_database(db, "example")
            self.assertEqual(matches, [{"query": "site:example.com", "title": "Example", "url": "https://example.com"}])


if __name__ == "__main__":
    unittest.main()
