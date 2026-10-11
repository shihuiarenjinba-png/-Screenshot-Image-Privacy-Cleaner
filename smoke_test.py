from pathlib import Path
import tempfile
from PIL import Image, ImageChops, ImageDraw, ImageOps, ImageStat

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
    assert tiff_info["raw_exif_tags"] > 0
    assert tiff_info["structural_tags"] > 0
    assert tiff_info["exif_tags"] == 0, tiff_info
    tiff_out = clean_image(tiff, root / "tiff-out", [], False)
    with Image.open(tiff_out) as cleaned_tiff:
        cleaned_tiff.load()
        assert "icc_profile" not in cleaned_tiff.info
    cleaned_tiff_info = inspect_image(tiff_out)
    assert cleaned_tiff_info["exif_tags"] == 0, cleaned_tiff_info

    tagged_tiff = root / "tagged.tiff"
    tiff_metadata = Image.Exif()
    tiff_metadata[270] = "private description"
    Image.new("RGB", (24, 16), "black").save(tagged_tiff, format="TIFF", exif=tiff_metadata)
    tagged_info = inspect_image(tagged_tiff)
    assert tagged_info["exif_tags"] >= 1, tagged_info

    oriented = root / "oriented.jpg"
    asymmetric = Image.new("RGB", (80, 40), "white")
    draw = ImageDraw.Draw(asymmetric)
    draw.rectangle((0, 0, 25, 15), fill="red")
    draw.rectangle((55, 20, 79, 39), fill="blue")
    orientation_exif = Image.Exif()
    orientation_exif[274] = 6
    asymmetric.save(oriented, format="JPEG", quality=98, exif=orientation_exif)
    with Image.open(oriented) as original:
        original.load()
        expected_visual = ImageOps.exif_transpose(original).convert("RGB")
    oriented_out = clean_image(oriented, root / "oriented-out", [], False)
    with Image.open(oriented_out) as cleaned_oriented:
        cleaned_oriented.load()
        actual_visual = cleaned_oriented.convert("RGB")
        assert actual_visual.size == expected_visual.size == (40, 80)
        difference = ImageChops.difference(expected_visual, actual_visual)
        mean_difference = sum(ImageStat.Stat(difference).mean) / 3
        assert mean_difference < 3.0, mean_difference
        assert len(cleaned_oriented.getexif()) == 0

    redacted_out = clean_image(oriented, root / "redacted-out", [(2, 3, 12, 13)], True)
    with Image.open(redacted_out) as redacted:
        redacted.load()
        assert redacted.size == expected_visual.size
        assert redacted.convert("RGB").getpixel((5, 5)) == (0, 0, 0)

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
