import json
import os
import re
import shutil
import subprocess
import tempfile
import uuid
import zipfile
from copy import deepcopy
from pathlib import Path
from xml.etree import ElementTree as ET

from flask import Flask, jsonify, render_template, request, send_file


BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_DOCX = BASE_DIR / "CV_эталон.docx"
START_DIR = BASE_DIR / "Start"
READY_DIR = BASE_DIR / "готовые резюме"
UPLOAD_DIR = BASE_DIR / "uploads"

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_NS}
ET.register_namespace("w", W_NS)

app = Flask(__name__)
SESSIONS = {}


FIELDS = [
    {"key": "role", "label": "Должность / желаемая роль"},
    {"key": "salary", "label": "Ожидаемый размер оплаты"},
    {"key": "fio", "label": "ФИО"},
    {"key": "phone", "label": "Телефон"},
    {"key": "email", "label": "Электронная почта"},
    {"key": "citizenship", "label": "Гражданство"},
    {"key": "family", "label": "Семейное положение / дети"},
    {"key": "birth_place_date", "label": "Место и дата рождения"},
    {"key": "registration", "label": "Место регистрации"},
    {"key": "location", "label": "Фактическое местонахождение"},
    {"key": "metro", "label": "Метро / станция электрички"},
    {"key": "driving", "label": "Водительские права, стаж, собственный автомобиль"},
    {"key": "about", "label": "Кандидат о себе"},
    {"key": "agency_comment", "label": "Комментарий Агентства"},
    {"key": "education_level", "label": "Образование"},
    {"key": "education", "label": "Учебное заведение, год окончания"},
    {"key": "courses", "label": "Повышение квалификации, курсы"},
    {"key": "recommendations", "label": "Наличие рекомендаций"},
]


def job_fields(job_count):
    fields = []
    for index in range(1, max(job_count, 2) + 1):
        fields.extend([
            {"key": f"job{index}_period", "label": f"Работа {index}: период"},
            {"key": f"job{index}_city", "label": f"Работа {index}: компания / город"},
            {"key": f"job{index}_site", "label": f"Работа {index}: сайт / информация"},
            {"key": f"job{index}_description", "label": f"Работа {index}: должность и обязанности"},
        ])
    return fields


def fields_for_job_count(job_count):
    return FIELDS[:-1] + job_fields(job_count) + FIELDS[-1:]


def ensure_dirs():
    START_DIR.mkdir(exist_ok=True)
    READY_DIR.mkdir(exist_ok=True)
    UPLOAD_DIR.mkdir(exist_ok=True)


