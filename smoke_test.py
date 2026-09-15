from pathlib import Path
import tempfile
from PIL import Image

from windows_app import inspect_image, clean_image

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    src = root / "sample.jpg"
    image = Image.new("RGB", (64, 64), "white")
    exif = Image.Exif()
    exif[270] = "private description"
    exif[315] = "private author"
    image.save(src, quality=90, exif=exif, icc_profile=b"private-icc-profile")

    info = inspect_image(src)
    assert info["size"] == (64, 64)
    assert info["exif_tags"] >= 2
    assert info["icc"] is True

    out = clean_image(src, root / "out", [(5, 5, 15, 15)], True)
    assert out.exists() and out.suffix.lower() == ".png"
    with Image.open(out) as cleaned:
        assert cleaned.size == (64, 64)
        assert len(cleaned.getexif()) == 0
        assert "icc_profile" not in cleaned.info
        pixel = cleaned.convert("RGB").getpixel((10, 10))
        assert pixel == (0, 0, 0)

    jpg_out = clean_image(src, root / "jpeg-out", [], False)
    with Image.open(jpg_out) as cleaned_jpg:
        assert len(cleaned_jpg.getexif()) == 0
        assert "icc_profile" not in cleaned_jpg.info

print("Image Privacy Cleaner smoke test: OK")
