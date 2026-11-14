"""Extract stage: OCR rows -> merchant, date, totals, tax, currency. Deterministic rules only.

Every field carries a confidence (rule strength x OCR confidence of its row) and the row it came
from, so low-confidence values can go to review and the UI can highlight their source.
"""

import re
from datetime import date
from decimal import Decimal
from typing import Generic, TypeVar

from pydantic import BaseModel

from app.ocr import OcrResult
from app.tax_profiles import TaxProfile

T = TypeVar("T")

CURRENCY_PREFIX = re.compile(r"^(RM|MYR|CHF|EUR|USD|\$|€|£)?\s*")
AMOUNT = re.compile(r"(?<![\d.,])\d{1,3}(?:,\d{3})*\.\d{2}(?![\d%])|(?<![\d.,])\d+\.\d{2}(?![\d%])")

# Ranked total rules: (pattern, rule confidence). The first rule with a match wins.
TOTAL_RULES = [
    (re.compile(r"ROUND\w*\s*\w?\s*TOTAL|TOTAL\s*(AMT\s*|AMOUNT\s*)?ROUND"), 1.0),
    (
        re.compile(
            r"N\s*ETT?\s*TOTAL|GRAND\s*TOTAL|TOTAL\s*(AMOUNT|AMT|PAYABLE|SALES|INCL|DUE)|(AMT|AMOUNT|BALANCE)\s*DUE|NETT?\s*AMT"
        ),
        0.95,
    ),
    (re.compile(r"\b(TOTAL|TOTL|TTL)\b"), 0.9),
]
CASH_RULES = [(re.compile(r"\b(CASH|VISA|MASTER\w*|CARD|PAID|PAYMENT|TENDER\w*)\b"), 0.6)]
CHANGE_RULES = [(re.compile(r"\bCHANGE\b"), 0.9)]
NOT_TOTAL = re.compile(
    r"SUB\s*-?\s*TOTA|EXCL|TOTAL\s*Q|QTY|ITEM|DISC|SAV|CHANGE|ADJ|TOTAL\s*(GST|TAX|SST|VAT)|(GST|TAX|SST|VAT)\s*TOTAL"
)
ROUNDING = re.compile(r"ROUND\w*\s*(ADJ|\(|:|-?\d|RM)")  # an adjustment row, not a rounded total
SIGNED_AMOUNT = re.compile(r"(-?)\s*(\d+\.\d{2})\s*$")
SUBTOTAL_RULES = [(re.compile(r"SUB\s*-?\s*TOTA|TOTAL\s*EXCL|AMOUNT\s*EXCL"), 0.85)]
TAX_RULES = [
    (re.compile(r"TOTAL\s*(GST|TAX|VAT|SST)|(GST|TAX|VAT|SST)\s*(AMOUNT|AMT|TOTAL)"), 0.85),
    (re.compile(r"\b(GST|TAX|VAT|SST|MWST|TVA|IVA)\b"), 0.75),
]
NOT_TAX = re.compile(  # totals that mention tax ("Total with GST", "Total Excl. GST"), tax IDs
    r"INCL|EXCL|\bINC\b|WITH|SUB|TAXABLE|\bID\b|REG|NO\b|INVOICE|"
    r"(?<!GST )(?<!TAX )(?<!VAT )(?<!SST )TOTAL(?!\s*(GST|TAX|VAT|SST))"  # keep "GST TOTAL 0.51"
)

DATE_PATTERNS = [  # (pattern, group order); 'a' = ambiguous day/month, resolved by profile
    (re.compile(r"\b(\d{4})[/.-](\d{1,2})[/.-](\d{1,2})\b"), "ymd"),
    (re.compile(r"\b(\d{1,2})[/.-](\d{1,2})[/.-](\d{4}(?=\d{1,2}:)|(?:\d{4}|\d{2})(?!\d))"), "a"),
    (
        re.compile(
            r"\b(\d{1,2})\s*-?(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\w*\s*-?(\d{4}|\d{2})\b"
        ),
        "dmy",
    ),
]
MONTHS = "JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC".split()

