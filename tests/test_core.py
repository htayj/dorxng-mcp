import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dorxng_mcp.core import SearchResult, normalize_servers, query_database, store_results


class CoreTests(unittest.TestCase):
    def test_normalize_servers_defaults_and_filters(self):
        self.assertEqual(normalize_servers(server="https://example/search"), ["https://example/search"])
        self.assertEqual(normalize_servers(servers=["", " https://one/search "]), ["https://one/search"])

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
