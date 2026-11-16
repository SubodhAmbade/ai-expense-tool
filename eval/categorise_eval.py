"""Compare the three categorisers on receipts from merchants none of them has seen.

Run from apps/api:
    .venv\\Scripts\\python ..\\..\\eval\\categorise_eval.py
Another embedding model: set EMBED_MODEL first, e.g. EMBED_MODEL=minishlab/potion-base-8M.
Needs data/receipts/sroie_ocr_text.jsonl and data/labels/merchant_categories.csv.
"""

import csv
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from app.categorise import CATEGORIES, by_description, by_examples, by_rules, embed  # noqa: E402

CONFIDENT = 0.8  # same review threshold as validation
TEST_SHARE = 30  # percent of merchants held out

with open(ROOT / "data" / "labels" / "merchant_categories.csv", encoding="utf-8") as f:
    labels = {row["merchant"]: row["category"] for row in csv.DictReader(f)}
with open(ROOT / "data" / "receipts" / "sroie_ocr_text.jsonl", encoding="utf-8") as f:
    receipts = [r for r in map(json.loads, f) if r["merchant"] in labels]

# Split by merchant, not by receipt: a merchant is either all examples or all test. The hash makes
# the split the same on every machine.
for r in receipts:
    r["test"] = int(hashlib.md5(r["merchant"].encode()).hexdigest(), 16) % 100 < TEST_SHARE
    r["label"] = labels[r["merchant"]]
examples = [r for r in receipts if not r["test"]]
test = [r for r in receipts if r["test"]]

category_vectors = embed(list(CATEGORIES.values()))  # also loads the model, so it isn't timed below
start = time.perf_counter()
for i, r in enumerate(receipts, 1):  # one receipt at a time, as the app will see them
    r["vector"] = embed([r["text"]])[0]
    print(f"\rEmbedding receipts: {i}/{len(receipts)}", end="", flush=True)
embed_ms = (time.perf_counter() - start) * 1000 / len(receipts)
example_vectors = np.array([r["vector"] for r in examples])
example_labels = [r["label"] for r in examples]


def rules_then_examples(r):
    """The design in the project plan: a merchant-name rule when one matches, else the model."""
    rule = by_rules(r["text"])
    if rule.confidence >= 0.9:  # 0.9 = the merchant name matched a keyword
        return rule
    return by_examples(r["vector"], example_vectors, example_labels)


methods = {
    "Rules": lambda r: by_rules(r["text"]),
    "BERT, zero-shot": lambda r: by_description(r["vector"], category_vectors),
    "BERT + examples": lambda r: by_examples(r["vector"], example_vectors, example_labels),
    "Rules, then BERT + examples": rules_then_examples,
}

# The labels were drafted with keyword rules on merchant names, so rules are graded partly on their
# own homework where the name contains a keyword. Receipts where it doesn't are the fair comparison.
for r in test:
    r["name_reveals"] = by_rules(r["text"]).confidence >= 0.9
revealing = sum(r["name_reveals"] for r in test)

merchants = len({r["merchant"] for r in test})
print(f"\n{len(test)} test receipts from {merchants} merchants; {len(examples)} example receipts")
print(f"Embedding: {embed_ms:.0f} ms per receipt\n")
print(
    f"| Method | Accuracy | Name reveals category ({revealing}) "
    f"| Name doesn't ({len(test) - revealing}) | Confident | Accuracy when confident |"
)
print("|---|---|---|---|---|---|")
for name, method in methods.items():
    results = [(r, method(r)) for r in test]
    correct = [(r, r["label"] == s.category, s.confidence) for r, s in results]

    def rate(rows):
        return f"{sum(ok for _, ok, _ in rows) / max(len(rows), 1):.0%}"

    confident = [c for c in correct if c[2] >= CONFIDENT]
    print(
        f"| {name} | {rate(correct)} | {rate([c for c in correct if c[0]['name_reveals']])} "
        f"| {rate([c for c in correct if not c[0]['name_reveals']])} "
        f"| {len(confident) / len(test):.0%} | {rate(confident)} |"
    )
