# Image Privacy Cleaner — Windows MVP

Windows-only local image privacy tool.

## Implemented

- JPG/JPEG/PNG/WEBP/BMP/TIFF intake
- EXIF tag count, GPS flag and ICC-profile inspection
- EXIF orientation normalization
- Metadata-stripped re-encoding
- Optional PNG flattening
- Optional manual black redaction by pixel rectangles (`x,y,width,height; ...`)

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
