# ADR-016: OCR routing by page composition, and a token-based text-quality gate
- **Status:** Accepted (Week 0 spike; carried into the ingestion worker in build week 1)
- **Date:** 2026-11-09

## Context
Day 1 showed two silent failures: scans give empty text with no error, and an extractor can produce glued words on clean pages. Day 2 measured the naive rule "OCR if a page has fewer than N characters" on 44 labelled pages (`spikes/day2_route_set.json`). At every N it either missed scans or OCR'd pages for nothing (sweep in `docs/experiments.md`).
- **Missed scans:** a scan with a typed header (154 chars) and a scan with a hidden OCR layer (1,503 chars). Only N = 2,000 catches both, at the cost of 30 needless OCRs.
- **Needless OCR:** with N ≤ 50, the blank pages.

## Options
1. Character-count threshold (baseline)
2. **Page composition**: route on how much of the page is an image, then verify any text layer under a full-page image
3. OCR every page and keep whichever text scores better (2× the work: ~1.5 s/page on a 2 GB VM for every page)

## Decision
Option 2, plus a text-quality gate on whatever text we keep.

**Routing (`route_page`):**
- Image covering < 90% of the page → native. Blank, sparse and screenshot pages contain no page photo to read.
- Image covering ≥ 90% → it's probably a scan. Keep the text layer only if all three hold:
  - It's **visible**. Scanners hide their own OCR layer with invisible render mode.
  - It has **≥ 800 visible characters**, so it's a page body and not a stamped header.
  - It **scores ≥ QUALITY_MIN**.
  Otherwise OCR. This keeps born-digital brochures with full-page backgrounds native.

**Quality (`text_quality`):** classify each token, then count.
- Neutral, not judged: commands, URLs, numbers, bullets.
- Word, or common English word.
- Bad: glued (≥ 25 letters), digit inside a word (`y0u`), noise fragment (`hc`, `|`, `‘`).

Score = (words − 1.5 × noise) / judged tokens. It's damped when fewer than 5% of tokens are common words, and only when there are ≥ 20 tokens. Every flag carries a number. `QUALITY_MIN = 0.5`.

**Page status (`page_status`):** adds the context text quality can't see.
- A no-image page with < 20 characters is *skipped as blank*, not failed.
- An OCR'd page that yields < 20 words is *failed*: "OCR recovered only N words".

## Results (Mac, Tesseract 5.5.4, 300 dpi, no preprocessing)
- **Routing:** baseline 39/44 with 2 scans missed → **44/44, 0 missed, 0 needless OCR**.
- **Failed pages** = exactly the pages with OCR CER ≥ 0.5 (5 pages).
- **Passing pages:** every page with CER ≤ 0.12 passes, and no clean page fails. 3 blank pages are skipped.
- **Break-it on synthetic PageInfo:**
  - Brochure with a full-page background → native.
  - Hidden OCR layer → OCR.
  - Visible glued layer → OCR (quality 0.0).
  - Full-page screenshot → OCR.

## Trade-offs and limits
- **Tuned on the data it's scored on.** Thresholds come from 10 pages with ground truth. The margin is thin: the worst readable page scores 0.65 and the best unreadable one 0.46. Re-check when the real corpus or new scans arrive.
- **English only.** The common-word list and word regex would fail other languages. Multilingual support is on the roadmap.
- **Word shape can't detect wrong-but-real words.** "pomp" for "prompt" passes. That's why noise weighting matters, and why the retrieval eval (Day 3+) is the final judge.
- **Full-page screenshots get OCR'd.** They look exactly like scans, and the quality gate catches junk afterwards.
- **No image preprocessing yet** (denoise, deskew, binarise). Medium synthetic scans fail outright. Preprocessing could rescue some and is a measured experiment for later, not a default.

## How I'd explain it to a client
"We don't guess from how much text a page has. We look at what the page is made of. If it's a photo of a page, we read it with OCR, unless it already carries real, visible text we can trust. Then every page gets a readability score with a plain reason. Unreadable pages show as Failed in the admin, with the reason, instead of silently counting as indexed. On our test set this caught every scan, including two the simple approach missed, and flagged exactly the pages OCR couldn't read."
