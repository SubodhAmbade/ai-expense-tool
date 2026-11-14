from decimal import Decimal

from app.config import get_settings
from app.tax_profiles import load_tax_profiles


def test_profiles_load_as_exact_decimals() -> None:
    profiles = load_tax_profiles(get_settings().tax_profiles_path)
    assert {"generic", "ch"} <= profiles.keys()
    assert profiles["ch"].rates["standard"] == Decimal("0.081")
    assert profiles["ch"].default_currency == "CHF"
