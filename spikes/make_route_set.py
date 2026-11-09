# /// script
# requires-python = ">=3.11"
# dependencies = ["reportlab>=4.2", "pypdfium2>=4.30", "pillow>=10.4"]
# ///
"""Day 2 fixtures: tricky scanned pages plus a labelled page set for OCR routing.

Creates in data/messy/:
| File                        | Expected route | Why it's tricky                                                  |
|-----------------------------|----------------|------------------------------------------------------------------|
| scan_set.pdf (6 pages)      | ocr            | Manual pages turned into scans at light / medium / heavy damage  |
| scan_with_text_header.pdf   | ocr            | Real scan + a typed header/footer: ~200 native chars, body lost  |
| scan_with_bad_text_layer.pdf| ocr            | Real scan + an invisible, wrong OCR layer (~1,700 chars of junk) |

Then writes spikes/day2_route_set.json: every page with its expected route, category and (if any) truth text.
Real manual pages are labelled "native" because the manuals are born-digital (Sphinx/LaTeX). Labels are the
ground truth for routing accuracy, so read them and change any you disagree with (e.g. screenshot pages).

Usage: uv run spikes/make_route_set.py   (needs the Day 1 corpus, the Day 1 messy PDFs and your real scan)
"""

from __future__ import annotations

import io
import json
import random
from pathlib import Path

import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_c
from PIL import Image, ImageEnhance, ImageFilter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "pdf"
MESSY = ROOT / "data" / "messy"
TRUTH = MESSY / "truth"
REAL_SCAN = MESSY / "scanned-nextcloud-user-manual.pdf"
REAL_SCAN_TRUTH = TRUTH / "scanned-nextcloud-user-manual.txt"
SET_FILE = Path(__file__).resolve().parent / "day2_route_set.json"
SEED = 7

# (rotation degrees, blur radius, 1-in-N pixels of noise, contrast, render dpi)
DAMAGE = {"light": (0.5, 0.3, 400, 1.0, 200), "medium": (1.5, 0.8, 60, 0.85, 150), "heavy": (3.0, 1.3, 15, 0.6, 100)}


def page_features(page: pdfium.PdfPage) -> tuple[int, float]:
    """Non-space characters and the share of the page covered by image objects."""
    w, h = page.get_size()
    chars = len("".join(page.get_textpage().get_text_range().split()))
    area = 0.0
    for obj in page.get_objects(max_depth=3):
        if obj.type == pdfium_c.FPDF_PAGEOBJ_IMAGE:
            left, bottom, right, top = obj.get_bounds()
            area += max(0.0, right - left) * max(0.0, top - bottom)
    return chars, min(1.0, area / (w * h))


