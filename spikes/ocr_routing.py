"""Day 2 🟥 HARD PART: OCR routing and text quality. YOU write the two functions at the bottom.

The harness (spikes/parse_compare.py) calls them for every page in spikes/day2_route_set.json:
  1. route_page(info) decides: keep the PDF's own text ("native") or OCR the page image ("ocr").
  2. text_quality(text) scores whatever text we end up with, so unreadable output becomes a visible
     "Failed: <reason>" instead of a silent "Indexed".

Reference solution (2026-11-09) after my first attempt; my v1 routed 44/44 but its text_quality
failed clean pages. The design is explained in docs/decisions/016-ocr-routing-and-text-quality.md.

Run:   uv run spikes/parse_compare.py                 (your functions)
       uv run spikes/parse_compare.py --baseline 100  (the naive "OCR if < N chars" rule, for comparison)

Rules: no network, no LLM, standard library only (re, math, statistics, collections...). It must be cheap:
it runs on every page of every upload on a 2 GB server.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import re

# ---------------------------------------------------------------------------------------------
# Scaffold (🟩, don't change): what the harness gives you about each page.
# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class PageInfo:
    native_text: str  # text from the PDF's own text layer (pypdfium2), possibly empty or junk
    width_pt: float  # page size in PDF points (1/72 inch)
    height_pt: float
    image_boxes: tuple[tuple[float, float, float, float], ...] = ()  # (left, bottom, right, top) per image, in pt
    invisible_chars: int = 0  # characters drawn in invisible render mode (how scanners embed their OCR layer)

    @property
    def image_coverage(self) -> float:
        """Share of the page area covered by images, 0..1 (overlaps counted twice, capped at 1)."""
        area = sum(max(0.0, r - l) * max(0.0, t - b) for l, b, r, t in self.image_boxes)
        return min(1.0, area / (self.width_pt * self.height_pt))


@dataclass
class Quality:
    score: float  # 0 = unreadable junk, 1 = clean text. You define the scale.
    flags: list[str] = field(default_factory=list)  # human-readable reasons, e.g. "glued words: 6% of tokens"


# The score below which a page is reported as "Failed: unreadable". Tune it on the data, not by feel.
QUALITY_MIN = 0.5  # chosen from the score table in docs/experiments.md (Day 2)


# ---------------------------------------------------------------------------------------------
# 🟥 Routing: what is this page made of?
# ---------------------------------------------------------------------------------------------

SCAN_COVERAGE = 0.9  # an image covering >= 90% of the page is a photo of the page, not a figure
MIN_TRUSTED_CHARS = 800  # a full-page image needs at least a real page of visible text to skip OCR


def route_page(info: PageInfo) -> str:
    """Return "native" or "ocr" for one page.

    1. No big image -> nothing to OCR. Blank, sparse and screenshot pages stay native, whatever their
       character count (character count alone was the naive rule's mistake in both directions).
    2. A page-sized image is probably a scan. Keep its text layer only if that layer is trustworthy:
       visible (scanners hide their own OCR layer), long enough to be the page body (not a stamped
       header), and readable. Otherwise OCR it.
    """
    if info.image_coverage < SCAN_COVERAGE:
        return "native"
    text = info.native_text
    visible_chars = len("".join(text.split())) - info.invisible_chars
    if visible_chars < MIN_TRUSTED_CHARS:
        return "ocr"  # scan with no text, a typed header only, or a hidden (scanner-made) OCR layer
    if text_quality(text).score < QUALITY_MIN:
        return "ocr"  # a visible but garbled text layer is no better than none
    return "native"  # e.g. a born-digital brochure with a full-page background image


# ---------------------------------------------------------------------------------------------
# 🟥 Text quality: judge tokens, then count.
# ---------------------------------------------------------------------------------------------

# Short words that make up roughly a fifth to a third of normal English prose. Garbage rarely spells them right.
COMMON_WORDS = frozenset(
    """the a an and or of to in on for with by from at as is are was be can you your it its this that these
    if not no will has have use using which when then click into how what all any more see also only other
    new one may must should after before each their there out up so set""".split()
)
TECHNICAL = re.compile(r"[/:._=@\\`<>{}\[\]#$%&+]|^\d[\d,.\-]*$|^--?\w")  # paths, URLs, config keys, numbers, CLI flags
WORD = re.compile(r"^[A-Za-z][A-Za-z'’\-]{0,24}$")
DIGIT_IN_WORD = re.compile(r"[a-z]\d+[a-z]|^[a-z]\d+[a-z]*$", re.IGNORECASE)  # y0u, Ncxtc1oud, 0f
EDGE_PUNCT = "\"'“”‘’()[]{},.;:!?*•–—-|"
NEUTRAL_SYMBOLS = frozenset("•–—-*·→>")  # bullets and arrows are normal in manuals
GLUED_LEN = 25  # letters-only run this long is words with the spaces lost (F20)
MIN_JUDGED = 20  # below this many tokens there's too little to judge prose
NOISE_WEIGHT = 1.5
COMMON_MIN = 0.05  # clean manual pages: 15-40% common words; the table page: 6%; damping starts below 5%


def classify(token: str) -> str:
    if token in NEUTRAL_SYMBOLS:
        return "neutral"
    core = token.strip(EDGE_PUNCT)
    if not core:
        return "noise"  # a lone symbol such as | ~ ‘ that isn't a bullet
    if TECHNICAL.search(core):
        return "neutral"  # don't judge commands, URLs, versions or numbers as English
    if DIGIT_IN_WORD.search(core):
        return "ocr_confusion"
    if core.isalpha() and len(core) >= GLUED_LEN:
        return "glued"
    if WORD.match(core):
        if len(core) <= 2 and core.lower() not in COMMON_WORDS and not core.isupper():
            return "noise"  # stray fragments like "hc", "oe", "ee"; acronyms (AI, UI, ID) are fine
        return "common" if core.lower() in COMMON_WORDS else "word"
    return "noise"


def text_quality(text: str) -> Quality:
    """Score 0..1 = share of judged tokens that look like real words, damped when common words are missing.

    Flags carry numbers so an admin sees *why* ("glued words: 6.2% of tokens"), not just a score.
    """
    tokens = text.split()
    if not tokens:
        return Quality(score=0.0, flags=["empty: no text"])
    counts: dict[str, int] = {}
    for t in tokens:
        kind = classify(t)
        counts[kind] = counts.get(kind, 0) + 1
    judged = len(tokens) - counts.get("neutral", 0)
    if judged == 0:
        return Quality(score=1.0, flags=["only technical tokens (commands, URLs, numbers)"])

    good = counts.get("word", 0) + counts.get("common", 0)
    # Noise fragments are rare in real text (<= 14% even on lightly damaged scans) and frequent in failed OCR
    # (>= 21% on pages with CER >= 0.5), so each one counts 1.5x against the score. See experiments.md, Day 2.
    score = max(0.0, (good - NOISE_WEIGHT * counts.get("noise", 0)) / judged)
    flags = []
    for kind, label in (("glued", "glued words"), ("ocr_confusion", "digits inside words"), ("noise", "noise fragments")):
        share = counts.get(kind, 0) / judged
        if share >= 0.02:
            flags.append(f"{label}: {share:.1%} of tokens")
    if judged >= MIN_JUDGED:
        common_share = counts.get("common", 0) / judged
        if common_share < COMMON_MIN:  # prose without "the/and/to/of" is word salad
            score *= common_share / COMMON_MIN
            flags.append(f"few common English words: {common_share:.1%}")
    else:
        flags.append(f"short text ({judged} words): judged on word shape only")
    return Quality(score=round(score, 3), flags=flags)


def page_status(decision: str, info: PageInfo, quality: Quality, text: str = "") -> str:
    """What the admin would see for this page: ok / skipped / failed with a reason.

    Context text_quality can't see on its own:
      - a page with no images and at most a page number ("vi") is blank by design: skip it, don't fail it;
      - an OCR'd page is a full-page image, so recovering only a handful of words means the OCR failed,
        even if those few words look fine.
    """
    if decision == "native" and info.image_coverage == 0 and len("".join(info.native_text.split())) < 20:
        return "skipped: blank page"
    if decision == "ocr" and len(text.split()) < MIN_JUDGED:
        return f"failed: OCR recovered only {len(text.split())} words from a full-page image"
    if quality.score < QUALITY_MIN:
        return "failed: " + ("; ".join(quality.flags) or "unreadable")
    return "ok"