CURRENCIES = {  # token on the receipt -> ISO code. A bare "$" is ambiguous, so it is not here.
    "RM": "MYR", "MYR": "MYR", "CHF": "CHF", "SFR": "CHF", "FR.": "CHF", "EUR": "EUR", "€": "EUR",
    "GBP": "GBP", "£": "GBP", "USD": "USD", "US$": "USD", "AUD": "AUD", "A$": "AUD",
    "SGD": "SGD", "S$": "SGD", "NZD": "NZD", "INR": "INR", "₹": "INR",
}  # fmt: skip
CURRENCY = re.compile(r"(?<![A-Z])(" + "|".join(re.escape(k) for k in CURRENCIES) + r")(?![A-Z])")
JUNK_MERCHANT = re.compile(
    r"TEL|FAX|PHONE|GST|REG|CO\.?\s*NO|INVOICE|RECEIPT|FORMERLY|LICENSEE|^\W*$|"
    r"JALAN|JLN|TAMAN|STREET|ROAD|AVENUE|FLOOR|FLR|LEVEL|LOT\b|^NO[.: ]|\d+,"  # address lines
)
COMPANY_SUFFIX = re.compile(
    r"\b(SDN\.?\s*BHD|S/B|BHD|LTD|LLC|INC|GMBH|AG|PTY|ENTERPRISE|TRADING|RESTAURANTS?)\b\.?|\bCO\."
)
REG_LINE = re.compile(r"(CO|COMPANY|GST|ROC)\.?\s*(NO|REG|ID)")  # "(CO. NO. 123-D)", not a name
REG_NUMBER = re.compile(r"\(?[\w-]*\d{4,}[\w-]*\)?")  # "(001451637-M)", "519537-X)"


class Field(BaseModel, Generic[T]):
    value: T | None = None
    confidence: float = 0.0
    source_row: int | None = None


class ExtractResult(BaseModel):
    merchant: Field[str]
    date: Field[date]
    total: Field[Decimal]  # amount paid, after any rounding
    subtotal: Field[Decimal]
    tax: Field[Decimal]
    cash: Field[Decimal]  # amount tendered
    change: Field[Decimal]
    currency: Field[str]  # ISO 4217; confidence 0.5 when taken from the profile default


def _find_amount(rows: list[str], conf: list[float], rules, exclude=None) -> Field[Decimal]:
    for pattern, weight in rules:
        hits = []
        for i, row in enumerate(rows):
            if not pattern.search(row) or (exclude and exclude.search(row)):
                continue
            amounts = AMOUNT.findall(row)
            next_row = CURRENCY_PREFIX.sub("", rows[i + 1].strip()) if i + 1 < len(rows) else ""
            if not amounts and AMOUNT.fullmatch(next_row):
                amounts, i = [next_row], i + 1  # label and amount on separate rows
            if amounts:  # the amount is the right-most number on the row
                hits.append((Decimal(amounts[-1].replace(",", "")), i))
        if hits:
            value, i = max(hits)  # the largest candidate; smaller ones are usually part-payments
            return Field(value=value, confidence=round(weight * conf[i], 3), source_row=i)
    return Field()


def _total(rows: list[str], conf: list[float], cash: Field, change: Field) -> Field[Decimal]:
    total = _find_amount(rows, conf, TOTAL_RULES, NOT_TOTAL)
    if total.value is None and cash.value is not None:  # no total printed: paid = cash - change
        # a misread change can make this <= 0; the sanity check then sends it to review
        paid = cash.value - (change.value or 0)
        return Field(value=paid, confidence=cash.confidence, source_row=cash.source_row)
    if total.value is not None and not TOTAL_RULES[0][0].search(rows[total.source_row]):
        for row in rows[total.source_row + 1 :]:  # a rounding row below the total: add it
            if ROUNDING.search(row) and (m := SIGNED_AMOUNT.search(row)):
                total.value += Decimal(m.group(1) + m.group(2))
                break
    return total


