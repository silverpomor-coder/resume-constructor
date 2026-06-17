# Stage 3.1 Input Format Diagnostics Report

## Scope

No code, frontend, backend, Tilda, or parser changes were made.

Report folder:

`tests/reports/stage3_1_input_format_diagnostics/`

Problem file copied to:

`tests/reports/stage3_1_input_format_diagnostics/Сорокин Константин.doc`

## Problem File

- Name: `Сорокин Константин.doc`
- Original path: `Start/Тест/Сорокин Константин.doc`
- Extension: `.doc`
- Size: `93806` bytes

### `file` result

```text
Сорокин Константин.doc: Rich Text Format data, version 1, ANSI, code page 1251, default language ID 1049
```

### First 64 bytes

```text
00000000: 7b5c 7274 6631 5c61 6e73 695c 616e 7369  {\rtf1\ansi\ansi
00000010: 6370 6731 3235 315c 6465 6666 305c 6465  cpg1251\deff0\de
00000020: 666c 616e 6731 3034 397b 5c66 6f6e 7474  flang1049{\fontt
00000030: 626c 7b5c 6630 5c66 7377 6973 735c 6670  bl{\f0\fswiss\fp
```

### Byte checks

```text
size: 93806
first_32_bytes: b'{\\rtf1\\ansi\\ansicpg1251\\deff0\\de'
starts_rtf: True
starts_zip: False
starts_doc_ole: False
starts_html: False
```

## Actual Format

Despite the `.doc` extension, the actual file format is:

`RTF`

The file starts with:

```text
{\rtf1\ansi\ansicpg1251...
```

It is not DOC OLE, DOCX ZIP, HTML, or TXT.

## Other Checked `.doc` Files

RTF files with `.doc` extension:

- `Start/Тест/Сорокин Константин.doc`
- `Start/Тест/Муравьев Роман.doc`
- `WIN_relise/Start/test_Муратова.doc`
- `WIN_relise/Start/test_Катунина.doc`

True binary DOC OLE files:

- `Start/Тест/TAB_02.doc`
- `Start/Тест/TEXT_01.doc`
- `Start/Дьяченко_Ольга_Владимировна.doc`
- `Start/Короткова Елизавета.doc`

Conclusion: this is not a unique case. HH-style exports can appear as `.doc` while actually being RTF.

## `/upload` Reproduction

Local Flask test client result on Mac:

```text
Start/Тест/Сорокин Константин.doc: status=200; content_type=application/json; body_prefix=b'{"data":{"_job_count":0,"agency_comment":"","birth_place_date":"30 \\u0438\\u044e\\u043d\\u044f 1983","citizenship":"\\u0420\\u043e\\u0441\\u0441\\u0438\\u044f, \\u0435\\u0441\\u0442\\u044c \\u0440\\u0430\\u0437\\u0440\\u0435\\u0448\\u0435\\u043d\\u0438\\u0435 \\u043d\\u0430 \\u0440\\u0430\\u0431\\u043e\\u0442\\u0443: \\u0420\\u043e\\u0441\\u0441\\u0438\\u044f","courses":"","criminal_record":"","driving":"\\u0418\\u043c\\u0435\\u0435\\u0442\\u0441\\u044f \\u0441\\u043e\\u0431\\u0441\\u0442\\u0432\\u0435\\u043d\\u043d\\u044b\\u0439 \\u0430\\u0432\\u0442\\'
Start/Тест/Муравьев Роман.doc: status=200; content_type=application/json; body_prefix=b'{"data":{"_job_count":6,"agency_comment":"","birth_place_date":"27 \\u043c\\u0430\\u044f 1979","citizenship":"\\u0420\\u043e\\u0441\\u0441\\u0438\\u044f, \\u0435\\u0441\\u0442\\u044c \\u0440\\u0430\\u0437\\u0440\\u0435\\u0448\\u0435\\u043d\\u0438\\u0435 \\u043d\\u0430 \\u0440\\u0430\\u0431\\u043e\\u0442\\u0443: \\u0420\\u043e\\u0441\\u0441\\u0438\\u044f","courses":"2019\\n\\u041e\\u041e\\u041e\\"\\u0422\\u0438\\u0440-\\u0421\\u043f\\u043e\\u0440\\u0442\\u0438\\u043d\\u0433\\"\\n\\u041e\\u041e\\u041e\\"\\u0422\\u0438\\u0440-\\u0421\\u043f\\u043e\\u0440\\u0442\\u0'
WIN_relise/Start/test_Муратова.doc: status=200; content_type=application/json; body_prefix=b'{"data":{"_job_count":4,"agency_comment":"","birth_place_date":"5 \\u0430\\u043f\\u0440\\u0435\\u043b\\u044f 1972","citizenship":"\\u0420\\u043e\\u0441\\u0441\\u0438\\u044f, \\u0435\\u0441\\u0442\\u044c \\u0440\\u0430\\u0437\\u0440\\u0435\\u0448\\u0435\\u043d\\u0438\\u0435 \\u043d\\u0430 \\u0440\\u0430\\u0431\\u043e\\u0442\\u0443: \\u0420\\u043e\\u0441\\u0441\\u0438\\u044f","courses":"","criminal_record":"","driving":"\\u041f\\u0440\\u0430\\u0432\\u0430 \\u043a\\u0430\\u0442\\u0435\\u0433\\u043e\\u0440\\u0438\\u0438 B","education":"2017\\n\\u0412\\u04'
WIN_relise/Start/test_Катунина.doc: status=200; content_type=application/json; body_prefix=b'{"data":{"_job_count":4,"agency_comment":"","birth_place_date":"14 \\u0430\\u043f\\u0440\\u0435\\u043b\\u044f 1980","citizenship":"\\u0420\\u043e\\u0441\\u0441\\u0438\\u044f, \\u0435\\u0441\\u0442\\u044c \\u0440\\u0430\\u0437\\u0440\\u0435\\u0448\\u0435\\u043d\\u0438\\u0435 \\u043d\\u0430 \\u0440\\u0430\\u0431\\u043e\\u0442\\u0443: \\u0420\\u043e\\u0441\\u0441\\u0438\\u044f","courses":"2025\\n\\u041d\\u044f\\u043d\\u044f- \\u044d\\u0441\\u043f\\u0435\\u0440\\u0442\\n\\u0428\\u043a\\u043e\\u043b\\u0430 \\u0445\\u043e\\u0440\\u043e\\u0448\\u0438\\u0445 \\u043d\\'
```

