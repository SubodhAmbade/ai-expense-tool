"""OCR stage: receipt image -> text lines (with confidence and position) in reading order.

CLI: python -m app.ocr <image-or-folder>   writes <image>.ocr.json next to each image.
"""

import sys
import time
from functools import lru_cache
from pathlib import Path
from typing import BinaryIO

import numpy as np
from PIL import Image, ImageOps
from pydantic import BaseModel
from rapidocr import RapidOCR

MAX_SIDE = 2000  # px; larger photos are shrunk to keep OCR fast without losing small print
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


class OcrLine(BaseModel):
    text: str
    confidence: float
    box: list[list[int]]  # 4 corners, clockwise from top-left
    row: int  # index of the text row this box belongs to


class OcrResult(BaseModel):
    engine: str = "rapidocr"
    duration_ms: int
    lines: list[OcrLine]  # reading order: top to bottom, left to right
    text: str  # lines on the same row joined by spaces, rows by newlines


# Tuned to fit a 512 MB server. On SROIE test receipts 350-449, with the reduced JPEG decode below:
# peak memory 708 -> 361 MB, 3.7 -> 2.2 s per receipt, same accuracy (eval/memory_check.py).
# Reading 2 text lines at a time instead of 6 is the big saving; receipts are photographed upright,
# so the rotation model is skipped.
ENGINE_SETTINGS = {
    "Det.limit_type": "max",  # text detection at most 960 px on the long side
    "Det.limit_side_len": 960,
    "Global.use_cls": False,  # no 180-degree rotation check
    "Rec.rec_batch_num": 2,  # text lines recognised per batch
}


@lru_cache
def _engine() -> RapidOCR:
    return RapidOCR(params=ENGINE_SETTINGS)  # loads the models once per process


def run_ocr(source: str | Path | BinaryIO) -> OcrResult:
    start = time.perf_counter()
    image = Image.open(source)
    # JPEG: decode straight at a reduced size, so a 12-30 megapixel phone photo never sits in memory
    # full size (SROIE 423, 4854x6712, added 170 MB). Still at least MAX_SIDE, so no detail is lost.
    image.draft("RGB", (MAX_SIDE, MAX_SIDE))
    if image.mode in (
        "1",
        "P",
    ):  # thumbnail can't smooth black-and-white or palette images: text goes jagged
        image = image.convert(
            "L" if image.mode == "1" else "RGBA" if "transparency" in image.info else "RGB"
        )
    # Shrink before rotating and converting: PNG and WebP can't decode small, so this keeps it to a
    # single full-size copy (the upload's pixel limit bounds that copy).
    image.thumbnail((MAX_SIDE, MAX_SIDE))
    image = ImageOps.exif_transpose(image)  # undo phone rotation
    if (
        "A" in image.getbands()
    ):  # transparent areas would turn black: put the receipt on white paper
        image = Image.alpha_composite(Image.new("RGBA", image.size, "white"), image.convert("RGBA"))
    image = image.convert("RGB")
    out = _engine()(np.asarray(image))

    # RapidOCR returns None (not empty lists) when the image has no text.
    lines = (
        [
            OcrLine(
                text=t,
                confidence=round(float(s), 3),
                box=np.asarray(b).astype(int).tolist(),
                row=-1,  # set once the rows are grouped below
            )
            for b, t, s in zip(out.boxes, out.txts, out.scores, strict=True)
        ]
        if out.boxes is not None
        else []
    )

    # Group boxes into rows: a box joins the current row if its vertical centre lies within
    # half a line-height of the row's first box. Receipts print label and amount as separate
    # boxes ("TOTAL" ... "12.50"), so this is what makes the text usable for extraction.
    rows: list[list[OcrLine]] = []
    for line in sorted(lines, key=lambda ln: ln.box[0][1] + ln.box[2][1]):
        centre = (line.box[0][1] + line.box[2][1]) / 2
        if rows:
            first = rows[-1][0]
            first_centre = (first.box[0][1] + first.box[2][1]) / 2
            if abs(centre - first_centre) < (first.box[2][1] - first.box[0][1]) / 2:
                rows[-1].append(line)
                continue
        rows.append([line])
    rows = [sorted(row, key=lambda ln: ln.box[0][0]) for row in rows]
    for i, row in enumerate(rows):
        for ln in row:
            ln.row = i

    return OcrResult(
        duration_ms=round((time.perf_counter() - start) * 1000),
        lines=[ln for row in rows for ln in row],
        text="\n".join(" ".join(ln.text for ln in row) for row in rows),
    )


if __name__ == "__main__":
    target = Path(sys.argv[1])
    images = (
        sorted(p for p in target.iterdir() if p.suffix.lower() in IMAGE_SUFFIXES)
        if target.is_dir()
        else [target]
    )
    for path in images:
        result = run_ocr(path)
        path.with_suffix(".ocr.json").write_text(result.model_dump_json(indent=2), "utf-8")
        n = len(result.lines)
        mean = sum(ln.confidence for ln in result.lines) / max(n, 1)
        print(f"{path.name}: {n} lines, mean conf {mean:.2f}, {result.duration_ms} ms")
