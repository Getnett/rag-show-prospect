# /// script
# requires-python = ">=3.11"
# dependencies = ["reportlab>=4.2", "pypdf[crypto]>=5.0", "pypdfium2>=4.30", "pillow>=10.4"]
# ///
"""Generate the deliberately messy test PDFs for Week 0 into data/messy/.

| File                       | What it tests                                                 |
|----------------------------|---------------------------------------------------------------|
| two_column.pdf             | reading order across columns (real manual text, re-laid out)  |
| table_heavy.pdf            | table extraction (synthetic "Acme Cloud" facts, known truth)  |
| password_user.pdf          | needs a password to open at all                               |
| password_owner_only.pdf    | permissions password only; opens without one                  |
| oversized.pdf              | 2,000 pages and ~50 MB: page/size limits, slowness, memory    |
| synthetic_scan.pdf         | image-only page (stand-in until your real phone scan arrives) |

Ground-truth text for the scan and the table goes to data/messy/truth/ (for CER and cell accuracy on Day 2).
The source manual is CC BY 3.0 (Nextcloud GmbH and contributors); the derived PDFs carry that attribution.

Usage: uv run spikes/make_messy_pdfs.py   (run download_corpus.py first)
"""

from __future__ import annotations

import io
import json
import random
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image, ImageFilter
from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageTemplate,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "data" / "raw" / "pdf" / "v35_user_manual.pdf"
OUT = ROOT / "data" / "messy"
TRUTH = OUT / "truth"
ATTRIBUTION = "Text: Nextcloud User Manual v35, CC BY 3.0, Nextcloud GmbH and contributors. Re-laid out for testing."
SYNTHETIC_NOTE = "Synthetic test document. Acme Cloud is a fictional company."
PASSWORD = "open-sesame"  # test value, not a secret: it only protects a generated test file
SEED = 42


def pick_text_pages(reader: PdfReader, start: int, count: int, min_chars: int = 2000) -> list[int]:
    """Indexes of the first `count` pages after `start` with enough body text."""
    picked = []
    for i in range(start, len(reader.pages)):
        if len((reader.pages[i].extract_text() or "").strip()) >= min_chars:
            picked.append(i)
            if len(picked) == count:
                break
    return picked


def page_paragraphs(pdf: pdfium.PdfDocument, index: int) -> list[str]:
    """Source text via pypdfium2: pypdf glues words together on this manual (Day 1 finding)."""
    raw = pdf[index].get_textpage().get_text_range().replace("\r", "")
    paras: list[str] = []
    for line in (ln.strip() for ln in raw.split("\n")):
        if not line:
            continue
        if not paras or line[0] in "•–-" or line.isdigit():
            paras.append(line)
        else:
            paras[-1] += " " + line
    return paras


def two_column(pdf: pdfium.PdfDocument, pages: list[int]) -> Path:
    styles = getSampleStyleSheet()
    path = OUT / "two_column.pdf"
    doc = BaseDocTemplate(str(path), pagesize=A4, title="Two-column test")
    w, h = A4
    gap, margin = 0.8 * cm, 1.8 * cm
    col_w = (w - 2 * margin - gap) / 2
    frames = [
        Frame(margin, margin, col_w, h - 2 * margin, id="left"),
        Frame(margin + col_w + gap, margin, col_w, h - 2 * margin, id="right"),
    ]

    def footer(canvas, _doc):
        canvas.setFont("Helvetica", 7)
        canvas.drawString(margin, 1 * cm, ATTRIBUTION)

    doc.addPageTemplates([PageTemplate(frames=frames, onPage=footer)])
    story = []
    for i in pages:
        for text in page_paragraphs(pdf, i):
            story.append(Paragraph(text.replace("&", "&amp;").replace("<", "&lt;"), styles["BodyText"]))
    doc.build(story)
    return path


TABLE_ROWS = [
    ["Plan", "Storage per user", "Max upload", "Max users", "Price / user / month", "Support response"],
    ["Starter", "50 GB", "2 GB", "10", "$4.00", "48 h (email)"],
    ["Team", "250 GB", "10 GB", "100", "$7.50", "24 h (email)"],
    ["Business", "1 TB", "25 GB", "500", "$12.00", "8 h (email, chat)"],
    ["Enterprise", "5 TB", "100 GB", "Unlimited", "Contact sales", "1 h (phone, 24/7)"],
]
RETENTION_ROWS = [
    ["Data type", "Starter", "Team", "Business", "Enterprise"],
    ["Deleted files (trash bin)", "7 days", "30 days", "90 days", "Configurable"],
    ["File versions", "5 versions", "20 versions", "50 versions", "Unlimited"],
    ["Audit log", "Not included", "30 days", "1 year", "7 years"],
    ["Backups", "Daily, 7 kept", "Daily, 14 kept", "Hourly, 30 days", "Custom"],
]


