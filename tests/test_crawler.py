import os
import unittest
import tempfile
import logging
from unittest.mock import patch, Mock
from recursive_crawler.recursive_crawler import RecursiveCrawler

class TestCrawler(unittest.TestCase):

    def setUp(self):
        # Disable logging during tests to avoid noise
        logging.disable(logging.CRITICAL)

    def tearDown(self):
        # Re-enable logging after tests
        logging.disable(logging.NOTSET)

    def generate_html_with_links(self, len_valid_links: int, len_invalid_links: int) -> str:
        html = "<html><body>"
        for i in range(len_valid_links):
            # check valid domain
            html += f"<a href='https://url-for-testing.com/start/page{i}'>Page {i}</a>"
        for i in range(len_invalid_links):
            # check invalid domain
            html += f"<a href='https://url-not-for-testing.com/page{i}'>Page {i}</a>"
        for i in range(len_invalid_links):
            # check subdomain
            html += f"<a href='https://not.url-for-testing.com/page{i}'>Page {i}</a>"
        for i in range(len_invalid_links):
            # check subdomain
            html += f"<a href='https://url-for-testing.com/page{i}'>Page {i}</a>"
        html += "</body></html>"
        return html

    @patch("recursive_crawler.recursive_crawler.requests.Session.get")
    def test_crawler(self, mock_get):
        len_valid_links = 30
        len_invalid_links = 20

        # Mock the requests response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = self.generate_html_with_links(len_valid_links, len_invalid_links)
        mock_get.return_value = mock_response

        with tempfile.TemporaryDirectory() as temp_dir:
            crawler = RecursiveCrawler(
                start_url="https://url-for-testing.com/start",
                output_dir=temp_dir,
                max_threads=1,
                max_retries=0,
                timeout=60,
                user_agent="test",
                proxy_file=None,
                log_level="DEBUG",
            )
            crawler.crawl()

            created_files = os.listdir(temp_dir)
            self.assertEqual(len(created_files), len_valid_links + 1)
            self.assertEqual(mock_get.call_count, len_valid_links + 1)

            mock_get.reset_mock()

            crawler = RecursiveCrawler(
                start_url="https://url-for-testing.com/start",
                output_dir=temp_dir,
                max_threads=1,
                max_retries=0,
                timeout=60,
                user_agent="test",
                proxy_file=None,
                log_level="DEBUG",
            )
            crawler.crawl()

            created_files = os.listdir(temp_dir)
            self.assertEqual(mock_get.call_count, 0)



if __name__ == "__main__":
    unittest.main()