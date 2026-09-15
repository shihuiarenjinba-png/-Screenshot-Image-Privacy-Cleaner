from pathlib import Path
import tempfile
from PIL import Image

from windows_app import inspect_image, clean_image

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    src = root / "sample.jpg"
    Image.new("RGB", (64, 64), "white").save(src, quality=90)
    info = inspect_image(src)
    assert info["size"] == (64, 64)
    out = clean_image(src, root / "out", [(5, 5, 15, 15)], True)
    assert out.exists() and out.suffix.lower() == ".png"
    with Image.open(out) as im:
        assert im.size == (64, 64)
print("Image Privacy Cleaner smoke test: OK")
