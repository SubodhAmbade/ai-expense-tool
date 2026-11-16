from datetime import date
from decimal import Decimal

from app.config import get_settings
from app.extract import TOTAL_RULES, extract
from app.ocr import OcrLine, OcrResult
from app.tax_profiles import load_tax_profiles

PROFILES = load_tax_profiles(get_settings().tax_profiles_path)


def ocr(*rows: str) -> OcrResult:
    lines = [OcrLine(text=r, confidence=1.0, box=[[0, 0]] * 4, row=i) for i, r in enumerate(rows)]
    return OcrResult(duration_ms=0, lines=lines, text="\n".join(rows))


def test_typical_receipt() -> None:
    result = extract(
        ocr(
            "tan woon yann",
            "BOOK TA .K (TAMAN DAYA) SDN BHD",
            "TEL: 07-3507405",
            "Date: 25/12/2018 8:13:39 PM",
            "SUBTOTAL 8.49",
            "GST 6% 0.51",
            "Total : 9.02",
            "Rounded Total (RM): 9.00",
            "Cash 10.00",
            "CHANGE 1.00",
        ),
        PROFILES["generic"],
    )
    assert result.merchant.value == "BOOK TA .K (TAMAN DAYA) SDN BHD"
    assert result.date.value == date(2018, 12, 25)
    assert result.total.value == Decimal("9.00")  # rounded total beats plain total and cash
    assert result.subtotal.value == Decimal("8.49")
    assert result.tax.value == Decimal("0.51")
    assert (result.currency.value, result.currency.confidence) == ("MYR", 0.95)


def test_ambiguous_date_and_currency_are_low_confidence() -> None:
    result = extract(ocr("CAFE ROMA", "03/04/2025", "TOTAL $ 12.50"), PROFILES["generic"])
    assert result.date.value == date(2025, 4, 3)  # generic profile reads day-first
    assert result.date.confidence < 0.8
    # a bare "$" is ambiguous, so the profile default is used, at low confidence
    assert (result.currency.value, result.currency.confidence) == ("USD", 0.5)


def test_missing_fields_are_empty_not_guessed() -> None:
    result = extract(ocr("THANK YOU"), PROFILES["ch"])
    assert result.total.value is None and result.date.value is None
    assert result.currency.value == "CHF" and result.currency.confidence == 0.5


def test_rounding_and_cash_rules() -> None:
    generic = PROFILES["generic"]
    rounding_after = extract(ocr("TOTAL AMT RM 60.31", "ROUNDING ADJ -0.01"), generic)
    rounding_before = extract(ocr("ROUNDING 0.02", "TOTAL 4.90"), generic)  # already included
    no_total = extract(ocr("CASH 100.00", "CHANGE 71.40"), generic)
    assert rounding_after.total.value == Decimal("60.30")
    assert rounding_before.total.value == Decimal("4.90")
    assert no_total.total.value == Decimal("28.60")
    misread = extract(ocr("CASH 20.00", "CHANGE 20.00"), generic)  # impossible: left for sanity
    assert misread.total.value == Decimal("0.00")


def test_tax_label_with_total_after_the_tax_name() -> None:
    for label in ("GST TOTAL", "GST  TOTAL", "TAX TOTAL", "TOTAL GST", "TAX DUE"):
        result = extract(ocr("SUBTOTAL 8.49", f"{label} 0.51", "TOTAL 9.00"), PROFILES["my"])
        assert result.tax.value == Decimal("0.51"), label
    with_gst = extract(ocr("Total with GST 41.48"), PROFILES["my"])  # a total, not the tax
    assert with_gst.tax.value is None


def test_rounded_total_printed_on_a_rounding_row() -> None:
    # SROIE 186: "ROUNDING RM 45.35" is the rounded total, not a 45.35 adjustment to add.
    result = extract(
        ocr(
            "TOTAL SALES (INCLUSIVE GST) RM 45.34",
            "ROUNDING ADJUSTMENT RM .01",
            "ROUNDING RM 45.35",
        ),
        PROFILES["my"],
    )
    assert result.total.value == Decimal("45.35")


def test_misread_rounding_adjustment_is_ignored() -> None:
    # Rounding moves a total by cents; "6.01" is an OCR slip for "0.01".
    result = extract(ocr("TOTAL SALES INCL GST 46.54", "ROUNDING ADJ 6.01"), PROFILES["my"])
    assert result.total.value == Decimal("46.54")


