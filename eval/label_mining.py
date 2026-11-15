"""Mine SROIE's answers: which lines hold the true total, and why extraction missed them.

Run from apps/api on the development receipts only, so the test set stays untouched:
    .venv\\Scripts\\python ..\\..\\eval\\label_mining.py ..\\..\\data\\receipts\\sroie 0 349
Needs the .ocr.json files and the SROIE key/ folder, as for extract_eval.py.
"""

import json
import re
import sys
from collections import Counter
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "api"))

from app.config import get_settings  # noqa: E402
from app.extract import AMOUNT, NOT_TOTAL, TOTAL_RULES, extract  # noqa: E402
from app.ocr import OcrResult  # noqa: E402
from app.tax_profiles import load_tax_profiles  # noqa: E402
from app.validate import validate  # noqa: E402

# A service charge line; not "customer service" or "Goods & Services Tax".
SERVICE = re.compile(r"SERVICE\s*CH|\bSVC\b|SERV\.?\s*CH|\bS/C\b")
NOT_WORD = re.compile(r"[^A-Z ]+")  # a line's label is what's left after numbers and symbols go

folder, first, last = Path(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
profile = load_tax_profiles(get_settings().tax_profiles_path)["my"]


def label(rows: list[str], i: int) -> str:
    words = " ".join(NOT_WORD.sub(" ", rows[i]).split())
    if not words and i > 0:  # the amount sits alone on its row: the label is the row above
        words = " ".join(NOT_WORD.sub(" ", rows[i - 1]).split())
    return words or "(no label)"


def rule_for(text: str) -> str:
    if NOT_TOTAL.search(text):
        return "excluded by NOT_TOTAL"
    hit = next((w for p, w in TOTAL_RULES if p.search(text)), None)
    return f"matches a rule ({hit})" if hit else "no rule matches"


labels, missed_labels, causes = Counter(), Counter(), Counter()
outcomes, examples = Counter(), []
service = {"receipts": 0, "arithmetic_failed": 0, "ids": []}

for n in range(first, last + 1):
    rid = f"{n:03d}"
    path = folder / f"{rid}.ocr.json"
    key_path = folder / "key" / f"{rid}.json"
    if not path.exists() or not key_path.exists():
        continue
    truth_text = re.sub(r"[^\d.]", "", json.loads(key_path.read_text("utf-8")).get("total", ""))
    if not truth_text:
        continue
    ocr = OcrResult.model_validate_json(path.read_text("utf-8"))
    rows = [" ".join(r.split()).upper() for r in ocr.text.splitlines()]
    result = extract(ocr, profile)
    truth = Decimal(truth_text)

    # Rows that print the true total (with or without a thousands comma).
    forms = {f"{truth:.2f}", f"{truth:,.2f}"}
    printed = [re.compile(rf"(?<![\d.]){re.escape(f)}(?!\d)") for f in forms]
    hits = [i for i, r in enumerate(rows) if any(p.search(r) for p in printed)]
    for lab in {label(rows, i) for i in hits}:
        labels[lab] += 1

    got = result.total.value
    outcome = "correct" if got == truth else "not found" if got is None else "wrong"
    outcomes[outcome] += 1
    if outcome != "correct":
        if not hits:
            cause = "true total never printed in the OCR text (misread or missing)"
        elif got is not None and got > truth:
            cause = f"picked a larger amount ({got / truth:.1f}x the total)"
        elif got is not None:
            cause = "picked a smaller amount"
        else:
            cause = "no total line found"
        causes[cause] += 1
        for lab in {label(rows, i) for i in hits}:
            missed_labels[f"{lab}  [{rule_for(lab)}]"] += 1
        picked = (
            label(rows, result.total.source_row) if result.total.source_row is not None else "-"
        )
        examples.append(
            f"{rid}: want {truth}, got {got} from '{picked}'; true total on: "
            + "; ".join(f"'{label(rows, i)}'" for i in hits[:3])
        )

    charged = [
        r
        for r in rows
        if SERVICE.search(r) and any(Decimal(a.replace(",", "")) > 0 for a in AMOUNT.findall(r))
    ]
    if charged:  # a service charge actually added, not a "SERVICE CHARGE 0.00" line
        service["receipts"] += 1
        service["ids"].append(rid)
        checks = {c.name: c.passed for c in validate(result, profile).checks}
        if checks.get("arithmetic") is False:
            service["arithmetic_failed"] += 1

total = sum(outcomes.values())
print(f"# Total labels on SROIE receipts {first:03d}-{last:03d} ({total} with an answer)\n")
print("Outcome: " + ", ".join(f"{k} {v} ({v / total:.0%})" for k, v in outcomes.most_common()))
print()
print("## Why totals were missed\n")
for cause, count in causes.most_common():
    print(f"- {count:3d}  {cause}")
print("\n## Labels on lines holding the true total, all receipts (top 25)\n")
for lab, count in labels.most_common(25):
    print(f"- {count:3d}  {lab}  [{rule_for(lab)}]")
print("\n## Labels on lines holding the true total, missed receipts only\n")
for lab, count in missed_labels.most_common(30):
    print(f"- {count:3d}  {lab}")
print(
    f"\n## Service charge\n\n{service['receipts']} receipts add one (amount above zero); "
    f"the arithmetic check failed on {service['arithmetic_failed']} of them."
)
print(f"Receipts: {', '.join(service['ids'])}")
print("\n## Every miss\n")
print("\n".join(examples))
