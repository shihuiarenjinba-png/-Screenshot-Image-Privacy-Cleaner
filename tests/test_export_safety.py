import tempfile
import unittest
from pathlib import Path
from PIL import Image
from windows_app import clean_image, inspect_image, verify_redactions


class ExportSafetyTests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.root = Path(self.t.name)
        self.source = self.root / 'source.png'
        self.output = self.root / 'out'
        self.output.mkdir()
        Image.new('RGBA', (20, 20), (240, 240, 240, 128)).save(self.source)

    def test_png_does_not_overwrite_existing_output(self):
        existing = self.output / 'source_clean.png'
        existing.write_bytes(b'important customer output')
        with self.assertRaises(FileExistsError):
            clean_image(self.source, self.output, [(2, 2, 8, 8)], False)
        self.assertEqual(existing.read_bytes(), b'important customer output')

    def test_rect_out_of_bounds_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'beyond image'):
            clean_image(self.source, self.output, [(0, 0, 50, 60)], True)
        self.assertFalse((self.output/'source_clean.png').exists())

    def test_pixel_redaction_is_opaque(self):
        result = clean_image(self.source, self.output, [(2, 2, 8, 8)], True)
        with Image.open(result) as im:
            self.assertEqual(im.convert('RGB').getpixel((4,4)), (0,0,0))
        checked = inspect_image(result)
        self.assertFalse(checked['gps'])
        self.assertFalse(checked['icc'])
        self.assertEqual(checked['exif_tags'], 0)

    def test_lossy_redaction_is_denied_without_png(self):
        jpeg = self.root / 'photo.jpg'
        Image.new('RGB', (20, 20), 'white').save(jpeg)
        with self.assertRaisesRegex(ValueError, 'lossless PNG'):
            clean_image(jpeg, self.output, [(2, 2, 8, 8)], False)
        self.assertFalse((self.output / 'photo_clean.jpg').exists())

    def test_post_export_pixel_verification_removes_bad_new_output(self):
        result = self.output / 'manipulated.png'
        Image.new('RGB', (20, 20), 'white').save(result)
        with self.assertRaisesRegex(ValueError, 'non-black'):
            verify_redactions(result, [(2, 2, 8, 8)])
        self.assertFalse(result.exists())

    def test_new_exif_metadata_not_copied(self):
        exif=Image.Exif()
        exif[305] = 'private software name'
        Image.new('RGB',(20,20),'red').save(self.source, format='PNG', exif=exif)
        result=clean_image(self.source,self.output,[],True)
        self.assertEqual(inspect_image(result)['exif_tags'],0)

    def test_multiframe_tiff_refused(self):
        source=self.root/'multi.tif'
        a=Image.new('RGB',(10,10),'white')
        b=Image.new('RGB',(10,10),'black')
        a.save(source, save_all=True, append_images=[b])
        with self.assertRaisesRegex(ValueError,'Multi-frame'):
            clean_image(source,self.output,[],False)
        self.assertFalse((self.output/'multi_clean.tif').exists())


if __name__=='__main__':
    unittest.main()
