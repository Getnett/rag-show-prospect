# ADR-006: License-clean PDF/OCR stack and format scope
- **Status:** Accepted (final parser chosen after the Week 0 Day 2 comparison)
- **Date:** 2026-11-04

## Context
The code is public and delivered to paying clients, so license matters. Verified 2026-11-04:
- **AGPL or restrictive:** PyMuPDF (AGPL), Marker (weights restricted above $5M revenue), MinerU (custom terms). OCRmyPDF needs Ghostscript, likely AGPL (unverified).
- **Permissive:** pypdfium2, pdfplumber, pypdf, Tesseract 5.5.4, RapidOCR and Docling (MIT code).
- PaddleOCR has no arm64 wheel.

## Options
1. pypdfium2 + pdfplumber + Tesseract (baseline)
2. Docling from the start
3. PyMuPDF/OCRmyPDF (fast, but license traps)

## Decision
Option 1, with Docling and RapidOCR compared on the messy PDFs in Week 0. Formats: PDF (native and OCR), TXT, MD, HTML, DOCX. CSV/XLSX and the vision-LLM call go to the roadmap; we keep only the interface and the flag.

## Trade-offs and consequences
pdfplumber is slower than PyMuPDF, and layout and tables need more of my own logic.

## How I'd explain it to a client
"Every library is commercially safe to hand over; nothing forces you to open-source your product."
