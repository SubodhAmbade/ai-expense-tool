"""Categorise stage: receipt text -> a suggested expense category. Suggestions only, never final.

Three interchangeable methods, compared in eval/categorise_eval.py:
  by_rules        keyword lookup (the baseline, no model)
  by_description  embedding similarity to each category's description (no labelled data)
  by_examples     embedding similarity to labelled receipts (nearest neighbours)
"""

import os
import re
from functools import lru_cache
from typing import Literal

import numpy as np
from pydantic import BaseModel

CATEGORIES = {  # slug -> description (the description is what by_description compares against)
    "meals": "Restaurant, cafe, bakery or takeaway: prepared food and drinks",
    "groceries": "Supermarket, mini market or convenience store: packaged food and household items",
    "office_supplies": "Stationery, books, printing, paper, pens, files, ink and toner",
    "repairs_maintenance": "Hardware store: tools, paint, electrical parts, building materials",
    "health": "Pharmacy or clinic: medicine, supplements, personal care",
    "transport": "Petrol station, parking, tolls, train or bus fares",
    "travel": "Flights, travel agency, car rental",
    "accommodation": "Hotel, hostel or other lodging",
    "software": "Software licence or online subscription",
    "other": "Anything else: gifts, furniture, clothing, telecom",
}

MERCHANT_RULES = [  # checked against the top rows of the receipt, first match wins
    ("transport", r"PARKING|PETROL|SHELL|FUEL|PETROKIOSK"),
    ("health", r"PHARMA|FARMASI|GUARDIAN|WATSON|HEALTHCARE|CLINIC|KLINIK"),
    ("office_supplies", r"STATIONER|BOOK|PRINT"),
    ("repairs_maintenance", r"HARDWARE|ELECTRICAL|MACHINERY|TIMBER|D\.\s?I\.\s?Y"),
    ("accommodation", r"HOTEL|HOSTEL|\bINN\b|RESORT"),
    (
        "meals",
        r"RESTAU|RESTOR|CAFE|KOPITIAM|PIZZA|NOODLE|KITCHEN|BISTRO|BAKERY|CAKE|COFFEE|SEAFOOD|F&B",
    ),
    ("groceries", r"\bMART\b|\bMARKET\b|PASAR|CASH & CARRY|GROCER|RUNCIT|HYPERMARKET"),
]
ITEM_RULES = [  # counted across the whole receipt, most hits wins
    (
        "meals",
        r"NASI|\bMEE\b|RICE|NOODLE|\bTEA\b|\bTEH\b|KOPI|COFFEE|CHICKEN|SOUP|DINE IN|TAKE ?AWAY",
    ),
    ("transport", r"LITRE|RON ?9[57]|DIESEL|PARKING FEE|TOLL"),
    (
        "repairs_maintenance",
        r"PAINT|DRILL|SCREW|\bPVC\b|CEMENT|PLUG|SOCKET|BRACKET|\bBOLT\b|SAND PAPER",
    ),
    ("office_supplies", r"\bPEN\b|\bFILE\b|\bA4\b|PAPER|TONER|CARTRIDGE|STAPLE|ENVELOPE|MARKER"),
    ("health", r"TABLET|CAPSULE|VITAMIN|\bCREAM\b|MEDICINE"),
    ("groceries", r"\d+ ?(G|GM|KG|ML)\b|MILK|BISCUIT|BREAD|SUGAR|FRUITS?|VEGETABLE"),
]
MERCHANT_RULES = [(c, re.compile(p)) for c, p in MERCHANT_RULES]
ITEM_RULES = [(c, re.compile(p)) for c, p in ITEM_RULES]


class Suggestion(BaseModel):
    category: str
    confidence: float
    source: Literal["rule", "description", "examples"]


def by_rules(text: str) -> Suggestion:
    rows = text.upper().splitlines()
    header = "\n".join(rows[:5])
    for category, pattern in MERCHANT_RULES:
        if pattern.search(header):
            return Suggestion(category=category, confidence=0.9, source="rule")
    hits = {c: len(p.findall("\n".join(rows))) for c, p in ITEM_RULES}
    category, count = max(hits.items(), key=lambda kv: kv[1])
    if count == 0:
        return Suggestion(category="other", confidence=0.0, source="rule")
    return Suggestion(category=category, confidence=0.6 if count >= 2 else 0.4, source="rule")


@lru_cache
def _model():
    from fastembed import TextEmbedding  # imported here so rules work without the model installed

    # A setting so the eval can compare models, e.g. EMBED_MODEL=minishlab/potion-base-8M (a 30 MB
    # static model, much lighter than this 67 MB transformer).
    return TextEmbedding(os.environ.get("EMBED_MODEL", "BAAI/bge-small-en-v1.5"))


def embed(texts: list[str]) -> np.ndarray:
    """One unit-length vector per text, so a dot product is the cosine similarity."""
    vectors = np.array(list(_model().embed(texts, batch_size=8)))  # small batches keep memory low
    return vectors / np.linalg.norm(vectors, axis=1, keepdims=True)


def by_description(vector: np.ndarray, category_vectors: np.ndarray) -> Suggestion:
    """category_vectors: embed(list(CATEGORIES.values())), in CATEGORIES order."""
    sims = category_vectors @ vector
    best, second = np.sort(sims)[-1], np.sort(sims)[-2]
    return Suggestion(
        category=list(CATEGORIES)[int(np.argmax(sims))],
        confidence=round(float(min((best - second) * 10, 1.0)), 3),  # gap to the runner-up
        source="description",
    )


def by_examples(
    vector: np.ndarray, example_vectors: np.ndarray, labels: list[str], k: int = 5
) -> Suggestion:
    nearest = np.argsort(example_vectors @ vector)[-k:]
    votes: dict[str, int] = {}
    for i in nearest:
        votes[labels[i]] = votes.get(labels[i], 0) + 1
    category, count = max(votes.items(), key=lambda kv: kv[1])
    return Suggestion(
        category=category, confidence=round(count / len(nearest), 3), source="examples"
    )