def degrade(img: Image.Image, level: str, rng: random.Random) -> Image.Image:
    rot, blur, noise_every, contrast, _ = DAMAGE[level]
    img = img.convert("L").rotate(rot * rng.choice((-1, 1)), expand=True, fillcolor=235)
    img = ImageEnhance.Contrast(img).enhance(contrast).filter(ImageFilter.GaussianBlur(blur))
    px = img.load()
    for _ in range(img.width * img.height // noise_every):
        px[rng.randrange(img.width), rng.randrange(img.height)] = rng.choice((30, 210))
    return img


def scan_set(user: pdfium.PdfDocument, pages: list[int]) -> list[dict]:
    rng = random.Random(SEED)
    images, entries = [], []
    for n, (idx, level) in enumerate(zip(pages, ["light", "light", "medium", "medium", "heavy", "heavy"])):
        dpi = DAMAGE[level][4]
        img = degrade(user[idx].render(scale=dpi / 72).to_pil(), level, rng)
        images.append(img)
        truth = TRUTH / f"scan_set_p{n + 1}.txt"
        truth.write_text(user[idx].get_textpage().get_text_range())
        entries.append(
            {"file": "data/messy/scan_set.pdf", "page": n, "expected": "ocr", "category": f"scan-{level}",
             "truth": str(truth.relative_to(ROOT)), "note": f"v35 user manual page index {idx}"}
        )
    images[0].save(MESSY / "scan_set.pdf", format="PDF", save_all=True, append_images=images[1:], resolution=150)
    return entries


def real_scan_image() -> tuple[Image.Image, float, float]:
    page = pdfium.PdfDocument(str(REAL_SCAN))[0]
    w, h = page.get_size()
    return page.render(scale=2).to_pil(), w, h


def scan_with_text_header() -> dict:
    img, w, h = real_scan_image()
    path = MESSY / "scan_with_text_header.pdf"
    c = canvas.Canvas(str(path), pagesize=(w, h))
    c.drawImage(ImageReader(img), 0, 0, width=w, height=h)
    c.setFont("Helvetica", 7)
    c.drawString(24, h - 14, "ACME Corp document archive - scanned 2026-11-05 - Nextcloud User Manual v35 - page 13 of 333")
    c.drawString(24, 10, "Scanned by ACME-MFP-3 at 300 dpi - batch 0042 - CONFIDENTIAL internal copy - do not distribute")
    c.save()
    return {"file": str(path.relative_to(ROOT)), "page": 0, "expected": "ocr", "category": "scan+text-header",
            "truth": str(REAL_SCAN_TRUTH.relative_to(ROOT)), "note": "typed header/footer as real text, body is an image"}


CONFUSABLE = {"h": "b", "l": "1", "I": "1", "e": "c", "o": "0", "n": "ri", "m": "rn", "a": "o", "t": "f"}


def corrupt(text: str, rng: random.Random) -> str:
    out = []
    for ch in text:
        if ch in CONFUSABLE and rng.random() < 0.2:
            out.append(CONFUSABLE[ch])
        elif ch == " " and rng.random() < 0.1:
            continue  # dropped space
        else:
            out.append(ch)
    return "".join(out)


def scan_with_bad_text_layer() -> dict:
    rng = random.Random(SEED)
    img, w, h = real_scan_image()
    path = MESSY / "scan_with_bad_text_layer.pdf"
    c = canvas.Canvas(str(path), pagesize=(w, h))
    c.drawImage(ImageReader(img), 0, 0, width=w, height=h)
    text = c.beginText(40, h - 60)
    text.setTextRenderMode(3)  # invisible: how scanners embed their OCR layer
    text.setFont("Helvetica", 9)
    for line in corrupt(REAL_SCAN_TRUTH.read_text(), rng).splitlines():
        text.textLine(line.strip())
    c.drawText(text)
    c.save()
    return {"file": str(path.relative_to(ROOT)), "page": 0, "expected": "ocr", "category": "scan+bad-text-layer",
            "truth": str(REAL_SCAN_TRUTH.relative_to(ROOT)), "note": "invisible OCR layer with ~20% confusable errors"}


def manual_pages() -> list[dict]:
    """Born-digital manual pages by category, sampled with a fixed seed."""
    rng = random.Random(SEED)
    entries = []
    for name, picks in (("v35_user_manual", {"body": 8, "screenshot": 6, "sparse": 4, "blank": 1}),
                        ("v35_admin_manual", {"body": 6, "screenshot": 2, "sparse": 2, "blank": 2})):
        doc = pdfium.PdfDocument(str(RAW / f"{name}.pdf"))
        buckets: dict[str, list[int]] = {k: [] for k in picks}
        for i in range(len(doc)):
            chars, img = page_features(doc[i])
            if chars < 20:
                buckets["blank"].append(i)
            elif img > 0.35 and chars < 300:
                buckets["screenshot"].append(i)
            elif chars < 300 and img < 0.1:
                buckets["sparse"].append(i)
            elif chars > 800 and img < 0.1:
                buckets["body"].append(i)
        for cat, k in picks.items():
            for i in sorted(rng.sample(buckets[cat], min(k, len(buckets[cat])))):
                entries.append({"file": f"data/raw/pdf/{name}.pdf", "page": i, "expected": "native",
                                "category": cat, "truth": None, "note": ""})
    return entries


def day1_messy() -> list[dict]:
    rows = [("synthetic_scan.pdf", 0, "ocr", "scan-synthetic", "synthetic_scan.txt"),
            ("scanned-nextcloud-user-manual.pdf", 0, "ocr", "scan-real", "scanned-nextcloud-user-manual.txt"),
            ("two_column.pdf", 0, "native", "two-column", None),
            ("two_column.pdf", 1, "native", "two-column", None),
            ("table_heavy.pdf", 0, "native", "table", None)]
    return [{"file": f"data/messy/{f}", "page": p, "expected": e, "category": c,
             "truth": f"data/messy/truth/{t}" if t else None, "note": "Day 1 fixture"} for f, p, e, c, t in rows]


def main() -> None:
    for need in (RAW / "v35_user_manual.pdf", REAL_SCAN, REAL_SCAN_TRUTH, MESSY / "synthetic_scan.pdf"):
        if not need.exists():
            raise SystemExit(f"missing {need}: run the Day 1 scripts first")
    user = pdfium.PdfDocument(str(RAW / "v35_user_manual.pdf"))
    body = [i for i in range(40, len(user)) if (f := page_features(user[i]))[0] > 1500 and f[1] < 0.05]
    entries = manual_pages() + day1_messy()
    entries += scan_set(user, random.Random(SEED).sample(body, 6))
    entries += [scan_with_text_header(), scan_with_bad_text_layer()]
    SET_FILE.write_text(json.dumps(entries, indent=2) + "\n")
    by_cat: dict[str, int] = {}
    for e in entries:
        by_cat[f"{e['expected']}/{e['category']}"] = by_cat.get(f"{e['expected']}/{e['category']}", 0) + 1
    print(f"{len(entries)} labelled pages -> {SET_FILE.relative_to(ROOT)}")
    for k, v in sorted(by_cat.items()):
        print(f"  {k:28s} {v}")


if __name__ == "__main__":
    main()
