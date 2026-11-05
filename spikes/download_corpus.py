# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Download the Week 0 demo corpus into data/raw/.

- Nextcloud User + Admin manual PDFs: v35 (stable) and v33 (for the conflicting-docs test).
- A polite crawl of up to N HTML pages under /server/stable/ (the only path robots.txt allows).

Every file is recorded in data/raw/manifest.json with its URL, sha256, size and license.
Licence: Nextcloud documentation is CC BY 3.0 (attribution required).

Usage: uv run spikes/download_corpus.py [--max-pages 100]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.parse
import urllib.request
import urllib.robotparser
from collections import deque
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path

BASE = "https://docs.nextcloud.com"
USER_AGENT = "rag-show-corpus-fetch/0.1 (portfolio spike)"
LICENSE = "CC BY 3.0, Nextcloud GmbH and contributors"
OUT = Path(__file__).resolve().parent.parent / "data" / "raw"

PDFS = {
    "v35_user_manual.pdf": "/server/stable/Nextcloud_User_Manual.pdf",
    "v35_admin_manual.pdf": "/server/stable/Nextcloud_Server_Administration_Manual.pdf",
    # Not crawled: two direct file downloads for the v33-vs-v35 conflict test.
    "v33_user_manual.pdf": "/server/33/Nextcloud_User_Manual.pdf",
    "v33_admin_manual.pdf": "/server/33/Nextcloud_Server_Administration_Manual.pdf",
}
CRAWL_SEEDS = ["/server/stable/user_manual/en/", "/server/stable/admin_manual/"]
CRAWL_PREFIX = "/server/stable/"
DELAY_S = 1.0  # one request per second
TIMEOUT_S = 60
MAX_HTML_BYTES = 5 * 1024 * 1024


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append(href)


def fetch(url: str, max_bytes: int | None = None) -> tuple[bytes, str]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
        final_url = resp.geturl()
        # Redirects must stay on the same host (a cheap SSRF-style guard, see F13).
        if urllib.parse.urlparse(final_url).netloc != urllib.parse.urlparse(BASE).netloc:
            raise RuntimeError(f"redirected off-site to {final_url}")
        data = resp.read(max_bytes + 1 if max_bytes else -1)
        if max_bytes and len(data) > max_bytes:
            raise RuntimeError(f"response larger than {max_bytes} bytes")
        return data, final_url


def normalize(base_url: str, href: str) -> str | None:
    url = urllib.parse.urljoin(base_url, href)
    parts = urllib.parse.urlparse(url)._replace(fragment="", query="")
    if parts.scheme != "https" or parts.netloc != "docs.nextcloud.com":
        return None
    if not parts.path.startswith(CRAWL_PREFIX) or not parts.path.endswith((".html", "/")):
        return None
    return urllib.parse.urlunparse(parts)


def record(manifest: list[dict], path: Path, url: str, kind: str, data: bytes) -> None:
    manifest.append(
        {
            "file": str(path.relative_to(OUT)),
            "url": url,
            "kind": kind,
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "fetched_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "license": LICENSE,
        }
    )


def download_pdfs(manifest: list[dict]) -> None:
    for name, path in PDFS.items():
        target = OUT / "pdf" / name
        if target.exists():
            print(f"skip (exists)  {name}")
            data = target.read_bytes()
        else:
            data, _ = fetch(BASE + path)
            target.write_bytes(data)
            print(f"downloaded     {name}  {len(data) / 1e6:.1f} MB")
            time.sleep(DELAY_S)
        record(manifest, target, BASE + path, "pdf", data)


def crawl(manifest: list[dict], max_pages: int) -> None:
    robots = urllib.robotparser.RobotFileParser(BASE + "/robots.txt")
    robots.read()
    queue = deque(BASE + s for s in CRAWL_SEEDS)
    seen = set(queue)
    saved = 0
    while queue and saved < max_pages:
        url = queue.popleft()
        if not robots.can_fetch(USER_AGENT, url):
            print(f"robots.txt disallows {url}")
            continue
        try:
            data, final_url = fetch(url, MAX_HTML_BYTES)
        except Exception as exc:  # noqa: BLE001 - one bad page must not stop the crawl
            print(f"FAILED {url}: {exc}")
            continue
        rel = urllib.parse.urlparse(final_url).path.removeprefix(CRAWL_PREFIX)
        if rel.endswith("/") or rel == "":
            rel += "index.html"
        target = OUT / "html" / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        record(manifest, target, final_url, "html", data)
        saved += 1
        parser = LinkParser()
        parser.feed(data.decode("utf-8", errors="replace"))
        for href in parser.links:
            nxt = normalize(final_url, href)
            if nxt and nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
        time.sleep(DELAY_S)
    print(f"crawled {saved} HTML pages ({len(queue)} more links left unvisited)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-pages", type=int, default=100)
    args = ap.parse_args()
    (OUT / "pdf").mkdir(parents=True, exist_ok=True)
    (OUT / "html").mkdir(parents=True, exist_ok=True)
    manifest: list[dict] = []
    download_pdfs(manifest)
    crawl(manifest, args.max_pages)
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"manifest: {len(manifest)} files -> {OUT / 'manifest.json'}")


if __name__ == "__main__":
    main()
