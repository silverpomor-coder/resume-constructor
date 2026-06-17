# Stage 2.1 DOCX fix diagnostic report

## unzip -t
    testing: word/fontTable.xml       OK
    testing: docProps/core.xml        OK
    testing: docProps/app.xml         OK
    testing: customXml/_rels/item1.xml.rels   OK
No errors detected in compressed data of tests/reports/stage2_1/CV_stage2_1_generated.docx.

## XML validation
OK

## broken_old
paraId: total=143; unique=80; duplicate_values=12; sample=[('4675F987', 2), ('275BE565', 2), ('65B5BF3A', 2), ('29342157', 2), ('77477223', 2), ('43F51A46', 4), ('4CBA0324', 9), ('1C61DC06', 2), ('3908E1B3', 5), ('5A0ACDAA', 5)]
textId: total=143; unique=44; duplicate_values=9; sample=[('77777777', 44), ('333A9FB0', 2), ('4DF5A21D', 2), ('597C3C83', 4), ('3728A9CE', 9), ('7D257089', 2), ('463861D9', 5), ('205B44A3', 10), ('67A03391', 30)]
missing_relationship_targets: none
duplicate_relationship_ids: none
unresolved_xml_relationship_refs: none
media: ['word/media/image2.png']
contains 'Муравьев Роман': True
contains 'Персональный водитель': True
contains 'Среднее специальное': True
contains 'Summa Group': True

## generated_new
paraId: total=0; unique=0; duplicate_values=0; sample=[]
textId: total=0; unique=0; duplicate_values=0; sample=[]
missing_relationship_targets: none
duplicate_relationship_ids: none
unresolved_xml_relationship_refs: none
media: ['word/media/image2.png']
contains 'Муравьев Роман': True
contains 'Персональный водитель': True
contains 'Среднее специальное': True
contains 'Summa Group': True


## Cloud /save contract check
status: 200
content_type: application/vnd.openxmlformats-officedocument.wordprocessingml.document
body_prefix: PK\x03\x04
result: DOCX blob contract unchanged

## LibreOffice check
LibreOffice/soffice is not available in this environment.
