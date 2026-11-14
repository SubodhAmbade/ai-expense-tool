# eval

- `extract_eval.py`: scores `app.extract` and `app.validate` against SROIE answers. Prints per-field
  accuracy, how many receipts validation auto-accepts and how often those are right, and every miss.
  Optional second argument: the region profile (default `generic`; use `my` for SROIE).

  ```powershell
  cd apps\api
  .\.venv\Scripts\python -m app.ocr ..\..\data\receipts\sroie
  .\.venv\Scripts\python ..\..\eval\extract_eval.py ..\..\data\receipts\sroie my
  ```

- `categorise_eval.py`: compares the categorisers in `app.categorise` on merchants they haven't seen.
  Needs `data/receipts/sroie_ocr_text.jsonl` and `data/labels/merchant_categories.csv`. Embeds one
  receipt at a time (about a minute on a laptop).

  ```powershell
  cd apps\api
  .\.venv\Scripts\python ..\..\eval\categorise_eval.py
  ```
