# Stage 2.9 shablon.docx Generator Report

## Goal

Adapt DOCX generation to the clean template:

`shablon.docx`

No frontend, API, HH parser, RTF, or old `CV_sample_v2.docx` deletion was done.

## Backup

Backup folder:

`tests/reports/stage2_9/backup_before_stage2_9/`

Backed up:

- `app.py`
- `shablon.docx`
- `CV_sample_v2.docx`

## Changed Files

- `app.py`

New template file used by the generator:

- `shablon.docx`

Important Git note:

- `shablon.docx` is currently untracked and must be added explicitly when committing.

## New Generator Function

Added:

- `fill_template_v3(data, output_path, photo_path=None)`

Kept as fallback:

- `fill_template_legacy(data, output_path, photo_path=None)`

Current `fill_template()` behavior:

- uses `fill_template_v3()` if `shablon.docx` exists;
- otherwise falls back to `fill_template_legacy()`.

## Table Fill Map

### Table 0

- Row 0, cell 0: `role` / должность
- Row 1, cell 1: `salary` / ожидаемый размер оплаты
- Row 2, cell 1: photo area
- Row 3, cell 1: `fio`
- Row 4, cell 1: `citizenship`
- Row 5, cell 1: `birth_place_date`, converted through `age_text()`

### Table 1

- Row 1, cell 1: `family`
- Row 2, cell 1: `registration`
- Row 3, cell 1: `location`
- Row 4, cell 1: `metro`
- Row 5, cell 1: `criminal_record`
- Row 6, cell 1: `languages`
- Row 7, cell 1: `driving`

### Table 2

- Row 1, cell 0: `education_level`
- Row 1, cell 1: `education`
- Row 2, cell 0: static label `Повышение квалификации, курсы`
- Row 2, cell 1: `courses`

### Table 3

Previous employment block.

Dynamic rows are expanded by current job count.

For each job:

- left cell: `jobN_period` with calculated duration;
- right cell: cleaned job summary from `jobN_city` and `jobN_description`.

### Table 4

- Row 1, cell 1: `recommendations`
- Row 3, cell 0: `agency_comment`

## Fields Without Safe Place In New Template

- `medical_book`

It is still present in JSON/frontend, but `shablon.docx` has no separate row for it.

## Photo Handling

Added helper logic for the new template:

- `update_template_photo_v3()`
- `set_cell_picture()`
- `build_inline_picture()`

If photo is passed to `/save`, it is inserted into the photo cell in Table 0.

Photo test file:

`tests/reports/stage2_9/generated_with_shablon_stage2_9_photo.docx`

Result:

- `/upload-photo`: `200`
- `/save`: `200`
- `unzip -t`: OK
- media contains:
  - `word/media/image1.png`
  - `word/media/candidate_photo.png`

## Sanitizer

The new generator still applies existing DOCX sanitation:

- removes `w14:paraId`;
- removes `w14:textId`;
- removes empty `<w:trPr/>`;
- removes empty `<w:t/>`;
- removes empty or format-only `<w:r>`.

## Test DOCX

Generated file:

`tests/reports/stage2_9/generated_with_shablon_stage2_9.docx`

Input file:

`Start/HH_01.docx`

## API Test Results

- `POST /upload`: `200`
- `POST /save`: `200`
- DOCX body starts with `PK`

## Technical Checks

- ZIP/DOCX: `True`
- XML errors: `[]`
- Missing relationship targets: `[]`
- Duplicate relationship IDs: `[]`
- `[Content_Types].xml` valid: `True`
- Header files: `[]`
- Footer files: `[]`
- Header references in document: `0`
- Footer references in document: `0`
- Empty `<w:trPr/>`: `0`
- Empty `<w:t/>`: `0`
- Empty or format-only `<w:r>`: `0`
- `w14` stats: `[['word/document.xml', 'paraId', 0, 0, 0], ['word/document.xml', 'textId', 0, 0, 0]]`

## Content Markers

- FIO present: `True`
- Role present: `True`
- Salary present: `True`
- Education header present: `True`
- Courses label present: `True`
- Employment header present: `True`
- Job marker present: `True`
- Recommendations header present: `True`
- Agency comment header present: `True`

## Table Shape After Generation

- Table count: `5`
- Rows by table: `[6, 8, 3, 14, 4]`
- Cell counts: `[[1, 2, 2, 3, 3, 3], [1, 2, 2, 2, 2, 2, 2, 2], [2, 2, 2], [1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2], [1, 2, 1, 1]]`
- Media: `['word/media/image1.png']`
- Drawing count: `1`
- Blip count: `1`

## Conclusion

`generated_with_shablon_stage2_9.docx` is technically healthy by structural checks.

It can be passed to the user for Microsoft Word opening test.

Do not deploy to VPS until the local Word test confirms that the file opens without recovery.
