"""Score extraction and validation against SROIE answers.

Run from apps/api:
    .venv\\Scripts\\python ..\\..\\eval\\extract_eval.py ..\\..\\data\\receipts\\sroie
Needs the .ocr.json files (python -m app.ocr <folder>) and the SROIE key/ folder.
"""

import json
import re
import sys
from datetime import datetime
from decimal import Decimal
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "api"))

from app.config import get_settings  # noqa: E402
from app.extract import extract  # noqa: E402
from app.ocr import OcrResult  # noqa: E402
from app.tax_profiles import load_tax_profiles  # noqa: E402
from app.validate import REVIEW_THRESHOLD, validate  # noqa: E402

DATE_FORMATS = ["%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y", "%d.%m.%Y", "%Y-%m-%d", "%d %b %Y"]
ANSWER_KEY = {"merchant": "company", "date": "date", "total": "total"}


def norm(text: str) -> str:
    return re.sub(r"[^A-Z0-9 ]", "", text.upper()).strip()


folder = Path(sys.argv[1])
profiles = load_tax_profiles(get_settings().tax_profiles_path)
profile = profiles[sys.argv[2] if len(sys.argv) > 2 else "generic"]

stats = {f: {"n": 0, "correct": 0, "confident": 0, "confident_correct": 0} for f in ANSWER_KEY}
misses = []
accepted, accepted_correct, accepted_total_correct = 0, 0, 0
files = sorted(folder.glob("*.ocr.json"))
for path in files:
    key = json.loads((folder / "key" / path.name.replace(".ocr.json", ".json")).read_text("utf-8"))
    result = extract(OcrResult.model_validate_json(path.read_text("utf-8")), profile)

    truth_date = None
    for fmt in DATE_FORMATS:
        try:
            truth_date = datetime.strptime(key["date"].strip(), fmt).date()
            break
        except ValueError:
            pass
    truth_total = re.sub(r"[^\d.]", "", key.get("total", ""))  # some answers are "$8.20"
    merchant_similarity = SequenceMatcher(
        None, norm(result.merchant.value or ""), norm(key["company"])
    ).ratio()

    checks = {  # None = no answer in the SROIE key, so the field is skipped
        "merchant": merchant_similarity >= 0.9,
        "date": result.date.value == truth_date if truth_date else None,
        "total": result.total.value == Decimal(truth_total) if truth_total else None,
    }
    for field, ok in checks.items():
        if ok is None:
            continue
        confident = getattr(result, field).confidence >= REVIEW_THRESHOLD
        stats[field]["n"] += 1
        stats[field]["correct"] += ok
        stats[field]["confident"] += confident
        stats[field]["confident_correct"] += ok and confident
        if not ok:
            got, want = getattr(result, field).value, key[ANSWER_KEY[field]]
            misses.append(f"{path.name.split('.')[0]} {field}: got {got!r}, want {want!r}")

    if validate(result, profile).status == "auto_accept":
        accepted += 1
        accepted_correct += all(ok is not False for ok in checks.values())
        accepted_total_correct += checks["total"] is not False

print(f"\n{len(files)} receipts, profile '{profile.code}', review threshold {REVIEW_THRESHOLD}\n")
print("| Field | Accuracy | Auto-accepted | Accuracy when auto-accepted |")
print("|---|---|---|---|")
for field, s in stats.items():
    auto = s["confident_correct"] / s["confident"] if s["confident"] else 0
    print(f"| {field} | {s['correct'] / s['n']:.0%} | {s['confident'] / s['n']:.0%} | {auto:.0%} |")
print(f"\nAfter validation: {accepted / len(files):.0%} of receipts auto-accepted;")
print(f"of those, total correct {accepted_total_correct / max(accepted, 1):.0%}, ", end="")
print(f"merchant + date + total all correct {accepted_correct / max(accepted, 1):.0%}")
print("\nMisses:\n" + "\n".join(misses))
