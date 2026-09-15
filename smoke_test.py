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

    tiff = root / "日本語.tiff"
    Image.new("RGB", (40, 40), "white").save(tiff, format="TIFF", icc_profile=b"private-icc")
    tiff_info = inspect_image(tiff)
    assert tiff_info["icc"] is True
    tiff_out = clean_image(tiff, root / "tiff-out", [], False)
    with Image.open(tiff_out) as cleaned_tiff:
        cleaned_tiff.load()
        assert "icc_profile" not in cleaned_tiff.info

    corrupt = root / "corrupt.png"
    corrupt.write_bytes(b"\x89PNG\r\n\x1a\ntruncated")
    try:
        inspect_image(corrupt)
    except Exception:
        pass
    else:
        raise AssertionError("Corrupt image must be rejected")

    unsupported = root / "fake.gif"
    Image.new("RGB", (16, 16), "white").save(unsupported, format="GIF")
    try:
        inspect_image(unsupported)
    except ValueError:
        pass
    else:
        raise AssertionError("Unsupported image extension must be rejected")

print("Image Privacy Cleaner smoke test: OK")
