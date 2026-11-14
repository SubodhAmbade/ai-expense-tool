# eval

- `extract_eval.py`: scores `app.extract` and `app.validate` against SROIE answers. Prints per-field
  accuracy, how many receipts validation auto-accepts and how often those are right, and every miss.
  Optional second argument: the region profile (default `generic`; use `my` for SROIE).

  ```powershell
  cd apps\api
  .\.venv\Scripts\python -m app.ocr ..\..\data\receipts\sroie
  .\.venv\Scripts\python ..\..\eval\extract_eval.py ..\..\data\receipts\sroie my
  ```

Categoriser comparison (baseline vs embeddings vs small LLM) will live here too.
