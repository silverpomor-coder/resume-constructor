# Stage 2.3 Word Recovery Diff Report

## Files

Original server DOCX:

```text
tests/reports/stage2_3/original_server_save_stage2_2.docx
```

Recovered Word DOCX:

```text
tests/reports/stage2_3/server_save_stage2_2_recovered.docx
```

Both files were unpacked:

```text
tests/reports/stage2_3/original_unpacked/
tests/reports/stage2_3/recovered_unpacked/
```

## ZIP / XML

Both DOCX files are valid ZIP archives.

`unzip -t` result for both files: no compressed data errors.

XML validation with `xmllint`: OK for both unpacked DOCX sets.

## Files Changed By Word Recovery

Word changed these files:

```text
[Content_Types].xml
docProps/app.xml
docProps/core.xml
word/_rels/document.xml.rels
word/_rels/header2.xml.rels
word/document.xml
word/endnotes.xml
word/footnotes.xml
word/header1.xml
word/header2.xml
word/settings.xml
```

Word did not change:

```text
word/styles.xml
word/numbering.xml
word/fontTable.xml
word/theme/theme1.xml
word/webSettings.xml
customXml/*
_rels/.rels
```

## Media Changes

Original:

```text
word/media/image2.png
```

Recovered:

```text
word/media/image1.png
```

The image bytes are identical. Word only renamed the image file and updated `word/_rels/header2.xml.rels`.

Original header image relationship:

```text
rId1 -> media/image2.png
```

Recovered header image relationship:

```text
rId1 -> media/image1.png
```

No missing media files were found.

## Relationships

Original relationships: no missing targets, no duplicate relationship IDs.

Recovered relationships: no missing targets, no duplicate relationship IDs.

Word renumbered some `document.xml.rels` IDs:

```text
Original default header: rId9 -> header1.xml
Original first header:   rId10 -> header2.xml

Recovered default header: rId8 -> header1.xml
Recovered first header:   rId9 -> header2.xml
```

This looks like Word cleanup after an unused old relationship ID gap, not a broken link.

## Content Types

Word removed this unused default content type:

```text
Default Extension="jpeg" ContentType="image/jpeg"
```

Reason: the generated DOCX no longer contains JPEG media. Only PNG remains.

No critical Content_Types problem found.

## document.xml

Important: `word/document.xml` in original already has no `w14:paraId` / `w14:textId` after Stage 2.1.

Original:

```text
paraId total=0 duplicate_values=0
textId total=0 duplicate_values=0
```

Recovered:

```text
paraId total=0 duplicate_values=0
textId total=0 duplicate_values=0
```

So the remaining Word warning is not caused by duplicate `paraId/textId` in `document.xml`.

## Tables

The table structure and text content are preserved.

Counts are the same:

```text
Table 0 rows: 6
Table 1 rows: 9
Table 2 rows: 2
Table 3 rows: 3
Table 4 rows: 14
Table 5 rows: 2
```

No bad `gridSpan` / `vMerge` pattern was found.

No `altChunk` found.

No drawing/blip inside `document.xml`.

## Main Structural Difference In Tables

Original `document.xml` contains 13 empty row-property blocks:

```text
<w:trPr/>
```

All 13 are in table 4, the employment table.

Recovered file contains:

```text
empty w:trPr = 0
```

Word removed those empty `w:trPr` containers during recovery.

This matches the generator behavior: `clear_row_height(row)` removes `w:trHeight`, but leaves an empty `w:trPr` in dynamic employment rows.

## Header / Footnotes / Endnotes

Original still has `w14:paraId` and `w14:textId` outside `document.xml`:

```text
word/header1.xml: paraId=2 textId=2
word/header2.xml: paraId=17 textId=17
word/footnotes.xml: paraId=2 textId=2
word/endnotes.xml: paraId=2 textId=2
```

Recovered Word file removes them all:

```text
word/header1.xml: paraId=0 textId=0
word/header2.xml: paraId=0 textId=0
word/footnotes.xml: paraId=0 textId=0
word/endnotes.xml: paraId=0 textId=0
```

These IDs were not duplicated, but Word still cleaned them.

## settings.xml

Word changed normal document metadata:

```text
zoom 150 -> 204
added several rsid values
removed w14:docId
```

This looks like normal Word save/recovery metadata, not the core cause.

## Most Likely Cause Of Word Warning

The strongest practical candidate is:

```text
empty <w:trPr/> blocks left in dynamic employment rows after removing w:trHeight
```

Secondary cleanup observed:

```text
remaining w14:paraId / w14:textId in header/footer-related XML parts
unused jpeg content type
media image rename image2.png -> image1.png
relationship ID renumbering
```

No evidence of broken ZIP, invalid XML, missing media, broken relationships, bad rId, bad gridSpan/vMerge, broken header/footer, or bad Content_Types.

## Minimal Next Fix Candidate

Do not rewrite the DOCX generator.

Minimal next code change should be:

1. After removing `w:trHeight`, delete empty `w:trPr` if it has no children.
2. Extend service-ID cleanup from only `word/document.xml` to all Word XML parts that may contain `w14:paraId` / `w14:textId`:
   - `word/header*.xml`
   - `word/footer*.xml` if present
   - `word/footnotes.xml`
   - `word/endnotes.xml`
3. Optionally remove unused image content types only if no matching media exists.

## Conclusion

The recovered file proves Word is not fixing business content. It is normalizing DOCX internals.

The next safest repair is to remove empty `w:trPr` blocks and clean `w14` IDs in all Word XML parts before packaging the DOCX.
