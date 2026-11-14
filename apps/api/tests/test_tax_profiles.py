from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.config import get_settings
from app.tax_profiles import TaxProfile, load_tax_profiles


def test_profiles_load_as_exact_decimals() -> None:
    profiles = load_tax_profiles(get_settings().tax_profiles_path)
    assert {"generic", "ch"} <= profiles.keys()
    assert profiles["ch"].rates["standard"] == Decimal("0.081")
    assert profiles["ch"].default_currency == "CHF"


def test_profile_without_rates_is_rejected_at_load() -> None:
    with pytest.raises(ValidationError, match="at least one rate"):
        TaxProfile(code="x", name="x", default_currency="EUR", rates={})
