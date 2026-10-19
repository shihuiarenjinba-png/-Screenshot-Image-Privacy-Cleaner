"""No source replacement and lossless redaction verification."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from windows_app import clean_image, image_sha256


class ImagePrivacyProductTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = self.root / "private.png"
        Image.new("RGB", (80, 80), (210, 140, 80)).save(self.source)

    def test_lossless_output_and_original_unchanged(self):
        source_hash = image_sha256(self.source)
        output = clean_image(self.source, self.root / "results",
                             [(10, 10, 40, 40)], True)
        self.assertNotEqual(output, self.source)
        self.assertEqual(source_hash, image_sha256(self.source))
        with Image.open(output) as exported:
            self.assertEqual(exported.getpixel((20, 20)), (0, 0, 0))
            self.assertEqual(exported.getpixel((60, 60)), (210, 140, 80))

    def test_mutation_during_export_removes_new_copy(self):
        import windows_app as target
        original = target.verify_redactions
        def mutate_input(*args, **kwargs):
            original(*args, **kwargs)
            Image.new("RGB", (80, 80), (0, 0, 0)).save(self.source)
        with patch("windows_app.verify_redactions", side_effect=mutate_input):
            with self.assertRaisesRegex(ValueError, "changed during export"):
                clean_image(self.source, self.root / "results",
                            [(10, 10, 40, 40)], True)
        self.assertFalse(list((self.root / "results").glob("*_clean.png")))

    def test_existing_output_never_replaced(self):
        destination = self.root / "results"
        destination.mkdir()
        existing = destination / "private_clean.png"
        existing.write_bytes(b"someone else's file")
        with self.assertRaises(FileExistsError):
            clean_image(self.source, destination, [], True)
        self.assertEqual(existing.read_bytes(), b"someone else's file")


if __name__ == "__main__":
    unittest.main()
