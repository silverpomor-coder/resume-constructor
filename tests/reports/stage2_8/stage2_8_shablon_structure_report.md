# Stage 2.8 shablon.docx Structure Report

## Technical Check
- `zip_ok`: `True`
- `xml_errors`: `[]`
- `relationship_missing_targets`: `[]`
- `relationship_duplicate_ids`: `[]`
- `content_types_ok`: `True`
- `header_files`: `[]`
- `footer_files`: `[]`
- `header_refs_in_document`: `0`
- `footer_refs_in_document`: `0`
- `media_files`: `['word/media/image1.png']`
- `w14_stats_document`: `[{'attr': 'paraId', 'total': 0, 'unique': 0, 'duplicate_values': 0}, {'attr': 'textId', 'total': 0, 'unique': 0, 'duplicate_values': 0}]`
- `empty_trPr_document`: `0`
- `empty_text_nodes_document`: `0`
- `empty_or_format_only_runs_document`: `0`
- `table_count`: `5`

## Project Field Compatibility
Current project fields used for comparison:
- `role`
- `salary`
- `fio`
- `citizenship`
- `birth_place_date`
- `family`
- `registration`
- `location`
- `metro`
- `criminal_record`
- `languages`
- `medical_book`
- `driving`
- `agency_comment`
- `education_level`
- `education`
- `courses`
- `recommendations`
- `photo`
- `jobN_period`, `jobN_city`, `jobN_description` for previous employment

Fields not found by text keywords in the new template:
- `role`
- `medical_book`
- `courses`

Possible new/unsupported labels found in template:
- none detected by keyword scan

## Table Map

### Table 0
- Rows: `6`
- Cell counts by row: `[1, 2, 2, 3, 3, 3]`
- Has merged cells: `True`
- Has images: `False`
- Empty rows: `[0]`
- Row 0: cells=1; class=`empty`; merged=`True`; images=`False`
  - Cell 0 (gridSpan=3): [empty]
- Row 1: cells=2; class=`single_text_row`; merged=`True`; images=`False`
  - Cell 0: Ожидаемый размер оплаты
  - Cell 1 (gridSpan=2): [empty]
- Row 2: cells=2; class=`possible_header_or_block`; merged=`True`; images=`False`
  - Cell 0 (gridSpan=2): Сведения о кандидате
  - Cell 1 (vMerge=restart): ФОТО
- Row 3: cells=3; class=`single_text_row`; merged=`True`; images=`False`
  - Cell 0: ФИО
  - Cell 1: [empty]
  - Cell 2 (vMerge=continue): [empty]
- Row 4: cells=3; class=`single_text_row`; merged=`True`; images=`False`
  - Cell 0: ГРАЖДАНСТВО
  - Cell 1: [empty]
  - Cell 2 (vMerge=continue): [empty]
- Row 5: cells=3; class=`single_text_row`; merged=`True`; images=`False`
  - Cell 0: ДАТА РОЖДЕНИЯ И ВОЗРАСТ
  - Cell 1: [empty]
  - Cell 2 (vMerge=continue): [empty]

### Table 1
- Rows: `8`
- Cell counts by row: `[1, 2, 2, 2, 2, 2, 2, 2]`
- Has merged cells: `True`
- Has images: `False`
- Empty rows: `[]`
- Row 0: cells=1; class=`single_text_row`; merged=`True`; images=`False`
  - Cell 0 (gridSpan=2): ПЕРСОНАЛЬНЫЕ ДАННЫЕ
- Row 1: cells=2; class=`single_text_row`; merged=`False`; images=`False`
  - Cell 0: Семейное положение, дети
  - Cell 1: [empty]
- Row 2: cells=2; class=`single_text_row`; merged=`False`; images=`False`
  - Cell 0: Место регистрации
  - Cell 1: [empty]
- Row 3: cells=2; class=`single_text_row`; merged=`False`; images=`False`
  - Cell 0: Место фактического проживания
  - Cell 1: [empty]
- Row 4: cells=2; class=`single_text_row`; merged=`False`; images=`False`
  - Cell 0: Метро/станция электрички
  - Cell 1: [empty]
- Row 5: cells=2; class=`single_text_row`; merged=`False`; images=`False`
  - Cell 0: Наличие судимости
  - Cell 1: [empty]
