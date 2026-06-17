# Stage 2.4 DOCX Sanitizer Report

## Context

Branch: `format-stabilization-server`

Goal: apply minimal DOCX sanitation after Word Recovery diagnostics.

No frontend, HH parser, template, API contract, photo logic, or RTF export changes were made.

## Changed Files

- `app.py`

## Code Changes

Added or changed:

- `remove_empty_row_properties(root)`:
  removes empty `<w:trPr/>` from `word/document.xml` table rows.
- `should_clean_word_generated_ids(part_name)`:
  selects DOCX XML parts where Word-generated IDs should be removed.
- `clean_word_generated_ids_in_parts(files)`:
  removes `w14:paraId` and `w14:textId` from:
  - `word/document.xml`
  - `word/header*.xml`
  - `word/footer*.xml`
  - `word/footnotes.xml`
  - `word/endnotes.xml`
- `clear_row_height(row)`:
  now removes empty `<w:trPr/>` if row height removal leaves it empty.
- `fill_template()`:
  now runs document cleanup before writing the final DOCX.

## Test File

Generated file:

`tests/reports/stage2_4/server_save_stage2_4.docx`

## POST /save Result

- HTTP status: `200`
- Content-Type: `application/vnd.openxmlformats-officedocument.wordprocessingml.document`
- Body prefix: `PK\x03\x04`

## ZIP Check

Result:

`No errors detected in compressed data of tests/reports/stage2_4/server_save_stage2_4.docx.`

## XML Check

All checked XML files are valid.

Checked:

- `[Content_Types].xml`
- `word/document.xml`
- `word/header1.xml`
- `word/header2.xml`
- `word/footnotes.xml`
- `word/endnotes.xml`
- relationship files

## Relationships Check

- Missing relationship targets: none
- Duplicate relationship IDs: none
- Unresolved XML relationship references: none

## Content Types Check

- `[Content_Types].xml`: valid

## Word Generated IDs

All checked files now have zero `w14:paraId` and `w14:textId`.

Checked files:

- `word/document.xml`
- `word/header1.xml`
- `word/header2.xml`
- `word/footnotes.xml`
- `word/endnotes.xml`

Result:

- `paraId`: total `0`
- `textId`: total `0`
- duplicate values: `0`

## Empty Row Properties

Stage 2.3 original DOCX:

- empty `<w:trPr/>`: `13`

Stage 2.3 recovered DOCX:

- empty `<w:trPr/>`: `0`

Stage 2.4 generated DOCX:

- empty `<w:trPr/>`: `0`

## Content Markers

The generated document still contains key resume data:

- `Васин Вадим Сергеевич`: present
- `Исполнительный директор`: present
- `245 000`: present
- `Высшее`: present
- `Индустрия Поволжья`: present
- `СВЕДЕНИЯ О ПРЕДЫДУЩЕЙ ЗАНЯТОСТИ`: present

## Media

Media files in generated DOCX:

- `word/media/image2.png`

No broken media relationship was found.

## Conclusion

The minimal DOCX sanitation is applied successfully:

- empty `<w:trPr/>` removed;
- Word-generated `w14:paraId` / `w14:textId` removed from all relevant DOCX XML parts;
- ZIP structure is valid;
- XML files are valid;
- relationships are valid;
- resume content is preserved.

Next safe step: deploy this branch to the server and generate a fresh DOCX through the real API. After that, the file can be checked in Microsoft Word.
