import argparse

from bs4 import BeautifulSoup

# TODO: add logging
# TODO: add progress bar
# TODO: add error handling
# TODO: add ^C support
# TODO: add tests
# TODO: add documentation


class Crawler:
    def __init__(
        self,
        start_url: str,
        output_dir: str,
        max_branch_depth: int,
        max_concurrency: int,
        max_retries: int,
        timeout: int,
        user_agent: str,
        proxy: str,
    ):
        self.start_url = start_url
        # TODO: check dir exists
        self.output_dir = output_dir
        self.max_branch_depth = max_branch_depth
        self.max_concurrency = max_concurrency
        self.max_retries = max_retries
        self.timeout = timeout
        self.user_agent = user_agent
        self.proxy = proxy

    def crawl(self):
        pass


if __name__ == "__main__":
    args = argparse.ArgumentParser()
    args.add_argument("--start-url", type=str, required=True)
    args.add_argument("--output-dir", type=str, required=True)
    args.add_argument(
        "--max-branch-depth", type=int, required=False, default=-1
    )
    args.add_argument(
        "--max-concurrency", type=int, required=False, default=10
    )
    args.add_argument("--max-retries", type=int, required=False, default=3)
    args.add_argument("--timeout", type=int, required=False, default=10)
    args.add_argument(
        "--user-agent",
        type=str,
        required=False,
        default=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                 "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
    )
    args.add_argument("--proxy", type=str, required=False, default=None)
    args = args.parse_args()

    print(args)