- Row 6: cells=2; class=`single_text_row`; merged=`False`; images=`False`
  - Cell 0: Владение иностранными языками
  - Cell 1: [empty]
- Row 7: cells=2; class=`single_text_row`; merged=`False`; images=`False`
  - Cell 0: Водительские права, стаж, собственный автомобиль
  - Cell 1: [empty]

### Table 2
- Rows: `3`
- Cell counts by row: `[2, 2, 2]`
- Has merged cells: `False`
- Has images: `False`
- Empty rows: `[1, 2]`
- Row 0: cells=2; class=`possible_header_or_block`; merged=`False`; images=`False`
  - Cell 0: ОБРАЗОВАНИЕ
  - Cell 1: УЧЕБНОЕ ЗАВЕДЕНИЕ, ГОД ОКОНЧАНИЯ
- Row 1: cells=2; class=`empty`; merged=`False`; images=`False`
  - Cell 0: [empty]
  - Cell 1: [empty]
- Row 2: cells=2; class=`empty`; merged=`False`; images=`False`
  - Cell 0: [empty]
  - Cell 1: [empty]

### Table 3
- Rows: `4`
- Cell counts by row: `[1, 2, 2, 2]`
- Has merged cells: `True`
- Has images: `False`
- Empty rows: `[1, 2, 3]`
- Row 0: cells=1; class=`possible_header_or_block`; merged=`True`; images=`False`
  - Cell 0 (gridSpan=2): СВЕДЕНИЯ О ПРЕДЫДУЩЕЙ ЗАНЯТОСТИ
- Row 1: cells=2; class=`empty`; merged=`False`; images=`False`
  - Cell 0: [empty]
  - Cell 1: [empty]
- Row 2: cells=2; class=`empty`; merged=`False`; images=`False`
  - Cell 0: [empty]
  - Cell 1: [empty]
- Row 3: cells=2; class=`empty`; merged=`False`; images=`False`
  - Cell 0: [empty]
  - Cell 1: [empty]

### Table 4
- Rows: `4`
- Cell counts by row: `[1, 2, 1, 1]`
- Has merged cells: `True`
- Has images: `False`
- Empty rows: `[3]`
- Row 0: cells=1; class=`possible_header_or_block`; merged=`True`; images=`False`
  - Cell 0 (gridSpan=2): РЕКОМЕНДАЦИИ ПРЕЖНИХ НАНИМАТЕЛЕЙ
- Row 1: cells=2; class=`single_text_row`; merged=`False`; images=`False`
  - Cell 0: Наличие
  - Cell 1: [empty]
- Row 2: cells=1; class=`possible_header_or_block`; merged=`True`; images=`False`
  - Cell 0 (gridSpan=2): КОММЕНТАРИЙ АГЕНТСТВА
- Row 3: cells=1; class=`empty`; merged=`True`; images=`False`
  - Cell 0 (gridSpan=2): [empty]

## Draft Mapping Summary
Draft JSON map: `tests/reports/stage2_8/shablon_template_map_draft.json`

Field candidates:
- `salary`: table 0, row 1
- `fio`: table 0, row 3
- `citizenship`: table 0, row 4
- `birth_place_date`: table 0, row 5
- `family`: table 1, row 1
- `registration`: table 1, row 2
- `location`: table 1, row 3
- `metro`: table 1, row 4
- `criminal_record`: table 1, row 5
- `languages`: table 1, row 6
- `driving`: table 1, row 7
- `agency_comment`: table 4, row 2
- `education_level`: table 2, row 0
- `education`: table 2, row 0
- `recommendations`: table 4, row 0
- `photo`: table 0, row 2

Dynamic block candidates:
- `education_courses_candidate`: table `2` (table text contains education/course keywords)
- `previous_employment_candidate`: table `3` (table text contains employment/work keywords)

## Generator Adaptation Notes
- Current `fill_template()` cannot be safely switched to this template blindly; it uses table indexes and row/cell positions from the old template.
- Next stage should adapt `fill_template()` only after this map is approved.
- Previous employment is likely the main dynamic block and needs explicit row-copy rules.
- Photo location must be confirmed visually; structural analysis can only identify image cells/placeholders.

## Conclusion
`shablon.docx` passed structural DOCX checks and can proceed to mapping review.
No code changes were made in this stage.