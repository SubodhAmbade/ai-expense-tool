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


@lru_cache
def _engine() -> RapidOCR:
    return RapidOCR()  # loads the models once per process


def run_ocr(source: str | Path | BinaryIO) -> OcrResult:
    start = time.perf_counter()
    image = ImageOps.exif_transpose(Image.open(source)).convert("RGB")  # undo phone rotation
    image.thumbnail((MAX_SIDE, MAX_SIDE))
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