def _merchant(raw: list[str], conf: list[float]) -> Field[str]:
    candidates = []  # (rule confidence, row index, cleaned name)
    for i, row in enumerate(raw[:8]):
        if REG_LINE.search(row.upper()):
            continue
        name = REG_NUMBER.sub("", row).strip(" -,")
        label, _, rest = name.partition(":")
        if rest and not COMPANY_SUFFIX.search(label.upper()):
            name = rest.strip()  # "Owned by: X" -> "X"
        if (name.count("(") > name.count(")") or name.endswith("&")) and i + 1 < len(raw):
            name = f"{name} {REG_NUMBER.sub('', raw[i + 1]).strip()}"  # name continues on next row
        suffixes = list(COMPANY_SUFFIX.finditer(name.upper()))
        if (
            suffixes
            and i > 0
            and sum(c.isalpha() for c in COMPANY_SUFFIX.sub("", name.upper())) < 3
        ):
            name = f"{raw[i - 1].strip()} {name}"  # "POPULAR BOOK" / "CO. (M) SDN BHD"
            suffixes = list(COMPANY_SUFFIX.finditer(name.upper()))
        if suffixes:
            candidates.append((0.95, i, name[: suffixes[-1].end()].strip()))  # cut text glued after
        elif (
            sum(c.isalpha() for c in name) >= 4
            and not name.islower()
            and not JUNK_MERCHANT.search(name.upper())
        ):
            candidates.append((0.7, i, name))
    if not candidates:
        return Field()
    weight, i, name = max(candidates, key=lambda c: (c[0], -c[1]))  # suffix first, then top-most
    return Field(value=name, confidence=round(weight * conf[i], 3), source_row=i)


def _date(rows: list[str], conf: list[float], profile: TaxProfile) -> Field[date]:
    for i in sorted(range(len(rows)), key=lambda i: "DATE" not in rows[i]):  # labelled dates first
        for pattern, order in DATE_PATTERNS:
            pos = 0
            while m := pattern.search(rows[i], pos):
                pos = m.start() + 1  # step one char, so "19-18/03/2018" still finds 18/03/2018
                a, b, c = m.groups()
                if order == "ymd":
                    y, mo, d = int(a), int(b), int(c)
                elif order == "dmy":
                    d, mo, y = int(a), MONTHS.index(b) + 1, int(c)
                else:
                    d, mo = (int(b), int(a)) if profile.date_order == "mdy" else (int(a), int(b))
                    y = int(c)
                try:
                    value = date(y + 2000 if y < 100 else y, mo, d)
                except ValueError:
                    continue
                ambiguous = (  # only a guess when the region's date order is unknown
                    order == "a"
                    and int(a) <= 12
                    and int(b) <= 12
                    and a != b
                    and profile.date_order == "unknown"
                )
                return Field(
                    value=value,
                    confidence=round((0.7 if ambiguous else 0.95) * conf[i], 3),
                    source_row=i,
                )
    return Field()


def extract(ocr: OcrResult, profile: TaxProfile) -> ExtractResult:
    raw = [" ".join(r.split()) for r in ocr.text.splitlines()]  # collapse repeated spaces
    rows = [r.upper() for r in raw]
    conf = [
        min((ln.confidence for ln in ocr.lines if ln.row == i), default=0.0)
        for i in range(len(rows))
    ]

    currency = Field(value=profile.default_currency, confidence=0.5)
    for i, row in enumerate(rows):
        if m := CURRENCY.search(row):
            currency = Field(value=CURRENCIES[m.group(1)], confidence=0.95, source_row=i)
            break

    cash = _find_amount(rows, conf, CASH_RULES, re.compile(r"CHANGE"))
    change = _find_amount(rows, conf, CHANGE_RULES)
    return ExtractResult(
        merchant=_merchant(raw, conf),
        date=_date(rows, conf, profile),
        total=_total(rows, conf, cash, change),
        subtotal=_find_amount(rows, conf, SUBTOTAL_RULES),
        tax=_find_amount(rows, conf, TAX_RULES, NOT_TAX),
        cash=cash,
        change=change,
        currency=currency,
    )
