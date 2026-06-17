# Stage 2.7 Simple Template Report

## Goal

Create a simplified DOCX template without dependency on header/footer content.

Source template:

`CV_sample_v2.docx`

New template:

`CV_sample_v3_simple.docx`

## What Was Done

- Created `CV_sample_v3_simple.docx` as a copy-derived simplified template.
- Moved the branded top header into the document body as an image paragraph using `logo_1.png`.
- Removed header/footer references from `word/document.xml` section properties.
- Left header parts empty/static:
  - `word/header1.xml`
  - `word/header2.xml`
- Removed dependency on `word/_rels/header2.xml.rels` image binding.
- Kept resume body tables unchanged.

## Why Header Was Inserted As Image, Not Table

The current generator addresses resume tables by fixed table indexes.

If the old header table were inserted into the body as a table, all table indexes would shift and the generator could fill the wrong blocks.

To keep generator compatibility, the branded header was inserted as a body image paragraph, not as a new table.

## Template Checks

`CV_sample_v3_simple.docx`:

- ZIP/DOCX structure: OK
- `unzip -t`: OK
- Tables in body: `6`
- Header references: `0`
- Footer references: `0`
- Body drawings: `2`
  - header image `logo_1.png`
  - candidate photo placeholder `image1.jpeg`
- Media:
  - `word/media/image1.jpeg`
  - `word/media/logo_1.png`
- Missing relationships: none
- Duplicate relationship IDs: none

## Generator Compatibility Test

The existing generator was tested without changing `app.py` by temporarily pointing it to:

`CV_sample_v3_simple.docx`

Generated test file:

`tests/reports/stage2_7/generated_with_v3_simple.docx`

Input file:

`Start/HH_01.docx`

Result:

- `/upload`: `200`
- `/save`: `200`
- DOCX starts with `PK`
- `unzip -t`: OK
- Tables in generated DOCX: `6`
- Header references: `0`
- Footer references: `0`
- Missing relationships: none
- Duplicate relationship IDs: none
- Empty `<w:t/>`: `0`
- Empty `<w:trPr/>`: `0`
- `w14:paraId/textId`: `0`

Content markers present in generated DOCX:

- `Васин Вадим Сергеевич`: present
- `Исполнительный директор`: present
- `245 000`: present
- `СВЕДЕНИЯ О ПРЕДЫДУЩЕЙ ЗАНЯТОСТИ`: present

## Comparison With Old Template

Old template:

- Firm header is in `word/header2.xml`.
- `word/document.xml` has header references.
- Header image is connected through `word/_rels/header2.xml.rels`.

New template:

- Firm header is in `word/document.xml` body.
- `word/document.xml` has no header references.
- Header image is connected through `word/_rels/document.xml.rels`.
- Resume body table count remains unchanged, so the old generator can still address the same resume tables.

## Visual QA

LibreOffice/soffice is not available in this environment, so automatic render-to-PNG visual QA could not be completed here.

Structural DOCX checks passed. Final visual verification should be done by opening:

`CV_sample_v3_simple.docx`

and generated file:

`tests/reports/stage2_7/generated_with_v3_simple.docx`

in Microsoft Word.

## Conclusion

`CV_sample_v3_simple.docx` is ready for manual Word review.

No changes were made to:

- `app.py`
- frontend/Tilda
- API
- HH parser

Next possible step after Word review:

- if the template opens cleanly and the generated file opens cleanly, switch the generator from `CV_sample_v2.docx` to `CV_sample_v3_simple.docx` in a separate app.py change.