def test_total_after_adjustment_wins() -> None:
    result = extract(
        ocr("TOTAL SALES INCL GST 46.54", "ROUNDING ADJ 0.01", "TOTAL AFTER ADJ INCL GST 46.55"),
        PROFILES["my"],
    )
    assert result.total.value == Decimal("46.55")


def test_zero_amount_is_never_the_total() -> None:
    # SROIE 091: two OCR rows merged, leaving 0.00 as the right-most amount on the rule's row.
    result = extract(
        ocr("TOTAL 85.10", "ROUNDING ADJUSTMENT TOTAL AFTER ROUNDING 85.10 0.00"), PROFILES["my"]
    )
    assert result.total.value == Decimal("85.10")


def test_one_letter_ocr_slips_in_keywords() -> None:
    assert extract(
        ocr("TATAL SALES INCLUSIVE OF GST 32.70"), PROFILES["my"]
    ).total.value == Decimal("32.70")
    assert extract(ocr("TOTEL AMT POYABLE 8.50"), PROFILES["my"]).total.value == Decimal("8.50")


def test_tax_lines_and_tax_summary_are_not_the_total() -> None:
    result = extract(
        ocr(
            "PAY 25.15",
            "(TOTAL INCLUDED GST @ 6% 1.42)",  # the tax, not the total
            "GST SUMMARY AMOUNT TAX",
            "SR @ 6% 23.73 1.42",
            "TOTAL 23.73 1.42",  # the summary table's own total row
        ),
        PROFILES["my"],
    )
    assert result.total.value is None  # nothing safe to read: review, not a wrong number


def test_decimal_only_rounding_rows() -> None:
    for adjustment, total in [(".01", "10.02"), ("-.01", "10.00")]:
        result = extract(ocr("TOTAL 10.01", f"ROUNDING {adjustment}"), PROFILES["my"])
        assert result.total.value == Decimal(total)


def test_tax_summary_rows_do_not_round_the_total() -> None:
    result = extract(ocr("TOTAL 10.02", "GST SUMMARY", "ROUNDING ADJ -0.02"), PROFILES["my"])
    assert result.total.value == Decimal("10.02")


def test_total_that_includes_gst_is_still_a_total() -> None:
    result = extract(
        ocr("SUBTOTAL 100.00", "GST 6.00", "GRAND TOTAL INCLUDED GST 106.00"), PROFILES["my"]
    )
    assert result.total.value == Decimal("106.00")


def test_cafe_receipt_with_one_decimal_amounts() -> None:
    result = extract(
        ocr(
            "T305",
            "365 Cafe",
            "Order Time: 2024-04-30 15:13:24",
            "Milk Tea RM 680.0",
            "75% Sugar",
            "Subtotal RM 1,274.0",
            "Total Discount -RM 208.0",
            "Service Charge(10%) RM 127.4",
            "Amount RM 1,193.4",
            "PAID (CASH) RM 1,193.4",
            "Expiry Date: 3 November 2024 11:59:59PM",  # the e-invoice QR code, not the purchase
        ),
        PROFILES["my"],
    )
    assert result.date.value == date(2024, 4, 30)
    assert result.subtotal.value == Decimal("1274.00")
    assert result.total.value == Decimal("1193.40")
    assert result.total.confidence < 0.8  # a bare "Amount" label needs the cash line to agree
    assert result.cash.value == Decimal("1193.40")


def test_bare_amount_label_is_not_the_cash_tendered() -> None:
    bare_amount = TOTAL_RULES[-1][0]
    assert bare_amount.search("AMOUNT RM 1,193.4") and bare_amount.search("AMOUNT")
    for row in ["AMOUNT TENDERED RM 50.0", "AMOUNT PAID RM 50.0", "AMOUNT (RM)"]:
        assert not bare_amount.search(row)
    split = extract(ocr("Amount", "RM 45.3"), PROFILES["my"])  # label and amount on two rows
    assert split.total.value == Decimal("45.30")


def test_one_decimal_rounded_total_row() -> None:
    result = extract(ocr("TOTAL 45.32", "ROUNDING RM 45.3"), PROFILES["my"])
    assert result.total.value == Decimal("45.30")
