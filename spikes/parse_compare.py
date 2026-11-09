# /// script
# requires-python = ">=3.11"
# dependencies = ["pypdfium2>=4.30", "pillow>=10.4", "rapidfuzz>=3.9", "pdfplumber>=0.11"]
# ///
"""Day 2 harness: OCR routing accuracy, OCR quality (CER), speed, text-quality scores and table cells.

Uses your route_page / text_quality from spikes/ocr_routing.py, or a naive baseline with --baseline N.
OCR = Tesseract 5 CLI (eng) on a 300 dpi render, one page at a time, as the worker will do on the VM.

Usage:
  uv run spikes/parse_compare.py                  # your functions
  uv run spikes/parse_compare.py --baseline 100   # "OCR if fewer than 100 non-space chars"
  uv run spikes/parse_compare.py --sweep          # baseline at several N, routing only (fast)
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
import time
from collections import defaultdict
from pathlib import Path

import pdfplumber
import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_c
from rapidfuzz.distance import Levenshtein

import ocr_routing as mine
from ocr_routing import PageInfo, Quality

ROOT = Path(__file__).resolve().parent.parent
SET_FILE = Path(__file__).resolve().parent / "day2_route_set.json"
OUT = Path(__file__).resolve().parent / "out"
TABLE_PDF = ROOT / "data" / "messy" / "table_heavy.pdf"
TABLE_TRUTH = ROOT / "data" / "messy" / "truth" / "table_heavy.json"
OCR_DPI = 300
OCR_TIMEOUT_S = 60


# --- page loading ---------------------------------------------------------------------------


def invisible_chars(page: pdfium.PdfPage, textpage: pdfium.PdfTextPage) -> int:
    n = 0
    for obj in page.get_objects(filter=[pdfium_c.FPDF_PAGEOBJ_TEXT], max_depth=3):
        if pdfium_c.FPDFTextObj_GetTextRenderMode(obj.raw) == pdfium_c.FPDF_TEXTRENDERMODE_INVISIBLE:
            size = pdfium_c.FPDFTextObj_GetText(obj.raw, textpage.raw, None, 0)  # UTF-16 bytes + terminator
            n += max(0, size // 2 - 1)
    return n


def page_info(page: pdfium.PdfPage) -> PageInfo:
    w, h = page.get_size()
    tp = page.get_textpage()
    boxes = tuple(
        tuple(obj.get_bounds()) for obj in page.get_objects(filter=[pdfium_c.FPDF_PAGEOBJ_IMAGE], max_depth=3)
    )
    return PageInfo(
        native_text=tp.get_text_range(), width_pt=w, height_pt=h, image_boxes=boxes, invisible_chars=invisible_chars(page, tp)
    )


def ocr(page: pdfium.PdfPage) -> tuple[str, float]:
    t0 = time.perf_counter()
    with tempfile.TemporaryDirectory() as tmp:
        png = Path(tmp) / "page.png"
        page.render(scale=OCR_DPI / 72, grayscale=True).to_pil().save(png)
        proc = subprocess.run(
            ["tesseract", str(png), "stdout", "-l", "eng", "--psm", "3"],
            capture_output=True, text=True, timeout=OCR_TIMEOUT_S,
        )
    if proc.returncode != 0:
        raise RuntimeError(f"tesseract failed: {proc.stderr.strip()[-200:]}")
    return proc.stdout, time.perf_counter() - t0


def cer(text: str, truth: str) -> float:
    """Character error rate after collapsing whitespace: edits needed / truth length. 0 = perfect."""
    a, b = " ".join(text.split()), " ".join(truth.split())
    return Levenshtein.distance(a, b) / max(1, len(b))


# --- routing strategies ------------------------------------------------------------------------


def baseline_route(n: int):
    return lambda info: "ocr" if len("".join(info.native_text.split())) < n else "native"


def no_quality(_text: str) -> Quality:
    return Quality(score=float("nan"), flags=["baseline: no quality check"])


# --- table cells ----------------------------------------------------------------------------------


def table_cell_accuracy() -> list[tuple[str, float]]:
    """Share of truth cells found in the right row, in order. Native text lines vs pdfplumber tables."""
    truth = json.loads(TABLE_TRUTH.read_text())
    rows = truth["plans"] + truth["retention"]
    total = sum(len(r) for r in rows)

    def score(extracted_rows: list[list[str]]) -> float:
        hit = 0
        for row in rows:
            best = 0
            for cand in extracted_rows:
                joined, pos, n = " | ".join(cand), 0, 0
                for cell in row:  # cells must appear left-to-right within one extracted row
                    i = joined.find(cell, pos)
                    if i >= 0:
                        n, pos = n + 1, i + len(cell)
                best = max(best, n)
            hit += best
        return hit / total

    native_lines = [[ln] for ln in pdfium.PdfDocument(str(TABLE_PDF))[0].get_textpage().get_text_range().splitlines()]
    with pdfplumber.open(TABLE_PDF) as pdf:
        tables = [[c or "" for c in r] for t in pdf.pages[0].extract_tables() for r in t]
    return [("pypdfium2 text, one line = one row", score(native_lines)), ("pdfplumber extract_tables()", score(tables))]


# --- main -----------------------------------------------------------------------------------------


def run(route, quality, do_ocr: bool) -> list[dict]:
    entries = json.loads(SET_FILE.read_text())
    docs: dict[str, pdfium.PdfDocument] = {}
    results = []
    for e in entries:
        doc = docs.setdefault(e["file"], pdfium.PdfDocument(str(ROOT / e["file"])))
        page = doc[e["page"]]
        info = page_info(page)
        t0 = time.perf_counter()
        decision = route(info)
        route_ms = (time.perf_counter() - t0) * 1000
        r = {**e, "decision": decision, "route_ms": route_ms, "native_chars": len("".join(info.native_text.split())),
             "image_coverage": info.image_coverage, "invisible_chars": info.invisible_chars, "ocr_s": None,
             "cer_native": None, "cer_ocr": None, "cer_final": None}
        text = info.native_text
        truth = (ROOT / e["truth"]).read_text() if e.get("truth") else None
        if do_ocr and (decision == "ocr" or truth is not None):
            ocr_text, r["ocr_s"] = ocr(page)
            if decision == "ocr":
                text = ocr_text
            if truth is not None:
                r["cer_ocr"] = cer(ocr_text, truth)
        if truth is not None:
            r["cer_native"] = cer(info.native_text, truth)
            r["cer_final"] = cer(text, truth) if (decision == "native" or do_ocr) else None
        q = quality(text)
        r["q_score"], r["q_flags"] = q.score, q.flags
        status = getattr(mine, "page_status", None)
        r["status"] = status(decision, info, q, text) if status and quality is not no_quality else None
        results.append(r)
    return results


def report(results: list[dict], label: str, quality_min: float | None) -> str:
    lines = [f"## {label}", ""]
    n = len(results)
    correct = sum(r["decision"] == r["expected"] for r in results)
    missed = [r for r in results if r["expected"] == "ocr" and r["decision"] != "ocr"]
    wasted = [r for r in results if r["expected"] == "native" and r["decision"] == "ocr"]
    lines += [
        f"**Routing:** {correct}/{n} correct ({correct / n:.0%}). "
        f"Missed scans (silent loss): **{len(missed)}**. Needless OCR: **{len(wasted)}**.", "",
        "| Category | Expected | Pages | Routed correctly | Mean native chars | Mean image cover | Mean quality score |",
        "|---|---|---|---|---|---|---|",
    ]
    by = defaultdict(list)
    for r in results:
        by[(r["expected"], r["category"])].append(r)
    for (exp, cat), rs in sorted(by.items()):
        qs = [r["q_score"] for r in rs if r["q_score"] == r["q_score"]]  # drop NaN
        lines.append(
            f"| {cat} | {exp} | {len(rs)} | {sum(r['decision'] == exp for r in rs)}/{len(rs)} "
            f"| {sum(r['native_chars'] for r in rs) / len(rs):.0f} | {sum(r['image_coverage'] for r in rs) / len(rs):.2f} "
            f"| {sum(qs) / len(qs):.2f} |" if qs else
            f"| {cat} | {exp} | {len(rs)} | {sum(r['decision'] == exp for r in rs)}/{len(rs)} "
            f"| {sum(r['native_chars'] for r in rs) / len(rs):.0f} | {sum(r['image_coverage'] for r in rs) / len(rs):.2f} | – |"
        )
    truth_rows = [r for r in results if r["cer_native"] is not None]
    if truth_rows:
        lines += ["", "**Pages with ground truth** (CER = character error rate, lower is better):", "",
                  "| Page | Category | Routed | CER native | CER OCR | CER final | OCR s | Quality | Flags |",
                  "|---|---|---|---|---|---|---|---|---|"]
        for r in truth_rows:
            f = lambda v: "–" if v is None else f"{v:.3f}"  # noqa: E731
            q = "–" if r["q_score"] != r["q_score"] else f"{r['q_score']:.2f}"
            lines.append(
                f"| {Path(r['file']).name} p{r['page']} | {r['category']} | {r['decision']} | {f(r['cer_native'])} "
                f"| {f(r['cer_ocr'])} | {f(r['cer_final'])} | {f(r['ocr_s'])} | {q} | {'; '.join(r['q_flags'])[:70]} |"
            )
    ocr_times = sorted(r["ocr_s"] for r in results if r["ocr_s"])
    if ocr_times:
        lines += ["", f"**OCR speed (mac):** {len(ocr_times)} pages, median {ocr_times[len(ocr_times) // 2]:.1f} s/page, "
                  f"max {ocr_times[-1]:.1f} s/page."]
    skipped = [r for r in results if (r.get("status") or "").startswith("skipped")]
    if skipped:
        lines += ["", "**Skipped (blank pages, not failures):** " + ", ".join(f"{Path(r['file']).name} p{r['page']}" for r in skipped)]
    if quality_min is not None:
        failed = [r for r in results if (r.get("status") or "").startswith("failed")
                  or (r.get("status") is None and r["q_score"] == r["q_score"] and r["q_score"] < quality_min)]
        lines += ["", f"**Would be marked Failed** (QUALITY_MIN = {quality_min}): "
                  + (", ".join(f"{Path(r['file']).name} p{r['page']} ({r['category']}: {r.get('status') or 'low score'})"
                               for r in failed) or "none")]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", type=int, help="use the naive rule: OCR if fewer than N non-space chars")
    ap.add_argument("--sweep", action="store_true", help="routing-only table for the baseline at several N")
    args = ap.parse_args()
    if not shutil.which("tesseract"):
        raise SystemExit("tesseract not found: brew install tesseract")
    OUT.mkdir(exist_ok=True)

    if args.sweep:
        print("| N (OCR if < N chars) | Correct | Missed scans | Needless OCR |\n|---|---|---|---|")
        for n in (20, 50, 100, 200, 300, 500, 1000, 2000):
            rs = run(baseline_route(n), no_quality, do_ocr=False)
            print(f"| {n} | {sum(r['decision'] == r['expected'] for r in rs)}/{len(rs)} "
                  f"| {sum(r['expected'] == 'ocr' and r['decision'] != 'ocr' for r in rs)} "
                  f"| {sum(r['expected'] == 'native' and r['decision'] == 'ocr' for r in rs)} |")
        return

    if args.baseline is not None:
        results = run(baseline_route(args.baseline), no_quality, do_ocr=True)
        text = report(results, f"Baseline: OCR if < {args.baseline} chars", None)
        name = f"day2_baseline_{args.baseline}.md"
    else:
        results = run(mine.route_page, mine.text_quality, do_ocr=True)
        text = report(results, "Your route_page + text_quality", mine.QUALITY_MIN)
        name = "day2_mine.md"
    text += "\n\n**Table cell accuracy** (table_heavy.pdf, 2 tables, 50 cells):\n\n| Extractor | Cells in the right row |\n|---|---|\n"
    text += "\n".join(f"| {k} | {v:.0%} |" for k, v in table_cell_accuracy())
    (OUT / name).write_text(text + "\n")
    print(text)
    print(f"\nsaved -> spikes/out/{name}")


if __name__ == "__main__":
    main()
