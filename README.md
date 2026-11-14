# AI Expense Tool

Turns receipt photos into structured, categorised, accounting-ready expense data.

**Core principle:** a deterministic engine handles the numbers; AI only makes suggestions.
Nothing is finalised without passing a confidence check or a human confirming it.

## Pipeline

1. **Capture**: upload or photograph a receipt; OCR runs locally (Tesseract or PaddleOCR).
2. **Extract**: merchant, date, amount, currency, tax.
3. **Validate**: plain code checks that net + tax = total. Tax rates live in a per-region config.
4. **Categorise**: keyword/merchant baseline first, then embeddings or a small LLM, compared against it.
5. **Review queue**: low-confidence items go to a person.
6. **Export**: CSV or an API-style payload for accounting tools.

## Repo layout

```
apps/
  api/        FastAPI backend (Render): OCR, extraction, validation, categorisation
    config/   tax_profiles.yaml (generic, Swiss, Malaysian)
  web/        Next.js frontend (Vercel): upload, review queue, export
supabase/
  migrations/ database schema
data/
  receipts/   receipt images (git-ignored)
  labels/     hand-labelled ground truth
eval/         categoriser comparison
```

## Getting started (Windows)

Requires Python 3.11+, Node 20+, and Git.

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
code .
```

Then press **F5** and pick **Full stack** to run the API on http://localhost:8000
(docs at `/docs`) and the web app on http://localhost:3000.

Manual alternative:

```powershell
cd apps\api; python -m venv .venv; .\.venv\Scripts\pip install -r requirements-dev.txt
.\.venv\Scripts\uvicorn app.main:app --reload
cd ..\web; npm install; npm run dev
```

## Results so far

Scored against [SROIE](https://rrc.cvc.uab.es/?ch=13) receipt answers (Malaysian receipts, `my` profile).
Rules were developed on receipts 000–349, then frozen and measured once on 350–449.

**Extract** (rules only, no AI):

| Field | Accuracy | Confident (≥ 0.8) | Accuracy when confident |
|---|---|---|---|
| Merchant | 95% | 87% | 99% |
| Date | 100% | 92% | 100% |
| Total | 87% | 94% | 89% |

**Validate** (plain-code checks; a total is only accepted when `subtotal + tax` or `cash − change` confirms it):

| | |
|---|---|
| Receipts auto-accepted | 29% |
| Totals correct among auto-accepted | 97% |
| Merchant + date + total all correct among auto-accepted | 93% |

The other 71% go to review with a stated reason. Most common: total not confirmed by any check,
no currency printed (currency is never assumed), low-confidence merchant.

Known failure modes: OCR misreads digits; totals picked from summary rows (some come out ~2× too
high); accounting-style negatives like `(0.01)` aren't read; merchant names that only appear in a logo.
Some SROIE answers are themselves inconsistent (pre-rounding vs rounded totals, one labelled with the
pre-tax amount).

Reproduce from `apps/api`: `python -m app.ocr <folder>`, then `python ../../eval/extract_eval.py <folder> my`.

## Design choices

- Currency is stored on every receipt, never assumed.
- Money is stored as `numeric` / `Decimal`, never float.
- Categories are a generic, editable set (travel, meals, software, office supplies, ...).
- Tax profiles are data, not code: adding a region means adding a YAML entry.

## Status

- [x] OCR (RapidOCR) and rule-based extraction, with an eval against SROIE
- [x] Validation engine: arithmetic, tax plausibility, cash, sanity checks; review routing
- [ ] Week 2: baseline categoriser, labelled test set, model comparison
- [ ] Week 3: UI, eval results, demo video