Local `/upload` did not return 500 because macOS has `textutil`, and current `normalize_to_text()` uses `textutil` before extension-specific branches.

## VPS-Relevant Simulation

On VPS, `textutil` is not available. I simulated that locally by disabling `shutil.which()` during the test.

```text
Start/Тест/Сорокин Константин.doc [normal]: OK len=4549 sample=' \nСорокин Константин\nМужчина, 42 года, родился 30 июня 1983\n\n+7 (920) 8726714\nkrabov30061983@mail.ru — предпочитаемый сп'
Start/Тест/Сорокин Константин.doc [no_textutil]: ERROR RuntimeError: Не удалось прочитать старый DOC-файл
Start/Тест/Муравьев Роман.doc [normal]: OK len=6020 sample=' \nМуравьев Роман\nМужчина, 47 лет, родился 27 мая 1979\n\n+7 (925) 9398826 — предпочитаемый способ связи\ntvister.75@mail.ru'
Start/Тест/Муравьев Роман.doc [no_textutil]: ERROR RuntimeError: Не удалось прочитать старый DOC-файл
```

Result:

- with `textutil`: OK;
- without `textutil`: RTF disguised as `.doc` falls into `binary_doc_to_text()` and fails with `RuntimeError: Не удалось прочитать старый DOC-файл`.

This matches the likely cause of the 500 on VPS.

## Where `/upload` Falls

Likely path on VPS:

1. `/upload` saves uploaded file.
2. `normalize_to_text(source_path)` is called.
3. File suffix is `.doc`.
4. VPS has no `textutil`.
5. Code goes to `binary_doc_to_text(source_path)`.
6. File is actually RTF, not binary DOC OLE.
7. `binary_doc_to_text()` raises `RuntimeError("Не удалось прочитать старый DOC-файл")`.
8. The exception is not converted into a user-friendly JSON error, so the browser sees 500.

## Recommendations

### 1. Fix `normalize_to_text()`

Yes, a change is needed.

The function should detect file type by content, not only by extension.

Safe priority:

- if bytes start with RTF marker: use `rtf_to_text()`;
- if bytes start with `PK`: use DOCX/ODT ZIP path depending on ZIP contents;
- if bytes start with OLE signature `D0 CF 11 E0 A1 B1 1A E1`: use binary DOC logic;
- if bytes look like HTML: strip/parse HTML;
- otherwise fallback by extension.

### 2. Support `.doc` that is really RTF

Yes. This is needed for HH/email-downloaded files.

### 3. Replace HTML 500 with JSON error

Yes. `/upload` should catch read/parse errors and return JSON, for example:

```json
{"error": "Не удалось прочитать файл. Возможно, формат файла не соответствует расширению."}
```

with HTTP status `400`, not `500`.

## Final Conclusion

The problem is a repeated input-format issue:

HH/email files may have `.doc` extension but contain RTF data.

The next safe fix is to update file normalization to detect real format by file bytes before choosing the reader.
