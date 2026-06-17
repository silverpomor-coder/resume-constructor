# Stage 2.6.1 Word Recovery Diff Report

## Files
- Original: `tests/reports/stage2_6_1_word_recovery/original_server_save_stage2_6_1.docx`
- Recovered: `tests/reports/stage2_6_1_word_recovery/recovery_2_6.docx`
- Original ZIP: `True`
- Recovered ZIP: `True`

## Package changes
- Original count: `21`
- Recovered count: `21`
- Added by Word: `['word/media/image1.png']`
- Removed by Word: `['word/media/image2.png']`
- Changed common files: `['[Content_Types].xml', 'docProps/app.xml', 'docProps/core.xml', 'word/_rels/document.xml.rels', 'word/_rels/header2.xml.rels', 'word/document.xml', 'word/endnotes.xml', 'word/footnotes.xml', 'word/header1.xml', 'word/header2.xml', 'word/settings.xml']`

## XML validation
- XML parse errors: none

## document.xml sanitation counters
- empty `<w:trPr/>` original/recovered: `0` / `0`
- empty `<w:t/>` original/recovered: `0` / `0`
- empty or format-only `<w:r>` original/recovered: `0` / `0`
- w14 original: `[('paraId', 0, 0, 0), ('textId', 0, 0, 0)]`
- w14 recovered: `[('paraId', 0, 0, 0), ('textId', 0, 0, 0)]`

## Tag counts
- `tbl` original/recovered: `6` / `6`
- `tr` original/recovered: `36` / `36`
- `tc` original/recovered: `69` / `69`
- `p` original/recovered: `316` / `316`
- `r` original/recovered: `306` / `307`
- `t` original/recovered: `306` / `307`
- `trPr` original/recovered: `17` / `17`
- `tcPr` original/recovered: `69` / `69`
- `pPr` original/recovered: `314` / `314`
- `rPr` original/recovered: `620` / `621`
- `drawing` original/recovered: `0` / `0`
- `blip` original/recovered: `0` / `0`
- `sectPr` original/recovered: `1` / `1`
- `headerReference` original/recovered: `2` / `2`

## Relationships
### word/_rels/document.xml.rels
- original: rels=11, duplicate=[], missing=[]
  - original: `{'Id': 'rId12', 'Type': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme', 'Target': 'theme/theme1.xml'}`
  - original: `{'Id': 'rId11', 'Type': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/fontTable', 'Target': 'fontTable.xml'}`
  - original: `{'Id': 'rId10', 'Type': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/header', 'Target': 'header2.xml'}`
  - original: `{'Id': 'rId9', 'Type': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/header', 'Target': 'header1.xml'}`
- recovered: rels=11, duplicate=[], missing=[]
  - recovered: `{'Id': 'rId8', 'Type': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/header', 'Target': 'header1.xml'}`
  - recovered: `{'Id': 'rId11', 'Type': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme', 'Target': 'theme/theme1.xml'}`
  - recovered: `{'Id': 'rId10', 'Type': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/fontTable', 'Target': 'fontTable.xml'}`
  - recovered: `{'Id': 'rId9', 'Type': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/header', 'Target': 'header2.xml'}`
### word/_rels/header2.xml.rels
- original: rels=1, duplicate=[], missing=[]
  - original: `{'Id': 'rId1', 'Type': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/image', 'Target': 'media/image2.png'}`
- recovered: rels=1, duplicate=[], missing=[]
  - recovered: `{'Id': 'rId1', 'Type': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/image', 'Target': 'media/image1.png'}`

## Media
- original: `[('image2.png', 82857, '20959ac36acf6347')]`
- recovered: `[('image1.png', 82857, '20959ac36acf6347')]`

Diff saved: `tests/reports/stage2_6_1_word_recovery/[Content_Types].xml.diff.txt`

Diff saved: `tests/reports/stage2_6_1_word_recovery/word___rels__document.xml.rels.diff.txt`

Diff saved: `tests/reports/stage2_6_1_word_recovery/word___rels__header2.xml.rels.diff.txt`

Diff saved: `tests/reports/stage2_6_1_word_recovery/word__document.xml.diff.txt`

Diff saved: `tests/reports/stage2_6_1_word_recovery/word__header2.xml.diff.txt`

Diff saved: `tests/reports/stage2_6_1_word_recovery/word__settings.xml.diff.txt`