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
    config/   tax_profiles.yaml (generic + Swiss)
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

**Extract** (rules only, no AI) scored against [SROIE](https://rrc.cvc.uab.es/?ch=13) receipt answers.
Rules were tuned on receipts 000–149 and frozen, then measured once on 150–249:

| Field | Accuracy | Auto-accepted (confidence ≥ 0.8) | Accuracy when auto-accepted |
|---|---|---|---|
| Merchant | 90% | 72% | 94% |
| Date | 95% | 60% | 98% |
| Total | 89% | 93% | 88% |

Known failure modes: OCR misreads digits (`1.42` for `21.42`), tax-summary rows mistaken for the total,
merchant names that only appear in a logo. Most wrong totals break `subtotal + tax = total` or
`cash − change = total`, which is what the Validate step checks next.

Reproduce: `python -m app.ocr <folder>` then `python ../../eval/extract_eval.py <folder>` from `apps/api`.

## Design choices

- Currency is stored on every receipt, never assumed.
- Money is stored as `numeric` / `Decimal`, never float.
- Categories are a generic, editable set (travel, meals, software, office supplies, ...).
- Tax profiles are data, not code: adding a region means adding a YAML entry.

## Status

- [x] OCR (RapidOCR) and rule-based extraction, with an eval against SROIE
- [ ] Week 1: validation engine
- [ ] Week 2: baseline categoriser, labelled test set, model comparison
- [ ] Week 3: UI, eval results, demo video
