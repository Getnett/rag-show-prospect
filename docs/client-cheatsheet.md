# How to answer client questions

Built from the drills (CLAUDE.md §2, step 7). Each answer is short enough to say out loud.
**Rule:** say "we measured" only for what is in `docs/experiments.md`. Anything else is "we will" or "the design does".

## Ingestion

### "Your system says a document is 'Indexed'. How do I know the bot can actually read it?"
*Drill 2026-11-05. Status: the checks below are **designed, not built** (Day 2 / build week 1).*

> "'Indexed' doesn't just mean 'the file was processed'. For every page we check that real text came out: enough characters, and words that aren't glued together or garbled. Pages with no text, like scans, go through OCR. If a page still can't be read, the document is marked **Failed** with a plain reason like 'page 4 is an unreadable scan', so it never looks fine when it isn't. Then we prove it end to end: our test question set includes questions about scanned pages and tables, and you can open any source in the admin to see exactly the text the bot sees."

Why it works: it names the silent failure, gives the check, and gives the proof.
- **The silent failure:** a scan returns empty text with no error (we saw it on Day 1).
- **The check:** per-page text-quality signals.
- **The proof:** eval questions plus visible extracted text.

Evidence to point at:
- Day 1: a scanned page gave **0 characters and no error** with a naive parser.
- Day 1: the naive parser glued words together on **113 of 333 pages** of a *clean* manual; our chosen extractor had 0% (experiments.md).

Traps to avoid: don't say "OCR fixes it". OCR can produce garbage too (F03), and that's why there's a quality check *after* OCR.

### "Why don't you just run OCR on every page, to be safe?"
*Drill 2026-11-09. Status: **measured** in Day 2 (`docs/experiments.md`).*

My first answer: "OCR doesn't create reliable output; it can add unintended things, so even normal text gets read incorrectly." The core point is right; it lacked numbers and the time cost.

> "Because OCR is a guess, and the text inside a normal PDF is exact. On our tests, even a good scan came back about 99% right and a slightly damaged one about 88%, while the PDF's own text is 100%. So OCR'ing everything would make clean pages *worse*. It's also slow: about 1.5 seconds a page on a laptop, so a 300-page manual goes from seconds to about 8 minutes, and longer on a small server. So we OCR only the pages that are photos of text, and we check the readability of every page either way."

Why it works:
- **Quality:** OCR makes exact text worse.
- **Cost:** time per page, scaled to a real document.
- **What we do instead:** route only the pages that need it, and verify every page.

Evidence to point at:
- CER 0.008 on the real scan and 0.12 on light synthetic scans, vs exact native text.
- Median 1.5 s/page for OCR (Mac).
- Routing: 44/44, 0 needless OCR (ADR-016).

Traps to avoid:
- Don't say "OCR is unreliable" in general. It's very good on a clean scan, which is why we use it for scans.
- Don't promise speed numbers for the server until Day 7 measures them on the VM.

## Retrieval

### "Your own numbers show fixed-size chunking scored higher. Why did you pick the lower one?"
*Drill 2026-11-17. Status: **measured** in Day 3 (`docs/experiments.md`, ADR-017).*

My first answer: the set is only 20 questions, so we can't conclude fixed-size is better; fixed-size chunks lose structure, so citations are unclear; and chunks cut at random points can give incomplete answers or hallucinations. Right on the sample size and the citations. It lacked the numbers and a switch rule, and it claimed hallucination we haven't measured.

> "Because the gap is two questions out of fourteen, and that's noise, not a result. Both setups miss the same hard cases. What decides it is what the client sees: our chunks follow your document's sections, so every answer can cite 'Sharing > Public link shares, page 64' and show you the exact passage. Fixed-size chunks start and stop mid-sentence, so the citation points at an arbitrary slice. We haven't closed the door, though: we wrote down in advance that if the structured version is still behind after we add keyword search and reranking, we switch. And the test set grows to 60 questions before anything ships."

Why it works:
- **Puts the number in proportion:** 2 of 14 questions.
- **Names the client benefit:** clear citations and a readable source passage.
- **Shows it's a decision, not a preference:** a rule written down in advance, then re-checked on a bigger set.

Evidence to point at:
- recall@5 0.71 (fixed_512) vs 0.57 (heading_aware) with OpenAI embeddings; one question = 0.07.
- q20's list across pages 64–65 is one chunk with its heading in heading_aware.
- The switch rule is in ADR-017.

Traps to avoid:
- Don't say fixed-size chunks "cause hallucinations". We haven't measured generation yet (Day 5). Say "the citation points at an arbitrary slice", which is true and visible.
- Don't call fixed-size chunks "random". They're cut at fixed positions; the problem is that the positions ignore the content.
