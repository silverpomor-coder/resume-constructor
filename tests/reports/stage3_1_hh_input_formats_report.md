# Stage 3.1: HH input formats diagnostics and fix

## Scope

Fixed backend upload handling for HH files where the visible extension does not match the real file format.

Code changed:
- `app.py`

Not changed:
- frontend / Tilda
- DOCX generation
- `shablon.docx`
- `fill_template_v3()`
- successful `/upload` response contract

## Test files

Requested files `Метлин Иван.doc` and `Метлин Иван.rtf` were not found in `Start/Тест`.

Checked available analogs:
- `Start/Тест/Сорокин Константин.doc`
- `Start/Тест/Муравьев Роман.doc`
- `Start/Тест/TAB_02.rtf`

Diagnostic outputs:
- `tests/reports/stage3_1_hh_input_formats/stage3_1_test_results.json`
- `tests/reports/stage3_1_hh_input_formats/Сорокин Константин_text.txt`
- `tests/reports/stage3_1_hh_input_formats/Муравьев Роман_text.txt`
- `tests/reports/stage3_1_hh_input_formats/TAB_02_text.txt`

## What changed

### Format detection by content

`normalize_to_text()` now checks file bytes before extension:
- `{\\rtf` -> RTF
- `PK` -> DOCX/ODT ZIP
- `%PDF` -> unsupported PDF JSON error
- `D0 CF 11 E0 A1 B1 1A E1` -> old binary DOC
- HTML prefixes -> HTML text extraction

This fixes HH files named `.doc` that are actually RTF.

### RTF Windows-1251 extraction

`rtf_to_text()` now reads RTF directly and respects `\\ansicpgNNN`, including CP1251.

Added safe post-processing for HH text boundaries:
- HH section headers
- month/year work periods
- glued salary values
- glued year fragments in education/courses

### Upload errors

`/upload` now catches text extraction errors and returns JSON:

```json
{"error": "..."}
```

instead of HTML 500.

### HH parsing adjustments

Small safe fixes:
- FIO is cleaned when glued with `Резюме обновлено ...`
- HH experience block is selected by real work periods
- HH periods without dash are accepted, for example `Июль 2018 Сентябрь 2025`
- leading `:` after labels is removed

## Test results

### `Сорокин Константин.doc`

Actual format: RTF inside `.doc`.

`/upload`:
- status: 200
- response: JSON

Recognized:
- FIO: `Сорокин Константин`
- role: `Управляющий загородным домом`
- salary: `160 000 ₽ на руки`
- citizenship: `Россия, есть разрешение на работу: Россия`
- birth date: `30 июня 1983`
- education level: `ПТУ-27`
- jobs: 2

### `Муравьев Роман.doc`

Actual format: RTF inside `.doc`.

`/upload`:
- status: 200
- response: JSON

Recognized:
- FIO: `Муравьев Роман`
- role: `Персональный водитель руководителя, Помощник по хозяйству, Управляющий.`
- salary: `200 000 ₽ на руки`
- citizenship: `Россия, есть разрешение на работу: Россия`
- birth date: `27 мая 1979`
- education level: `Среднее специальное`
- jobs: 6

### `TAB_02.rtf`

Actual format: RTF.

`/upload`:
- status: 200
- response: JSON

Recognized:
- role: `Домработница/ВИП-горничная/ВИП-гардероб`
- salary: `100 000`
- citizenship: `Россия, есть разрешение на работу: Россия`
- education level: `Высшее`
- jobs: 3

FIO and birth date were not reliably extracted from this specific file because it contains WordML/legacy hyperlink noise inside RTF.

### PDF

Backend PDF extraction is not available in current dependencies.

Fake PDF upload test:
- status: 400
- response: JSON
- error: `PDF пока не поддерживается. Загрузите резюме в DOC, DOCX, RTF или TXT.`

PDF was not enabled in frontend `accept`.

## Checks

Command:

```bash
PYTHONPYCACHEPREFIX=/tmp/constructor_resume_pycache python3 -m py_compile app.py
```

Result: passed.

## Conclusion

Stage 3.1 backend fix is complete:
- HH `.doc` files that are actually RTF now upload successfully.
- HH `.rtf` files now extract readable CP1251 text.
- `/upload` returns JSON errors instead of HTML 500.
- PDF is intentionally not enabled yet because backend PDF text extraction is not implemented.