def table_heavy() -> Path:
    styles = getSampleStyleSheet()
    path = OUT / "table_heavy.pdf"
    doc = SimpleDocTemplate(str(path), pagesize=A4, title="Acme Cloud plans and limits")
    grid = TableStyle(
        [
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]
    )
    story = [
        Paragraph("Acme Cloud: plans and limits", styles["Title"]),
        Paragraph(SYNTHETIC_NOTE, styles["Italic"]),
        Spacer(1, 12),
        Paragraph("Table 1. Plans", styles["Heading2"]),
        Table(TABLE_ROWS, style=grid, repeatRows=1),
        Spacer(1, 18),
        Paragraph("Table 2. Retention by plan", styles["Heading2"]),
        Table(RETENTION_ROWS, style=grid, repeatRows=1),
        Spacer(1, 12),
        Paragraph(
            "Upload limits apply per file. Prices exclude VAT. Enterprise retention is set in the contract.",
            styles["BodyText"],
        ),
    ]
    doc.build(story)
    (TRUTH / "table_heavy.json").write_text(json.dumps({"plans": TABLE_ROWS, "retention": RETENTION_ROWS}, indent=2))
    return path


def password_variants(src: Path) -> list[Path]:
    user = OUT / "password_user.pdf"
    w = PdfWriter(clone_from=src)
    w.encrypt(user_password=PASSWORD, owner_password=PASSWORD + "-owner", algorithm="AES-256")
    w.write(user)

    owner = OUT / "password_owner_only.pdf"
    w = PdfWriter(clone_from=src)
    w.encrypt(user_password="", owner_password=PASSWORD + "-owner", algorithm="AES-256", permissions_flag=0)
    w.write(owner)
    return [user, owner]


def oversized(text_pages: int = 2000, image_pages: int = 50) -> Path:
    """Many pages plus incompressible images, so both page count and file size are large."""
    rng = random.Random(SEED)
    styles = getSampleStyleSheet()
    path = OUT / "oversized.pdf"
    doc = SimpleDocTemplate(str(path), pagesize=A4, title="Oversized test")
    filler = " ".join(["Lorem ipsum filler text for page-count testing."] * 30)
    story = []
    for i in range(text_pages):
        story.append(Paragraph(f"Page {i + 1}. {filler}", styles["BodyText"]))
        story.append(PageBreak())
    doc.build(story)

    # Append image-only pages filled with noise (JPEG can't compress noise much).
    w = PdfWriter(clone_from=path)
    for _ in range(image_pages):
        noise = Image.frombytes("RGB", (1400, 1400), rng.randbytes(1400 * 1400 * 3))
        buf = io.BytesIO()
        noise.save(buf, format="PDF", quality=95)
        w.append(PdfReader(io.BytesIO(buf.getvalue())))
    w.write(path)
    return path


def synthetic_scan(page_index: int) -> Path:
    """Render a real manual page to pixels, then rotate, blur and add noise like a phone photo."""
    rng = random.Random(SEED)
    pdf = pdfium.PdfDocument(str(SOURCE))
    page = pdf[page_index]
    truth = page.get_textpage().get_text_range()
    img = page.render(scale=150 / 72).to_pil().convert("L")
    img = img.rotate(1.5, expand=True, fillcolor=235)
    img = img.filter(ImageFilter.GaussianBlur(0.8))
    px = img.load()
    for _ in range(img.width * img.height // 40):
        x, y = rng.randrange(img.width), rng.randrange(img.height)
        px[x, y] = rng.choice((40, 200))
    path = OUT / "synthetic_scan.pdf"
    img.save(path, format="PDF", resolution=150)
    (TRUTH / "synthetic_scan.txt").write_text(truth)
    return path


def main() -> None:
    if not SOURCE.exists():
        raise SystemExit(f"missing {SOURCE}; run spikes/download_corpus.py first")
    OUT.mkdir(parents=True, exist_ok=True)
    TRUTH.mkdir(parents=True, exist_ok=True)
    reader = PdfReader(SOURCE)
    pages = pick_text_pages(reader, start=20, count=3)
    print(f"source pages (0-based) for two-column and scan: {pages}")

    made = [two_column(pdfium.PdfDocument(str(SOURCE)), pages), table_heavy()]
    made += password_variants(made[0])
    made.append(oversized())
    made.append(synthetic_scan(pages[0]))
    for p in made:
        print(f"{p.name:28s} {p.stat().st_size / 1e6:8.2f} MB")


if __name__ == "__main__":
    main()
