# eval

- `extract_eval.py`: scores merchant, date and total from `app.extract` against SROIE answers.
  Prints accuracy, how many fields would be auto-accepted, and every miss.

  ```powershell
  cd apps\api
  .\.venv\Scripts\python -m app.ocr ..\..\data\receipts\sroie
  .\.venv\Scripts\python ..\..\eval\extract_eval.py ..\..\data\receipts\sroie
  ```

Categoriser comparison (baseline vs embeddings vs small LLM) will live here too.
