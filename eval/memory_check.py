"""How much memory and time the API needs, stage by stage: does it fit a 512 MB server?

Runs the pipeline in one process, as the API does, and prints resident memory (RSS) and peak
after each stage. Linux reads /proc (what servers run); macOS uses the resource module; Windows
needs `pip install psutil` and counts memory a little differently, so compare the steps between
stages, not the totals.
    python eval/memory_check.py <folder of receipt images> [count] [bert]
Reads the JPEG, PNG and WebP files in the folder; put a large PNG in it to check the PNG path.
Add "bert" to also load the embedding model (EMBED_MODEL picks which).
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "api"))


def memory() -> str:
    proc = Path("/proc/self/status")
    if proc.exists():  # Linux
        status = dict(line.split(":", 1) for line in proc.read_text().splitlines() if ":" in line)
        now, peak = (int(status[k].split()[0]) // 1024 for k in ("VmRSS", "VmHWM"))
        return f"{now:4d} MB now, {peak:4d} MB peak"
    import psutil

    info = psutil.Process().memory_info()
    if hasattr(info, "peak_wset"):  # Windows
        peak = f"{info.peak_wset // 2**20:4d} MB"
    else:  # macOS: the resource module's high-water mark, in bytes there
        import resource

        peak = f"{resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 2**20:4d} MB"
    return f"{info.rss // 2**20:4d} MB now, {peak} peak"


def stage(name: str, started: float) -> None:
    print(f"{name:<44} {memory()}   {time.perf_counter() - started:6.2f} s")


folder, options = Path(sys.argv[1]), sys.argv[2:]
count = next((int(o) for o in options if o.isdigit()), 10)
with_bert = "bert" in options
images = sorted(
    p for p in folder.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
)
images = images[:count]

t = time.perf_counter()
from app.categorise import by_examples, by_rules, embed  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.extract import extract  # noqa: E402
from app.main import app  # noqa: E402, F401  (the whole API, as uvicorn would load it)
from app.ocr import run_ocr  # noqa: E402
from app.tax_profiles import load_tax_profiles  # noqa: E402
from app.validate import validate  # noqa: E402

stage("API imported", t)

profile = load_tax_profiles(get_settings().tax_profiles_path)["my"]
texts = []
t = time.perf_counter()
run_ocr(images[0])
stage("OCR models loaded, first receipt read", t)

t = time.perf_counter()
for path in images:
    ocr = run_ocr(path)
    validate(extract(ocr, profile), profile)
    by_rules(ocr.text)
    texts.append(ocr.text)
stage(f"{len(images)} receipts: OCR + extract + validate + rules", t)
print(f"{'':<44} {(time.perf_counter() - t) / len(images):.2f} s per receipt")

if not with_bert:
    sys.exit()

t = time.perf_counter()
embed(["warm up"])
stage("BERT (bge-small) loaded", t)

t = time.perf_counter()
vectors = embed(texts)
stage(f"BERT: {len(texts)} receipts embedded", t)
print(f"{'':<44} {(time.perf_counter() - t) / len(texts):.2f} s per receipt")

t = time.perf_counter()
by_examples(vectors[0], vectors[1:], ["meals"] * (len(texts) - 1))
stage("nearest-example vote", t)
