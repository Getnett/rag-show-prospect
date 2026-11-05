# /// script
# requires-python = ">=3.11"
# dependencies = ["pypdf[crypto]>=5.0"]  # [crypto]: without it, AES-encrypted PDFs fail with DependencyError
# ///
"""Day 1 break-it: feed PDFs to the most naive parser (pypdf extract_text, no checks) and classify what happens.

Each file is parsed in a child process with a timeout so a hang is observed, not suffered.
Outcomes: ok / error / empty / garbage? / hang. "garbage?" is a rough heuristic (share of tokens
that look like words), not a verdict: Day 2 measures OCR quality properly.

Usage: uv run spikes/naive_parse.py [--timeout 120] [files...]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FILES = [
    "data/raw/pdf/v35_user_manual.pdf",  # clean baseline
    "data/messy/two_column.pdf",
    "data/messy/table_heavy.pdf",
    "data/messy/password_user.pdf",
    "data/messy/password_owner_only.pdf",
    "data/messy/oversized.pdf",
    "data/messy/synthetic_scan.pdf",
]

CHILD = r"""
import json, resource, sys, time
from pypdf import PdfReader
t0 = time.perf_counter()
out = {"pages": None, "chars": 0, "text_sample": "", "error": None}
try:
    reader = PdfReader(sys.argv[1])
    out["pages"] = len(reader.pages)
    text = "".join((p.extract_text() or "") for p in reader.pages)
    out["chars"] = len(text.strip())
    out["text_sample"] = text[:20000]
except Exception as exc:
    out["error"] = f"{type(exc).__name__}: {exc}"
out["seconds"] = round(time.perf_counter() - t0, 2)
rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
out["peak_rss_mb"] = round(rss / (1024 * 1024 if sys.platform == "darwin" else 1024), 1)
print(json.dumps(out))
"""

WORD = re.compile(r"^[A-Za-z][A-Za-z'\-]{1,19}[.,:;]?$")  # a plausible English word, 2-20 letters
GLUED = re.compile(r"^[A-Za-z,()'\-]{25,}$")  # letters-only run of 25+ chars: words with the spaces lost


def word_ratio(text: str) -> float:
    tokens = text.split()
    return sum(bool(WORD.match(t)) for t in tokens) / len(tokens) if tokens else 0.0


def glued_share(text: str) -> float:
    tokens = text.split()
    return sum(bool(GLUED.match(t)) for t in tokens) / len(tokens) if tokens else 0.0


def classify(res: dict) -> str:
    if res.get("hang"):
        return "hang"
    if res["error"]:
        return "error"
    pages = res["pages"] or 1
    if res["chars"] / pages < 20:
        return "empty"
    if word_ratio(res["text_sample"]) < 0.5 or glued_share(res["text_sample"]) > 0.02:
        return "garbage?"
    return "ok"


def run(path: Path, timeout: int) -> dict:
    t0 = time.perf_counter()
    try:
        # -I: isolated mode, so nothing next to the (untrusted) file can be imported.
        proc = subprocess.run(
            [sys.executable, "-I", "-c", CHILD, str(path)], capture_output=True, text=True, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        return {"pages": None, "chars": 0, "error": None, "hang": True, "seconds": float(timeout), "peak_rss_mb": None}
    if proc.returncode != 0:
        return {"pages": None, "chars": 0, "error": f"crashed: {proc.stderr.strip()[-200:]}", "seconds": round(time.perf_counter() - t0, 2), "peak_rss_mb": None, "text_sample": ""}
    return json.loads(proc.stdout)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*", default=DEFAULT_FILES)
    ap.add_argument("--timeout", type=int, default=120)
    args = ap.parse_args()

    print("| File | MB | Pages | Outcome | Chars/page | Word ratio | Glued % | Seconds | Peak RSS MB | Detail |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for f in args.files:
        path = (ROOT / f) if not Path(f).is_absolute() else Path(f)
        res = run(path, args.timeout)
        outcome = classify(res)
        cpp = round(res["chars"] / res["pages"]) if res.get("pages") else "-"
        sample = res.get("text_sample", "")
        ratio = f"{word_ratio(sample):.2f}" if sample else "-"
        glued = f"{glued_share(sample) * 100:.1f}" if sample else "-"
        detail = (res["error"] or "")[:80] or ("timed out" if res.get("hang") else "")
        print(
            f"| {path.name} | {path.stat().st_size / 1e6:.1f} | {res.get('pages') or '-'} | **{outcome}** | {cpp} | {ratio} | {glued} "
            f"| {res['seconds']} | {res.get('peak_rss_mb') or '-'} | {detail} |"
        )


if __name__ == "__main__":
    main()
