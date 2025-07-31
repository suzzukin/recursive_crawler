# Recursive Crawler

Recursive web crawler that downloads pages from child URLs only.

## Installation

```bash
pip install .
```

## Usage

### Basic

```bash
recursive-crawler --start-url https://example.com/path --output-dir ./output
```

### With Options

```bash
recursive-crawler \
  --start-url https://example.com/path \
  --output-dir ./output \
  --max-threads 20 \
  --max-retries 3 \
  --timeout 30 \
  --proxy-file proxies.txt \
  --log-level DEBUG
```

## Options

- `--start-url` - URL to start crawling (required)
- `--output-dir` - Directory to save pages (required)
- `--max-threads` - Concurrent threads (default: 10)
- `--max-retries` - Retry failed requests (default: 1)
- `--timeout` - Request timeout in seconds (default: 60)
- `--proxy-file` - File with proxies, one per line (optional)
- `--log-level` - Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL (default: INFO)

## URL Validation

Only crawls child URLs. For `https://example.com/path`:

- Valid: `https://example.com/path/sub`
- Invalid: `https://example.com/other`
- Invalid: `https://other.com`

## Requirements

- Python 3.9+
- beautifulsoup4
- requests
