"""Per-region tax profiles. Rates live in config/tax_profiles.yaml, never in code."""

from decimal import Decimal
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, field_validator


class TaxProfile(BaseModel):
    code: str
    name: str
    default_currency: str
    # How to read dates like 03/04/2025. "unknown" reads day-first but marks such dates for review.
    date_order: Literal["dmy", "mdy", "unknown"] = "unknown"
    rates: dict[str, Decimal]

    @field_validator("rates")
    @classmethod
    def rates_in_range(cls, v: dict[str, Decimal]) -> dict[str, Decimal]:
        for name, rate in v.items():
            if not Decimal("0") <= rate < Decimal("1"):
                raise ValueError(f"rate '{name}' must be a fraction between 0 and 1, got {rate}")
        return v


def load_tax_profiles(path: Path) -> dict[str, TaxProfile]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    # Rates are read as strings so they become exact Decimals, not floats.
    return {
        code: TaxProfile(code=code, **{**p, "rates": {k: str(r) for k, r in p["rates"].items()}})
        for code, p in raw["profiles"].items()
    }