def normalize_to_text(source_path):
    suffix = source_path.suffix.lower()
    if suffix == ".txt":
        return source_path.read_text(encoding="utf-8", errors="ignore")
    with tempfile.TemporaryDirectory() as temp_dir:
        out_dir = Path(temp_dir)
        result = subprocess.run(
            ["textutil", "-convert", "txt", "-output", str(out_dir / "out.txt"), str(source_path)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "Не удалось прочитать файл")
        return (out_dir / "out.txt").read_text(encoding="utf-8", errors="ignore")


def compact_lines(text):
    prepared = text.replace("\u2028", "\n").replace("\u00a0", " ")
    return [line.strip() for line in prepared.splitlines() if line.strip()]


def value_after_label(lines, labels):
    lowered = [line.lower().strip(": ") for line in lines]
    for label in labels:
        target = label.lower().strip(": ")
        for index, line in enumerate(lowered):
            if line == target or line.startswith(target + ":"):
                original = lines[index]
                if ":" in original:
                    after = original.split(":", 1)[1].strip()
                    if after:
                        return after
                for next_line in lines[index + 1 :]:
                    if next_line and not re.fullmatch(r"\d+\.?", next_line):
                        return next_line
    return ""


def block_between(lines, start_labels, stop_labels):
    start = None
    for index, line in enumerate(lines):
        clean = line.lower().strip(": ")
        if any(clean.startswith(label.lower().strip(": ")) for label in start_labels):
            start = index + 1
            break
    if start is None:
        return ""
    end = len(lines)
    for index in range(start, len(lines)):
        clean = lines[index].lower().strip(": ")
        if any(clean.startswith(label.lower().strip(": ")) for label in stop_labels):
            end = index
            break
    return "\n".join(lines[start:end]).strip()


def collect_numbered_answer(lines, question_fragment, stop_at_next_number=True):
    start = None
    for index, line in enumerate(lines):
        if question_fragment.lower() in line.lower():
            start = index + 1
            break
    if start is None:
        return ""
    values = []
    for line in lines[start:]:
        if stop_at_next_number and re.fullmatch(r"\d+\.?", line):
            break
        values.append(line)
    return "\n".join(values).strip()


def first_match(pattern, text):
    match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
    return match.group(1).strip() if match else ""


def parse_resume(text):
    lines = compact_lines(text)
    data = {field["key"]: "" for field in fields_for_job_count(2)}

    data["email"] = first_match(r"([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})", text)
    data["phone"] = (
        value_after_label(lines, ["Контактный телефон", "Телефон"])
        or first_match(r"((?:\+7|8|\(?\d{3}\)?)[\d \u00a0()\-]{7,}(?:\s*\([^)]*\))?)", text)
    )

    data["fio"] = (
        value_after_label(lines, ["Ф.И.О.", "ФИО"])
        or first_match(r"^([А-ЯЁ][а-яё]+ [А-ЯЁ][а-яё]+ [А-ЯЁ][а-яё]+)$", "\n".join(lines[:8]))
    )
    role_from_form = first_match(r"Анкета на вакансию\s+[«\"]([^»\"]+)[»\"]", text)
    data["role"] = value_after_label(lines, ["Желаемая должность"]) or role_from_form
    if not data["role"] and "Желаемая должность и зарплата" in text:
        data["role"] = value_after_label(lines, ["Желаемая должность и зарплата"])

    data["salary"] = collect_numbered_answer(lines, "Желаемый уровень заработной платы") or value_after_label(lines, ["Зарплата"])
    data["citizenship"] = value_after_label(lines, ["Гражданство", "Гражданство сейчас"]) or first_match(r"Гражданство:\s*(.+)", text)
    if data["citizenship"].lower().startswith("гражданство ранее"):
        for index, line in enumerate(lines):
            if line.lower().startswith("гражданство ранее"):
                data["citizenship"] = lines[index + 1] if index + 1 < len(lines) else ""
                break
    data["family"] = (
        value_after_label(lines, ["Семейное положение", "Состав семьи"])
        or first_match(r"Семейное положение:\s*(.+)", text)
    )
    if data["family"].lower() in {"вдова", "замужем. разведена", "дети: сын. дочь. возраст"}:
        for index, line in enumerate(lines):
            if line.lower().startswith("дети:"):
                data["family"] = lines[index + 1] if index + 1 < len(lines) else ""
                break
    data["birth_place_date"] = (
        value_after_label(lines, ["Дата рождения", "Дата рождения. Возраст"])
        or first_match(r"(?:родился|родилась)\s+(.+)", text)
    )
    data["registration"] = value_after_label(lines, ["Прописка по паспорту", "Место регистрации"])
    data["location"] = (
        value_after_label(lines, ["Адрес фактического проживания", "Город проживания"])
        or first_match(r"Проживает:\s*(.+)", text)
    )
    district = value_after_label(lines, ["Район проживания"])
    if district and data["location"]:
        data["location"] = f"{data['location']}; {district}"
    data["metro"] = value_after_label(lines, ["Ближайшее метро", "Ближайшая станция метро", "Метро / станция электрички"])
    data["driving"] = (
        value_after_label(lines, ["Наличие водительских прав", "Опыт вождения", "Наличие водительских прав. Фактический опыт вождения автомобиля."])
        or block_between(lines, ["Опыт вождения"], ["Дополнительная информация", "Обо мне"])
    )
    data["education_level"] = value_after_label(lines, ["Образование"])
    if data["education_level"].endswith(",") or "среднее" in data["education_level"].lower():
        for index, line in enumerate(lines):
            if line.lower().startswith("неоконченное высшее") and index + 1 < len(lines):
                data["education_level"] = lines[index + 1]
                break
    data["education"] = (
        collect_numbered_answer(lines, "Наименование учебного заведения")
        or block_between(lines, ["Образование"], ["Повышение квалификации", "Курсы и тренинги", "Дополнительное образование", "Иностранные языки", "Навыки", "Дополнительная информация"])
    )
    data["courses"] = (
        block_between(lines, ["Повышение квалификации", "Курсы и тренинги"], ["Тесты", "Навыки", "Иностранные языки", "Дополнительная информация", "Опыт работы"])
        or collect_numbered_answer(lines, "Дополнительное образование")
    )
    data["about"] = (
        block_between(lines, ["Обо мне", "Дополнительные сведения"], ["Комментарии к резюме", "История общения", "Занятия в свободное время"])
        or collect_numbered_answer(lines, "Ваша Презентация")
        or value_after_label(lines, ["Дополнительные сведения"])
    )
    data["agency_comment"] = ""
    recommendations = value_after_label(lines, ["Рекомендации и ссылки", "Рекомендации прежних работодателей"])
    data["recommendations"] = recommendations

    jobs = extract_jobs(lines, text)
    for index, job in enumerate(jobs, 1):
        data[f"job{index}_period"] = job.get("period", "")
        data[f"job{index}_city"] = job.get("city", "")
        data[f"job{index}_site"] = job.get("site", "")
        data[f"job{index}_description"] = job.get("description", "")
    data["_job_count"] = len(jobs)

    return data


def extract_jobs(lines, text):
    if "Опыт работы в СЕМЬЕ" in text:
        block = block_between(lines, ["Опыт работы в СЕМЬЕ"], ["Ваша Презентация", "Есть ли у Вас"])
        return split_questionnaire_jobs(block.splitlines())

    block = block_between(lines, ["Опыт работы"], ["Образование", "Курсы", "Иностранные языки", "Навыки", "Дополнительная информация"])
    if block:
        return split_standard_jobs(block.splitlines())

    work = collect_numbered_answer(lines, "Трудовой стаж", False)
    return split_questionnaire_jobs(work.splitlines())


def split_standard_jobs(lines):
    month_names = "январ|феврал|март|апрел|ма[йя]|июн|июл|август|сентябр|октябр|ноябр|декабр"
    starts = []
    for index, line in enumerate(lines):
        if re.search(rf"({month_names}).+(настоящее время|\d{{4}})", line.lower()):
            starts.append(index)
    jobs = []
    for pos, start in enumerate(starts):
        end = starts[pos + 1] if pos + 1 < len(starts) else len(lines)
        chunk = [line for line in lines[start:end] if line.strip()]
        if not chunk:
            continue
        period = chunk[0]
        if any(line.rstrip(":").lower() in {"должность", "в организации", "описание деятельности организации", "должностные обязанности"} for line in chunk):
            jobs.append(split_labeled_job(chunk, period))
            continue
        cursor = 1
        if cursor < len(chunk) and re.search(r"(месяц|год|лет)", chunk[cursor].lower()):
            period = period + "\n" + chunk[cursor]
            cursor += 1
        company = chunk[cursor] if cursor < len(chunk) else ""
        if cursor + 1 < len(chunk) and not re.search(r"(директор|нян|воспит|домработ|представитель|начальник|руковод)", chunk[cursor + 1].lower()):
            city = chunk[cursor + 1]
            place = "\n".join(line for line in [company, city] if line)
            cursor += 2
        else:
            place = company
            cursor += 1
        site = ""
        jobs.append({"period": period, "city": place, "site": site, "description": "\n".join(chunk[cursor:]).strip()})
    return jobs


def value_from_labeled_chunk(chunk, label):
    target = label.lower().strip(": ")
    for index, line in enumerate(chunk):
        clean = line.lower().strip(": ")
        if clean == target:
            return chunk[index + 1] if index + 1 < len(chunk) else ""
    return ""


def block_from_labeled_chunk(chunk, labels):
    indexes = []
    label_set = {label.lower().strip(": ") for label in labels}
    for index, line in enumerate(chunk):
        if line.lower().strip(": ") in label_set:
            indexes.append(index)
    values = []
    for pos, index in enumerate(indexes):
        end = indexes[pos + 1] if pos + 1 < len(indexes) else len(chunk)
        values.extend(chunk[index + 1:end])
    return "\n".join(values).strip()


def split_labeled_job(chunk, period):
    company = value_from_labeled_chunk(chunk, "В организации")
    role = value_from_labeled_chunk(chunk, "Должность")
    description = block_from_labeled_chunk(chunk, ["Описание деятельности организации", "Должностные обязанности"])
    combined_description = "\n".join(line for line in [role, description] if line).strip()
    return {"period": period, "city": company, "site": "", "description": combined_description}


def split_questionnaire_jobs(lines):
    starts = []
    for index, line in enumerate(lines):
        if re.search(r"(\d{4}|январ|феврал|март|апрел|ма[йя]|июн|июл|август|сентябр|октябр|ноябр|декабр)", line.lower()):
            if "причина" not in line.lower():
                starts.append(index)
    jobs = []
    for pos, start in enumerate(starts):
        end = starts[pos + 1] if pos + 1 < len(starts) else min(len(lines), start + 8)
        chunk = [line for line in lines[start:end] if line.strip()]
        jobs.append({
            "period": chunk[0] if chunk else "",
            "city": chunk[1] if len(chunk) > 1 else "",
            "site": "",
            "description": "\n".join(chunk[2:]).strip(),
        })
    return jobs


def cell_text(cell):
    return "".join(node.text or "" for node in cell.findall(".//w:t", NS)).strip()


def set_run_bold(run, enabled):
    rpr = run.find("./w:rPr", NS)
    if rpr is None:
        rpr = ET.Element(f"{{{W_NS}}}rPr")
        run.insert(0, rpr)
    bold = rpr.find("./w:b", NS)
    if enabled and bold is None:
        ET.SubElement(rpr, f"{{{W_NS}}}b")
    if not enabled and bold is not None:
        rpr.remove(bold)


def set_cell_text(cell, value, bold_first_line=False):
    paragraphs = cell.findall("./w:p", NS)
    template_paragraph = deepcopy(paragraphs[0]) if paragraphs else ET.Element(f"{{{W_NS}}}p")
    for child in list(cell):
        if child.tag == f"{{{W_NS}}}p":
            cell.remove(child)
    lines = str(value or "").splitlines() or [""]
    for index, line in enumerate(lines):
        paragraph = deepcopy(template_paragraph)
        runs = paragraph.findall(".//w:r", NS)
        if runs:
            first_run = runs[0]
            for run in runs[1:]:
                parent = paragraph
                parent.remove(run)
        else:
            first_run = ET.SubElement(paragraph, f"{{{W_NS}}}r")
        for node in list(first_run):
            if node.tag != f"{{{W_NS}}}rPr":
                first_run.remove(node)
        set_run_bold(first_run, bold_first_line and index == 0 and bool(line.strip()))
        text_node = ET.SubElement(first_run, f"{{{W_NS}}}t")
        text_node.text = line
        if line.startswith(" ") or line.endswith(" "):
            text_node.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        cell.append(paragraph)


def count_jobs(data):
    indexes = []
    for key, value in data.items():
        match = re.fullmatch(r"job(\d+)_(period|city|site|description)", key)
        if match and str(value or "").strip():
            indexes.append(int(match.group(1)))
    return max(indexes) if indexes else 0


def expand_employment_table(table, job_count):
    rows = table.findall("./w:tr", NS)
    if len(rows) < 7:
        return
    for row in rows[7:]:
        table.remove(row)
    needed = max(job_count, 2)
    template_block = [deepcopy(row) for row in rows[4:7]]
    for _ in range(3, needed + 1):
        for row in template_block:
            table.append(deepcopy(row))


def fill_template(data, output_path):
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_docx = Path(temp_dir) / "work.docx"
        shutil.copy2(TEMPLATE_DOCX, temp_docx)
        with zipfile.ZipFile(temp_docx, "r") as zin:
            files = {name: zin.read(name) for name in zin.namelist()}
        root = ET.fromstring(files["word/document.xml"])
        tables = root.findall(".//w:tbl", NS)

        def set_by_pos(table_index, row_index, cell_index, key, bold_first_line=False):
            try:
                row = tables[table_index].findall("./w:tr", NS)[row_index]
                cell = row.findall("./w:tc", NS)[cell_index]
            except IndexError:
                return
            set_cell_text(cell, data.get(key, ""), bold_first_line=bold_first_line)

        set_by_pos(0, 0, 0, "role")
        set_by_pos(0, 1, 1, "salary")
        set_by_pos(0, 3, 1, "fio")
        set_by_pos(0, 4, 1, "citizenship")
        set_by_pos(0, 5, 1, "family")
        set_by_pos(1, 1, 1, "birth_place_date")
        set_by_pos(1, 2, 1, "registration")
        set_by_pos(1, 3, 1, "location")
        set_by_pos(1, 4, 1, "metro")
        set_by_pos(1, 5, 1, "driving")
        set_by_pos(2, 1, 0, "about")
        set_by_pos(2, 3, 0, "agency_comment")
        set_by_pos(3, 1, 0, "education_level")
        set_by_pos(3, 1, 1, "education")
        set_by_pos(3, 2, 1, "courses")
        job_count = count_jobs(data)
        expand_employment_table(tables[4], job_count)
        for index in range(1, max(job_count, 2) + 1):
            row_base = 1 + (index - 1) * 3
            set_by_pos(4, row_base, 0, f"job{index}_period")
            set_by_pos(4, row_base, 1, f"job{index}_city", bold_first_line=True)
            set_by_pos(4, row_base + 1, 1, f"job{index}_site")
            set_by_pos(4, row_base + 2, 1, f"job{index}_description")
        set_by_pos(5, 1, 1, "recommendations")

        files["word/document.xml"] = ET.tostring(root, encoding="utf-8", xml_declaration=True)
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zout:
            for name, content in files.items():
                zout.writestr(name, content)


def safe_filename(name):
    cleaned = re.sub(r"[^\wа-яА-ЯёЁ ._-]+", "_", name, flags=re.UNICODE).strip()
    return cleaned or "resume"


@app.route("/")
def index():
    return render_template("index.html", fields=fields_for_job_count(2))


@app.post("/upload")
def upload():
    ensure_dirs()
    uploaded = request.files.get("file")
    if not uploaded:
        return jsonify({"error": "Файл не выбран"}), 400
    original_name = safe_filename(uploaded.filename)
    session_id = uuid.uuid4().hex
    saved_path = UPLOAD_DIR / f"{session_id}_{original_name}"
    uploaded.save(saved_path)
    shutil.copy2(saved_path, START_DIR / original_name)
    text = normalize_to_text(saved_path)
    data = parse_resume(text)
    SESSIONS[session_id] = {"source": str(saved_path), "filename": original_name, "text": text, "data": data}
    return jsonify({
        "session_id": session_id,
        "filename": original_name,
        "text": text,
        "data": data,
        "fields": fields_for_job_count(data.get("_job_count", 0)),
    })


@app.post("/save")
def save():
    ensure_dirs()
    payload = request.get_json(force=True)
    session_id = payload.get("session_id")
    data = payload.get("data") or {}
    if session_id not in SESSIONS:
        return jsonify({"error": "Сначала загрузите файл"}), 400
    fio = data.get("fio") or Path(SESSIONS[session_id]["filename"]).stem
    output_name = "CV_" + safe_filename(fio).replace(" ", "_") + ".docx"
    output_path = READY_DIR / output_name
    fill_template(data, output_path)
    SESSIONS[session_id]["data"] = data
    SESSIONS[session_id]["output"] = str(output_path)
    return jsonify({"filename": output_name, "path": str(output_path)})


@app.get("/download/<session_id>")
def download(session_id):
    session = SESSIONS.get(session_id)
    if not session or not session.get("output"):
        return jsonify({"error": "Файл еще не сохранен"}), 404
    return send_file(session["output"], as_attachment=True)


@app.get("/health")
def health():
    return jsonify({"ok": True})


if __name__ == "__main__":
    ensure_dirs()
    app.run(host="127.0.0.1", port=5000, debug=False)
