#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import argparse
import requests
import random
import os
import threading
import logging
import signal
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin, quote
from typing import Set, Optional


# TODO: add random user agent
# TODO: more tests


class RecursiveCrawler:
    """Recursive crawler class.

    This class is used to crawl a website recursively.

    Args:
        start_url (str): The URL to start crawling from.
        output_dir (str): The path to the output directory.
        max_threads (int): The maximum number of concurrent threads.
        max_retries (int): The maximum number of retries for failed requests.
        timeout (int): The timeout for HTTP requests in seconds.
        user_agent (str): The user agent to use for requests.
        proxy_file (str): The path to the file containing the proxies.
        log_level (str): The logging level.

    Attributes:
        start_url (str): The URL to start crawling from.
        start_url_fqdn (str): The FQDN of the start URL.
        output_dir (str): The path to the output directory.
        existing_files (Set[str]): A set of existing files.
        max_threads (int): The maximum number of concurrent threads.
        max_retries (int): The maximum number of retries for failed requests.
        timeout (int): The timeout for HTTP requests in seconds.
        user_agent (str): The user agent to use for requests.
        proxy_file (str): The path to the file containing the proxies.
        crawled_urls (Set[str]): A set of crawled URLs.
    """

    def __init__(
        self,
        start_url: str,
        output_dir: str,
        max_threads: int,
        max_retries: int,
        timeout: int,
        user_agent: str,
        proxy_file: str,
        log_level: str = "INFO",
    ):
        self.logger = logging.getLogger(
            f"{__name__}.{self.__class__.__name__}"
        )
        self.logger.setLevel(getattr(logging, log_level.upper()))
        self.start_url = start_url
        self.output_dir = self.check_dir_exists(output_dir)
        self.existing_files = self._get_existing_files(output_dir)
        self.max_threads = max_threads
        self.max_retries = max_retries
        self.timeout = timeout
        self.user_agent = user_agent
        self.proxy_file = proxy_file
        self.crawled_urls = set()
        self.pending_urls = set()
        self.urls_lock = threading.Lock()
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.user_agent})
        self.proxies = set()
        self.invalid_proxies = set()
        self.proxy_lock = threading.Lock()

        # Graceful shutdown support
        self.shutdown_event = threading.Event()

        # Setup logging

        # Create console handler with formatting
        if not self.logger.handlers:
            console_handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - [Thread-%(thread)d] - %(message)s"
            )
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

        if proxy_file:
            with open(proxy_file, "r") as f:
                self.proxies = set(f.read().splitlines())
            self.logger.info(
                f"Loaded {len(self.proxies)} proxies from {proxy_file}"
            )

        self.logger.info(f"Initialized crawler for {start_url}")
        self.logger.info(f"Output directory: {output_dir}")
        self.logger.info(f"Max threads: {max_threads}")
        self.logger.info(f"Max retries: {max_retries}")
        self.logger.info(f"Timeout: {timeout}s")

    def check_dir_exists(self, output_dir: str) -> str:
        """Check if the output directory exists.

        Args:
            output_dir (str): The path to the output directory.

        Returns:
            str: The path to the output directory.
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        return output_dir

    def _get_existing_files(self, output_dir: str) -> Set[str]:
        """Get the existing files in the output directory.

        Args:
            output_dir (str): The path to the output directory.

        Returns:
            Set[str]: A set of existing files.
        """
        try:
            return set(os.listdir(output_dir))
        except OSError as e:
            self.logger.error(
                f"Failed to get existing files from {output_dir}: {e}", exc_info=True)
            return set()

    def _write_page(self, filename: str, page: str) -> None:
        """Write the page content to a file.

        Args:
            filename (str): The sanitized filename for the page.
            page (str): The page content to write.
        """
        if self.shutdown_event.is_set():
            return

        filepath = os.path.join(self.output_dir, filename)
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(page)
            self.logger.debug(f"Saved page: {filename} ({len(page)} chars)")
        except Exception as e:
            self.logger.error(f"Failed to save page {filename}: {e}")

    def _get_proxy(self) -> Optional[str]:
        """Get a random proxy from the list of proxies.

        Returns:
            Optional[str]: A random proxy if available, None otherwise.
        """
        with self.proxy_lock:
            if self.proxies:
                proxy = random.choice(list(self.proxies))
                self.logger.debug(f"Using proxy: {proxy}")
                return proxy
            else:
                return None

    def _sanitize_url(self, url: str) -> str:
        """Sanitize a URL.

        This function is used to sanitize the URL to be used as a filename.
        Example:
            >>> inst._sanitize_url("https://www.example.com/path?query=value")
            "www.example.com%2Fpath%3Fquery%3Dvalue"

        Args:
            url (str): The URL to sanitize.

        Returns:
            str: The sanitized URL.
        """
        return quote(url.split("://", 1)[-1], safe="")

    def _get_page(self, url: str) -> Optional[str]:
        """Get the page content for a given URL.

        Args:
            url (str): The URL to get the page content for.

        Returns:
            Optional[str]: The page content if successful, None otherwise.
        """
        for attempt in range(self.max_retries + 1):
            if self.shutdown_event.is_set():
                return None

            proxy = self._get_proxy()
            proxies = {"http": proxy, "https": proxy} if proxy else None

            try:
                self.logger.debug(
                    f"Fetching {url} (attempt {attempt + 1}/{self.max_retries + 1})"
                )
                response = self.session.get(
                    url, timeout=self.timeout, proxies=proxies
                )
                if response.status_code == 200:
                    self.logger.debug(
                        f"Successfully fetched {url} ({len(response.text)} chars)"
                    )
                    return response.text
                else:
                    self.logger.warning(
                        f"HTTP {response.status_code} for {url}"
                    )
                    return None
            except Exception as e:
                self.logger.warning(
                    f"Attempt {attempt + 1} failed for {url}: {e}"
                )
                if attempt == self.max_retries:
                    self.logger.error(f"All attempts failed for {url}")
                    return None

                # Remove failed proxy
                if proxy:
                    with self.proxy_lock:
                        self.invalid_proxies.add(proxy)
                        self.proxies.discard(proxy)
                        self.logger.debug(f"Removed failed proxy: {proxy}")
        return None

    def _process_url(self, url: str) -> Set[str]:
        """Process a single URL.

        Args:
            url (str): The URL to process.
        Returns:
            Set[str]: A set of new URLs to crawl.
        """
        if self.shutdown_event.is_set():
            return set()

        # Check if already processed
        with self.urls_lock:
            if (
                url in self.crawled_urls
                or self._sanitize_url(url) in self.existing_files
            ):
                self.logger.debug(f"URL already processed: {url}")
                return set()
            self.crawled_urls.add(url)

        self.logger.info(f"Crawling: {url}")

        page = self._get_page(url)
        if not page:
            self.logger.warning(f"Failed to get page content: {url}")
            return set()

        # Save page
        self._write_page(self._sanitize_url(url), page)

        # Parse links from the page
        try:
            soup = BeautifulSoup(page, "html.parser")
            links = {
                l.get("href") for l in soup.find_all("a") if l.get("href")
            }
            self.logger.debug(f"Found {len(links)} links on {url}")
        except Exception as e:
            self.logger.error(f"Failed to parse HTML for {url}: {e}")
            return set()

        new_urls = set()
        with self.urls_lock:
            for link in links:
                if self.shutdown_event.is_set():
                    break

                # Convert relative URLs to absolute
                if 'http' not in link:
                    absolute_url = urljoin(url, link)
                else:
                    absolute_url = link
                # Only crawl URLs that are children of the start URL
                if not absolute_url.startswith(self.start_url):
                    self.logger.debug(f"Skipping non-child URL: {absolute_url}")
                    continue

                # Skip if already processed or pending
                if (
                    absolute_url not in self.crawled_urls
                    and absolute_url not in self.pending_urls
                ):
                    self.pending_urls.add(absolute_url)
                    new_urls.add(absolute_url)

        self.logger.info(f"Found {len(new_urls)} new URLs to crawl from {url}")
        return new_urls

    def crawl(self, link: str = None):
        if link is None:
            link = self.start_url

        urls_to_process = {link}

        self.logger.info(f"Starting crawl from {link}")

        try:
            with ThreadPoolExecutor(max_workers=self.max_threads) as executor:
                while urls_to_process and not self.shutdown_event.is_set():
                    batch_size = len(urls_to_process)
                    self.logger.info(f"Processing batch of {batch_size} URLs")

                    # Submit tasks for current batch of URLs
                    future_to_url = {
                        executor.submit(self._process_url, url): url
                        for url in urls_to_process
                    }

                    # Clear the current batch
                    urls_to_process = set()

                    # Process completed tasks and collect new URLs
                    for future in as_completed(future_to_url):
                        if self.shutdown_event.is_set():
                            # Cancel remaining futures
                            for f in future_to_url:
                                if not f.done():
                                    f.cancel()
                            break

                        try:
                            new_urls = future.result(timeout=1)
                            if new_urls and not self.shutdown_event.is_set():
                                urls_to_process.update(new_urls)
                        except Exception as e:
                            url = future_to_url[future]
                            self.logger.error(f"Error processing {url}: {e}")

                    if not self.shutdown_event.is_set():
                        with self.urls_lock:
                            processed_count = len(self.crawled_urls)
                        self.logger.info(
                            f"Batch completed. Processed: {processed_count} total URLs"
                        )

                        with self.urls_lock:
                            remaining_proxies = len(self.proxies)
                            invalid_proxies = len(self.invalid_proxies)

                        if self.proxies:
                            self.logger.info(
                                f"Proxy status: {remaining_proxies} active, {invalid_proxies} failed"
                            )

        except KeyboardInterrupt:
            # This shouldn't happen as we handle it in main(), but just in case
            self.shutdown_event.set()
            raise
        finally:
            self.logger.info(
                f"Crawl completed. Total URLs processed: {len(self.crawled_urls)}"
            )
            self.logger.info(
                f"Total unique URLs found: {len(self.crawled_urls)}"
            )


def signal_handler(signum, frame, crawler):
    """Handle SIGINT and SIGTERM signals."""
    crawler.logger.info("Received interrupt signal, initiating graceful shutdown...")
    crawler.shutdown_event.set()


def main():
    args = argparse.ArgumentParser(
        description="Recursive web crawler with concurrency support"
    )
    args.add_argument(
        "--start-url",
        type=str,
        required=True,
        help="URL to start crawling from",
    )
    args.add_argument(
        "--output-dir",
        type=str,
        required=True,
        help="Directory to save the crawled pages",
    )
    args.add_argument(
        "--max-threads",
        type=int,
        required=False,
        default=10,
        help="Maximum number of concurrent threads (default: 10)",
    )
    args.add_argument(
        "--max-retries",
        type=int,
        required=False,
        default=1,
        help="Maximum number of retries for failed requests (default: 1)",
    )
    args.add_argument(
        "--timeout",
        type=int,
        required=False,
        default=60,
        help="Timeout for HTTP requests in seconds (default: 60)",
    )
    args.add_argument(
        "--user-agent",
        type=str,
        required=False,
        default=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        help="User agent string to use for requests",
    )
    args.add_argument(
        "--proxy-file",
        type=str,
        required=False,
        default=None,
        help=(
            "Path to file containing list of proxies (one per line). "
            "If not provided, no proxies will be used. "
            "If any error occurs, this proxy will be excluded from use."
        ),
    )
    args.add_argument(
        "--log-level",
        type=str,
        required=False,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level (default: INFO)",
    )
    args = args.parse_args()

    # Setup root logging
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    crawler = RecursiveCrawler(
        start_url=args.start_url,
        output_dir=args.output_dir,
        max_threads=args.max_threads,
        max_retries=args.max_retries,
        timeout=args.timeout,
        user_agent=args.user_agent,
        proxy_file=args.proxy_file,
        log_level=args.log_level,
    )

    def handle_signal(signum, frame):
        signal_handler(signum, frame, crawler)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    # Run the crawler
    try:
        crawler.crawl()
    except KeyboardInterrupt:
        crawler.shutdown_event.set()
        # crawler._handle_shutdown()
        sys.exit(0)


if __name__ == "__main__":
    main()
