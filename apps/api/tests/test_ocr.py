from io import BytesIO

from PIL import Image, ImageDraw, ImageFont

from app.ocr import run_ocr


def test_label_and_amount_are_joined_into_one_row() -> None:
    image = Image.new("RGB", (900, 300), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=48)
    draw.text((40, 40), "COFFEE SHOP", fill="black", font=font)
    draw.text((40, 160), "TOTAL", fill="black", font=font)
    draw.text((600, 160), "12.50", fill="black", font=font)
    buf = BytesIO()
    image.save(buf, format="PNG")

    result = run_ocr(BytesIO(buf.getvalue()))

    assert result.text.splitlines() == ["COFFEE SHOP", "TOTAL 12.50"]
    assert all(0 <= ln.confidence <= 1 for ln in result.lines)
