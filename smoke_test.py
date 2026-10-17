from pathlib import Path
import tempfile
from PIL import Image

from windows_app import inspect_image, clean_image, scale_preview_rectangle

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

    # Drag mapping must honor source scale, reverse dragging and clipping.
    assert scale_preview_rectangle((10, 20), (30, 50), (100, 100), (400, 200)) == (40, 40, 120, 100)
    assert scale_preview_rectangle((30, 50), (10, 20), (100, 100), (400, 200)) == (40, 40, 120, 100)
    assert scale_preview_rectangle((-10, -10), (1000, 1000), (100, 100), (400, 200)) == (0, 0, 400, 200)
    try:
        scale_preview_rectangle((10, 10), (10, 20), (100, 100), (400, 200))
    except ValueError:
        pass
    else:
        raise AssertionError("Zero-area drag must be refused")

    # The user's previous cleaned export must never be silently replaced.
    original_export_bytes = out.read_bytes()
    try:
        clean_image(src, root / "out", [(0, 0, 5, 5)], True)
    except FileExistsError:
        pass
    else:
        raise AssertionError("Existing cleaned output must not be overwritten")
    assert out.read_bytes() == original_export_bytes

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
