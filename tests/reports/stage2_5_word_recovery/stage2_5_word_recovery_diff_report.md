# Stage 2.5 Word Recovery Diff Report

## Context

Microsoft Word for Mac still opened `server_save_stage2_5.docx` in recovery mode.

User saved the recovered file as:

`recovery_5_5.docx`

Both files were copied into:

`tests/reports/stage2_5_word_recovery/`

## Files

- Original: `tests/reports/stage2_5_word_recovery/original_server_save_stage2_5.docx`
- Recovered: `tests/reports/stage2_5_word_recovery/recovery_5_5.docx`

## Package Check

- Original file count: `21`
- Recovered file count: `21`
- ZIP structure: readable in both files
- XML structure: valid in checked files

## Key Differences

Word changed these common files:

- `[Content_Types].xml`
- `docProps/app.xml`
- `docProps/core.xml`
- `word/_rels/document.xml.rels`
- `word/_rels/header2.xml.rels`
- `word/document.xml`
- `word/endnotes.xml`
- `word/footnotes.xml`
- `word/header1.xml`
- `word/header2.xml`
- `word/settings.xml`

## Empty Table Row Properties

The previous suspected issue is fixed:

- Empty `<w:trPr/>` in original Stage 2.5 DOCX: `0`
- Empty `<w:trPr/>` in recovered DOCX: `0`

## Word Generated IDs

The previous suspected issue is fixed:

- `w14:paraId` in checked files: `0`
- `w14:textId` in checked files: `0`

Checked:

- `word/document.xml`
- `word/header1.xml`
- `word/header2.xml`
- `word/footnotes.xml`
- `word/endnotes.xml`

## Remaining Important Difference

The original DOCX contains empty text nodes:

- Empty `<w:t />` in `word/document.xml`: `9`
- Empty `<w:t />` after Word recovery: `0`

Word removed these empty text runs during recovery.

This is now the strongest remaining technical suspect.

## Header Image Difference

Word also renamed the header image:

- Original: `word/media/image2.png`
- Recovered: `word/media/image1.png`

The image bytes are identical:

- Original hash prefix: `20959ac36acf6347`
- Recovered hash prefix: `20959ac36acf6347`

Word also updated:

- `word/_rels/header2.xml.rels`

from:

`Target="media/image2.png"`

to:

`Target="media/image1.png"`

This looks like Word normalization, not image corruption.

## Header Relationships

Word renumbered header relationships:

Original:

- default header: `rId9`
- first header: `rId10`

Recovered:

- default header: `rId8`
- first header: `rId9`

This may be related to the earlier fixed `rId8` photo placeholder design, but no missing relationship target or duplicate relationship ID was found.

## Relationships

- Missing relationship targets: none
- Duplicate relationship IDs: none
- Broken media references: none

## Current Conclusion

Stage 2.4 fixed:

- empty `<w:trPr/>`;
- duplicated/generated `w14:paraId` / `w14:textId`.

Word still enters recovery mode.

The strongest remaining suspect is:

- empty `<w:t />` nodes in `word/document.xml`.

## Minimal Next Fix

Stage 2.6 should add one more small sanitizer:

- remove empty `<w:t />` nodes;
- if a `<w:r>` becomes empty except for formatting after removing `<w:t />`, remove that empty run too;
- keep real empty paragraphs if they are used for layout.

Do not change frontend, Tilda, HH parser, DOCX template, or RTF logic for this fix.
