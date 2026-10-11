# Image Privacy Cleaner — Windows MVP

Windows-only local image privacy tool.

## Implemented

- JPG/JPEG/PNG/WEBP/BMP/TIFF intake
- Privacy/content-bearing EXIF tag count, GPS flag and ICC-profile inspection. Required TIFF pixel-layout tags are reported separately as structural tags and do not trigger an EXIF privacy warning.
- EXIF orientation normalization
- Metadata-stripped re-encoding
- Optional PNG flattening
- Optional manual black redaction by pixel rectangles (`x,y,width,height; ...`)

## Orientation and redaction coordinates

The cleaner applies EXIF orientation to the pixels first and then removes the orientation tag. The cleaned file therefore preserves the image's displayed orientation; its raw width/height may swap for 90-degree orientations. Redaction rectangles are interpreted in this normalized, displayed coordinate space. Tests compare the cleaned pixels against `exif_transpose` output rather than against the unrotated raw pixel matrix.

No image content is uploaded anywhere by this implementation.

## Run

```powershell
py -3 -m pip install pillow
py -3 .\windows_app.py
```

## Build

```powershell
powershell -ExecutionPolicy Bypass -File .\build-windows-portable.ps1
```

Output: `dist\ImagePrivacyCleaner.exe`

## Sales note

Automatic OCR, face detection and QR detection are not claimed in this MVP. Those features require separate detection engines and release tests. Before sale verify metadata removal on fixture images, redaction coordinates, Windows 10/11, malware scan, Authenticode signing and SHA256.
