# Market / OSS reference audit — 2026-11-20

Product: **Image Privacy Cleaner**

## References reviewed
- Microsoft Presidio Image Redactor: image PII redaction assisted by OCR/PII detection, with the broader Presidio warning that automated detection is not complete.
  - https://github.com/microsoft/presidio
- ExifTool ecosystem: widely used tooling for reading/removing image metadata; metadata removal is distinct from pixel-content redaction.
  - https://exiftool.org/

## Decisions for this product
- Keep metadata removal and visible-region redaction as separate user-visible operations/statuses.
- Never treat “no OCR/automatic finding” as proof that an image is safe.
- Preserve human preview/selection for redaction and output to a new file.
- Re-open/re-inspect exported metadata where feasible and report what was actually removed.
- Avoid a single generic “clean” badge when only one privacy layer was processed.
- Treat this document as design evidence only; no third-party code was copied.

## Remaining release evidence
- Real Windows tests for JPG/PNG/WebP and EXIF/GPS-bearing fixtures.
- Verify redacted pixels and metadata in the exported copy while original bytes remain unchanged.
- DPI/visual QA, exact Store version/assets, QA_UNSIGNED MSIX and manifest/hash evidence.
