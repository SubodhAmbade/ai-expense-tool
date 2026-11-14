"""Validate stage: plain-code checks on extracted fields -> auto_accept or needs_review.

Nothing is auto-accepted unless every check that can run passes and every required field is
confident. A low-confidence total counts as confident when an independent check agrees with it.
"""

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

from app.extract import ExtractResult
from app.tax_profiles import TaxProfile

TOLERANCE = Decimal("0.05")  # largest rounding difference allowed between amounts
REVIEW_THRESHOLD = 0.8  # fields below this confidence need a person
EARLIEST_DATE = date(2000, 1, 1)
REQUIRED = ("merchant", "date", "total", "currency")


class Check(BaseModel):
    name: str
    passed: bool | None  # None = could not run because a field is missing
    detail: str


class ValidationResult(BaseModel):
    status: Literal["auto_accept", "needs_review"]
    checks: list[Check]
    reasons: list[str]  # why a person needs to look; empty when auto-accepted


def validate(
    result: ExtractResult, profile: TaxProfile, today: date | None = None
) -> ValidationResult:
    today = today or date.today()
    total, sub, tax = result.total.value, result.subtotal.value, result.tax.value
    cash, change = result.cash.value, result.change.value
    total_from_cash = (
        result.total.source_row is not None and result.total.source_row == result.cash.source_row
    )
    base = sub if sub is not None else total  # tax is checked against the subtotal, else the total
    max_rate = max(profile.rates.values())
    missing = [f for f in REQUIRED if getattr(result, f).value is None]

    # Two amounts that agree confirm each other. If an optional amount (tax, change) is missing,
    # agreement still counts but disagreement proves nothing, so the check returns None.
    arithmetic = cash_ok = None
    if total is not None and sub is not None:
        gap = abs(sub - total) if tax is None else min(abs(sub + tax - total), abs(sub - total))
        arithmetic = gap <= TOLERANCE or (None if tax is None else False)
    if total is not None and cash is not None and not total_from_cash:  # else it would be circular
        cash_ok = abs(cash - (change or 0) - total) <= TOLERANCE or (
            None if change is None else False
        )

    checks = [
        Check(
            name="required_fields",
            passed=not missing,
            detail=f"missing: {', '.join(missing) or 'none'}",
        ),
        Check(
            name="arithmetic",  # tax added on top (sub + tax) or already included in prices (sub)
            passed=arithmetic,
            detail=f"subtotal {sub} + tax {tax} vs total {total}",
        ),
        Check(
            name="tax_plausible",  # a range, not one rate, so mixed-rate receipts pass
            passed=None if None in (base, tax) else 0 <= tax <= base * max_rate + TOLERANCE,
            detail=f"tax {tax} within 0..{max_rate:.1%} of {base}",
        ),
        Check(
            name="cash",
            passed=cash_ok,
            detail=f"cash {cash} - change {change} vs total {total}",
        ),
        Check(
            name="sanity",
            passed=(total is None or total > 0)
            and (result.date.value is None or EARLIEST_DATE <= result.date.value <= today),
            detail=f"total {total} > 0, date {result.date.value} in {EARLIEST_DATE}..{today}",
        ),
    ]

    reasons = [f"check failed: {c.name} ({c.detail})" for c in checks if c.passed is False]
    if total is not None and not (arithmetic or cash_ok):
        reasons.append("total not confirmed by subtotal + tax or cash - change")
    reasons += [  # the total is judged by the checks above, the other fields by confidence
        f"low confidence: {f} ({getattr(result, f).confidence:.2f})"
        for f in REQUIRED
        if f != "total" and f not in missing and getattr(result, f).confidence < REVIEW_THRESHOLD
    ]
    return ValidationResult(
        status="needs_review" if reasons else "auto_accept", checks=checks, reasons=reasons
    )
