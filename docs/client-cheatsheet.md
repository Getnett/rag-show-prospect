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
