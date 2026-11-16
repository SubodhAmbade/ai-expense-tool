from io import BytesIO

import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFont

import app.ocr as ocr_module
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


def large_receipt(mode: str) -> BytesIO:
    """Black text, wider than MAX_SIDE so it gets shrunk, saved as PNG in the given mode."""
    transparent = mode == "RGBA"
    image = Image.new(
        "RGBA" if transparent else "RGB", (2600, 500), (0, 0, 0, 0) if transparent else "white"
    )
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=110)
    draw.text((80, 80), "TOTAL", fill="black", font=font)
    draw.text((1700, 80), "12.50", fill="black", font=font)
    buf = BytesIO()
    if not transparent:  # pure black and white, so any grey comes from smoothing on the way in
        image = image.convert("1").convert(mode)
    image.save(buf, format="PNG")
    return BytesIO(buf.getvalue())


def test_transparent_receipt_is_read_on_white() -> None:
    # Without a white backing, the transparent background turns black: black text on black.
    assert run_ocr(large_receipt("RGBA")).text.splitlines() == ["TOTAL 12.50"]


@pytest.mark.parametrize("mode", ["1", "P"])
def test_black_and_white_and_palette_images_are_shrunk_smoothly(mode: str, monkeypatch) -> None:
    # Shrunk in their own mode, these keep only pure black and white: jagged text. Catch the image
    # OCR receives and check the edges were smoothed into greys.
    seen = []

    class Engine:
        def __call__(self, pixels):
            seen.append(pixels)
            return type("Out", (), {"boxes": None, "txts": None, "scores": None})()

    monkeypatch.setattr(ocr_module, "_engine", lambda: Engine())
    run_ocr(large_receipt(mode))
    assert len(np.unique(seen[0])) > 2
