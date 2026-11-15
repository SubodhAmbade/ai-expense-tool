# AI Expense Tool

Turns receipt photos into structured, categorised, accounting-ready expense data.

**Core principle:** a deterministic engine handles the numbers; AI only makes suggestions.
Nothing is finalised without passing a confidence check or a human confirming it.

For setup, usage, architecture and design decisions, see the **[User and Architecture Guide](docs/GUIDE.md)**.

## Pipeline

1. **Capture**: upload or photograph a receipt; OCR runs locally (Tesseract or PaddleOCR).
2. **Extract**: merchant, date, amount, currency, tax.
3. **Validate**: plain code checks that net + tax = total. Tax rates live in a per-region config.
4. **Categorise**: keyword/merchant rules first, compared against a small local BERT model.
5. **Review queue**: low-confidence items go to a person, who corrects and confirms them.
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
  labels/     category labels per merchant (AI-drafted, being verified)
eval/         categoriser comparison
```

## Getting started (Windows)

Requires Python 3.13, Node 20+, Git and a free [Supabase](https://supabase.com) project.

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
code .
```

Run the three SQL files in `supabase/migrations/` in your Supabase project, put its URL and secret key
in `apps/api/.env`, then press **F5** and pick **Full stack**: the API runs on http://localhost:8000
(docs at `/docs`) and the web app on http://localhost:3000. Step-by-step instructions are in the
[guide](docs/GUIDE.md#run-the-app-locally).

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
| Totals correct among auto-accepted | 97% (28 of 29) |
| Merchant + date + total all correct among auto-accepted | 93% (26 of 28 with full answers) |

The other 71% go to review with a stated reason. Most common: total not confirmed by any check,
no currency printed (currency is never assumed), low-confidence merchant.

**Categorise** (suggestions only; a person can always change them). Compared on 201 receipts from 76
merchants that none of the methods had seen (the data is split by merchant, not by receipt):

| Method | Accuracy | Confident (≥ 0.8) | Accuracy when confident |
|---|---|---|---|
| Rules (merchant and item keywords) | 85% | 49% | 100% |
| BERT, zero-shot (compare to category descriptions) | 5% | 29% | 7% |
| BERT + examples (nearest labelled receipts) | 74% | 45% | 84% |

BERT = `bge-small-en-v1.5`, run locally (no API, no per-use cost); 255 ms per receipt on a laptop.
Caveat: the category labels were drafted by AI and are not yet human-verified, and they were drafted
partly with keyword rules, so the Rules row is inflated. The eval also reports the fair split
(receipts whose merchant name does or doesn't reveal the category).

Known extraction failure modes: OCR misreads digits; totals picked from summary rows (some come out ~2× too
high); accounting-style negatives like `(0.01)` aren't read; merchant names that only appear in a logo.
Some SROIE answers are themselves inconsistent (pre-rounding vs rounded totals, one labelled with the
pre-tax amount).

Reproduce from `apps/api`: `python -m app.ocr <folder>`, then `python ../../eval/extract_eval.py <folder> my`;
for categories, `python ../../eval/categorise_eval.py`.

## Design choices

- Currency is stored on every receipt, never assumed.
- Money is stored as `numeric` / `Decimal`, never float.
- Categories are a generic, editable set (travel, meals, software, office supplies, ...).
- Tax profiles are data, not code: adding a region means adding a YAML entry.

## Status

- [x] OCR (RapidOCR) and rule-based extraction, with an eval against SROIE
- [x] Validation engine: arithmetic, tax plausibility, cash, sanity checks; review routing
- [x] Categoriser comparison: rules vs local BERT (zero-shot and with examples)
- [x] Skeleton app: upload, review, confirm, CSV export; Supabase for data and photos
- [ ] Login, then deploy
- [ ] Week 2: baseline categoriser, labelled test set, model comparison
- [ ] Week 3: UI, eval results, demo video
