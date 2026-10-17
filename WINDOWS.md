# Image Privacy Cleaner — Windows candidate

## Implemented in improvement branch

- Open JPG/JPEG/PNG/WEBP/BMP/TIFF images without uploading them.
- Select an image and drag over its **EXIF-orientation-corrected preview** to mark black-redaction rectangles; each file keeps its own selected regions.
- Clear the regions on the selected image. Optional **advanced** typed rectangles still apply globally to all selected files; leave that field blank unless you intend this.
- Re-encode images without passing through source EXIF or ICC metadata and optionally flatten to PNG.
- Re-open each processed image and check for GPS, ICC, and (except TIFF structural tags) remaining EXIF before recording successful export.
- Reject an existing output filename by exclusive creation; source files are not edited.
- Check output pixel and metadata behavior with the included smoke test, including scale mapping, reversed/cropped drags, and existing-output protection.

## Run and test on Windows

```powershell
py -3 -m pip install pillow
py -3 .\smoke_test.py
py -3 .\bilingual_smoke_test.py
py -3 .\windows_app.py
```

```powershell
powershell -ExecutionPolicy Bypass -File .\build-windows-portable.ps1
```

Build output: `dist\ImagePrivacyCleaner.exe` (portable, **not** a Microsoft Store MSIX).

## Safety limits

- Dragging draws opaque black pixels in the re-encoded output, **not** a guarantee that every sensitive detail in the image is discovered. Users must visually review the final output.
- Text recognition, face identification, QR detection and steganography detection are not implemented.
- Transparency is preserved or flattened according to file format/PNG option; users must verify actual appearance across viewers and for GIF/animation/multi-frame files (not supported for assured cleaning).
- Embedded payloads and all TIFF/vendor-specific metadata are not exhaustively certified absent. TIFF has structural tags that are not equivalent to sensitive EXIF.
- A generated image can remain sensitive even if EXIF/GPS/ICC flags are absent.
- Visible images, DPI scaling, 100/125/150% high-DPI mouse drag, huge images, invalid files, orientation, Unicode filenames, JPEG edge compression and alpha compositing require a real Windows GUI acceptance run.
- Existing output files are refused, not overwritten. A failed export can leave a reported output only if a post-save metadata recheck fails; do not share that file.

## Store release gate

**HOLD**. Portable EXE is a developer candidate only. Need Windows 10/11 manual GUI/DPI and end-to-end tests, verified MSIX identity and manifest, install/update/uninstall/optional WACK check and Store certification, complete commercial rights and third-party notices, signing/distribution method, screenshots, accurate privacy statements and product/bundle integration review.
