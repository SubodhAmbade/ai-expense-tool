from datetime import date
from decimal import Decimal

from app.config import get_settings
from app.extract import ExtractResult, Field
from app.tax_profiles import load_tax_profiles
from app.validate import validate

MY = load_tax_profiles(get_settings().tax_profiles_path)["my"]
TODAY = date(2026, 1, 1)


def receipt(**amounts: str | None) -> ExtractResult:
    """A confidently read receipt; each amount (given as a string) sits on its own row."""
    money = {
        k: Field(value=Decimal(v), confidence=0.9, source_row=i)
        for i, (k, v) in enumerate(amounts.items())
        if v
    }
    return ExtractResult(
        merchant=Field(value="SHOP SDN BHD", confidence=0.95),
        date=Field(value=date(2018, 3, 1), confidence=0.95),
        currency=Field(value="MYR", confidence=0.95),
        **{k: money.get(k, Field()) for k in ("total", "subtotal", "tax", "cash", "change")},
    )


def test_total_confirmed_by_arithmetic_is_accepted_even_at_low_confidence() -> None:
    r = receipt(subtotal="8.49", tax="0.51", total="9.00")
    r.total.confidence = 0.5
    assert validate(r, MY, TODAY).status == "auto_accept"


def test_tax_inclusive_prices_and_cash_check_pass() -> None:
    inclusive = validate(receipt(subtotal="28.60", tax="0.07", total="28.60"), MY, TODAY)
    cash = validate(receipt(total="28.60", cash="100.00", change="71.40"), MY, TODAY)
    assert inclusive.status == cash.status == "auto_accept"


def test_unconfirmed_or_inconsistent_totals_go_to_review() -> None:
    alone = validate(receipt(total="0.42"), MY, TODAY)
    mismatch = validate(receipt(subtotal="8.49", tax="0.51", total="1.42"), MY, TODAY)
    tax_is_total = validate(
        receipt(tax="8.48", total="8.48", cash="10.00", change="1.52"), MY, TODAY
    )
    assert "total not confirmed" in alone.reasons[0]
    assert mismatch.status == tax_is_total.status == "needs_review"


def test_cash_check_skipped_when_total_was_worked_out_from_cash() -> None:
    r = receipt(cash="30.00", change="6.00")
    r.total = Field(value=Decimal("24.00"), confidence=0.6, source_row=r.cash.source_row)
    result = validate(r, MY, TODAY)
    assert next(c for c in result.checks if c.name == "cash").passed is None
    assert result.status == "needs_review"


def test_impossible_date_fails_sanity() -> None:
    r = receipt(subtotal="8.49", tax="0.51", total="9.00")
    r.date.value = date(2060, 2, 4)
    assert validate(r, MY, TODAY).status == "needs_review"
