# Group C progress evidence — 2026-11-20

Product: **Image Privacy Cleaner**

## Validated source before this record
- Source HEAD: `5c3493d61649672a06deefe49dcd0cec2b8817b4`
- GitHub Actions run: `44685180269`
- build-portable: **SUCCESS**
- regression suite: **SUCCESS**
- packaged EXE self-test: **PASS**
- package-unsigned-msix: **SUCCESS**
- real Store candidate build: **SKIPPED by approval gate**

## QA-only package evidence
- Portable EXE SHA-256: `812AED1A5FF106F92D9AF5BEF40E92A58A86E5BB5339DF6B657664E9E7AF097E`
- QA version: `1.0.48.0` — workflow-generated, **NOT an approved Store version**
- Package: `ImagePrivacyCleaner_QA_UNSIGNED_1.0.48.0_x64.msix`
- MSIX SHA-256: `245E53F25BD1F9D18607BC97236878E719A6B185EC95CA5C4524BD612F58526E`
- Manifest identity check: **PASS**
- Artifact ID: `14605872886`
- Sales release: `HOLD`

## Current blockers for a real Store candidate
- package version approval is not OWNER_APPROVED
- brand assets approval is not OWNER_APPROVED
- approved Store version is missing
- approved asset directory and `store-assets/approval.json` are missing
- real image fixtures and Windows human DPI/visual acceptance remain separate

Do not upload the QA_UNSIGNED package as a production Store package.
