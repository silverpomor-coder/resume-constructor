# Stage 2.9.1 mc:Ignorable Fix Report

## Problem

After switching to `shablon.docx`, Microsoft Word still opened the generated DOCX through recovery.

Diagnostics showed that the generator rewrote `word/document.xml` and removed namespace declarations, but left this attribute:

`mc:Ignorable="w14 w15 w16se w16cid w16 w16cex w16sdtdh w16sdtfl w16du wp14"`

As a result, `mc:Ignorable` referenced XML prefixes that no longer existed in the generated `word/document.xml` root tag.

## Safe Fix

Changed `app.py` only.

Added:

- `MC_NS`
- `remove_markup_compatibility_ignorable(root)`

Updated:

- `sanitize_document_xml(root, files)` now removes `mc:Ignorable` from generated `word/document.xml`.

No changes were made to:

- frontend/Tilda
- API
- HH parser
- RTF
- `shablon.docx`
- old `CV_sample_v2.docx`

## Test DOCX

Generated:

`tests/reports/stage2_9_1/generated_with_shablon_stage2_9_1.docx`

Input:

`Start/HH_01.docx`

## API Test

- `/upload`: `200`
- `/save`: `200`
- DOCX starts with `PK`

## Technical Checks

- ZIP/DOCX: OK
- `unzip -t`: OK
- XML: OK
- relationships: OK
- `[Content_Types].xml`: OK
- header references: `0`
- footer references: `0`
- empty `<w:trPr/>`: `0`
- empty `<w:t/>`: `0`
- empty or format-only `<w:r>`: `0`
- `w14:paraId`: `0`
- `w14:textId`: `0`

## mc:Ignorable Check

After fix:

- `mc:Ignorable`: absent
- missing ignorable prefixes: none
- `mc:Ignorable` text in root tag: false

## Content Markers

Present in generated DOCX:

- FIO
- role / должность
- salary
- education
- courses
- previous employment
- recommendations
- agency comment

## Conclusion

The known XML namespace defect is fixed.

Next step: open `generated_with_shablon_stage2_9_1.docx` in Microsoft Word on Mac and check whether recovery is still triggered.
