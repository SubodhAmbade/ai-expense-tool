"""Pipeline: one receipt photo -> a row ready to store. Runs the stages in order, nothing more."""

from io import BytesIO

from app.categorise import by_rules
from app.extract import extract
from app.ocr import run_ocr
from app.tax_profiles import TaxProfile
from app.validate import REVIEW_THRESHOLD, validate


def process(image: bytes, profile: TaxProfile) -> dict:
    ocr = run_ocr(BytesIO(image))
    fields = extract(ocr, profile)
    result = validate(fields, profile)
    category = by_rules(ocr.text)  # rules only until BERT's memory use is measured on Render

    reasons = list(result.reasons)
    if category.confidence < REVIEW_THRESHOLD:
        reasons.append(f"low confidence: category ({category.confidence:.2f})")

    amount = lambda f: None if f.value is None else str(f.value)  # noqa: E731 - exact, never float
    return {
        "status": "needs_review" if reasons else "confirmed",
        "raw_ocr_text": ocr.text,
        "merchant": fields.merchant.value,
        "receipt_date": fields.date.value.isoformat() if fields.date.value else None,
        "currency": fields.currency.value,
        "net_amount": amount(fields.subtotal),
        "tax_amount": amount(fields.tax),
        "total_amount": amount(fields.total),
        "tax_profile": profile.code,
        "totals_reconcile": next(c.passed for c in result.checks if c.name == "arithmetic"),
        "validation_errors": reasons,
        "checks": [c.model_dump() for c in result.checks],
        "extraction": fields.model_dump(mode="json"),
        "category": category.category,
        "category_source": "rule" if category.source == "rule" else "model",
        "category_confidence": category.confidence,
    }
