import re
import json
import hmac
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
import zipfile
from io import BytesIO
from copy import deepcopy
from datetime import date
from pathlib import Path
from xml.etree import ElementTree as ET

from flask import Flask, jsonify, redirect, render_template, request, send_file, session, url_for
from werkzeug.exceptions import RequestEntityTooLarge


BASE_DIR = Path(__file__).resolve().parent
RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", BASE_DIR))
RUNTIME_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else BASE_DIR
APP_MODE = os.environ.get("APP_MODE", "local").lower()
IS_CLOUD = APP_MODE == "cloud"
START_DIR = RUNTIME_DIR / "Start"
READY_DIR = Path(tempfile.gettempdir()) / "constructor_resume_ready" if IS_CLOUD else RUNTIME_DIR / "готовые резюме"
UPLOAD_DIR = Path(tempfile.gettempdir()) / "constructor_resume_uploads" if IS_CLOUD else RUNTIME_DIR / "uploads"
SETTINGS_PATH = RUNTIME_DIR / "app_settings.json"
APP_PASSWORD = os.environ.get("APP_PASSWORD")
MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "16"))
CLEANUP_MAX_AGE_SECONDS = int(os.environ.get("CLEANUP_MAX_AGE_SECONDS", str(3 * 60 * 60)))
CLEANUP_INTERVAL_SECONDS = 15 * 60
TEMPLATE_DOCX_NAME = "CV_sample_v2.docx"
TEMPLATE_DOCX = RESOURCE_DIR / TEMPLATE_DOCX_NAME
if not TEMPLATE_DOCX.exists():
    TEMPLATE_DOCX = START_DIR / TEMPLATE_DOCX_NAME

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_NS}
ET.register_namespace("w", W_NS)
MONTHS = {
    "январь": 1,
    "января": 1,
    "февраль": 2,
    "февраля": 2,
    "март": 3,
    "марта": 3,
    "апрель": 4,
    "апреля": 4,
    "май": 5,
    "мая": 5,
    "июнь": 6,
    "июня": 6,
    "июль": 7,
    "июля": 7,
    "август": 8,
    "августа": 8,
    "сентябрь": 9,
    "сентября": 9,
    "октябрь": 10,
    "октября": 10,
    "ноябрь": 11,
    "ноября": 11,
    "декабрь": 12,
    "декабря": 12,
}

app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET_KEY", uuid.uuid4().hex)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024
SESSIONS = {}
LAST_CLEANUP_AT = 0
if IS_CLOUD and not APP_PASSWORD:
    app.logger.warning("APP_MODE=cloud запущен без APP_PASSWORD. Доступ не защищен паролем.")


FIELDS = [
    {"key": "role", "label": "Должность / желаемая роль"},
    {"key": "salary", "label": "Ожидаемый размер оплаты"},
    {"key": "fio", "label": "ФИО"},
    {"key": "phone", "label": "Телефон"},
    {"key": "email", "label": "Электронная почта"},
    {"key": "citizenship", "label": "Гражданство"},
    {"key": "birth_place_date", "label": "Место и дата рождения"},
    {"key": "family", "label": "Семейное положение / дети"},
    {"key": "registration", "label": "Место регистрации"},
    {"key": "location", "label": "Фактическое местонахождение"},
    {"key": "metro", "label": "Метро / станция электрички"},
    {"key": "criminal_record", "label": "Наличие судимости"},
    {"key": "languages", "label": "Знание иностранных языков"},
    {"key": "medical_book", "label": "Наличие медицинской книжки"},
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
    if not IS_CLOUD:
        START_DIR.mkdir(exist_ok=True)
    READY_DIR.mkdir(exist_ok=True)
    UPLOAD_DIR.mkdir(exist_ok=True)


def cleanup_old_files(force=False):
    global LAST_CLEANUP_AT
    if not IS_CLOUD:
        return
    now = time.time()
    if not force and now - LAST_CLEANUP_AT < CLEANUP_INTERVAL_SECONDS:
        return
    LAST_CLEANUP_AT = now
    cutoff = now - CLEANUP_MAX_AGE_SECONDS
    for directory in (UPLOAD_DIR, READY_DIR):
        if not directory.exists():
            continue
        for path in directory.iterdir():
            if path.is_file() and path.stat().st_mtime < cutoff:
                path.unlink(missing_ok=True)
    for session_id, data in list(SESSIONS.items()):
        output = data.get("output")
        source = data.get("source")
        if (output and not Path(output).exists()) or (source and not Path(source).exists()):
            SESSIONS.pop(session_id, None)


@app.before_request
def before_request():
    cleanup_old_files()
    if not IS_CLOUD or not APP_PASSWORD:
        return None
    allowed = {"login", "health", "static"}
    if request.endpoint in allowed:
        return None
    if session.get("authenticated"):
        return None
    if request.path.startswith("/static/"):
        return None
    if request.accept_mimetypes.accept_html and request.method == "GET":
        return redirect(url_for("login"))
    return jsonify({"error": "Требуется пароль"}), 401


@app.errorhandler(RequestEntityTooLarge)
def upload_too_large(error):
    return jsonify({"error": f"Файл слишком большой. Максимум: {MAX_UPLOAD_MB} МБ"}), 413


def normalize_to_text(source_path):
    suffix = source_path.suffix.lower()
    if suffix == ".txt":
        return read_text_file(source_path)
    if shutil.which("textutil"):
        return normalize_with_textutil(source_path)
    if suffix == ".docx":
        return docx_to_text(source_path)
    if suffix == ".odt":
        return odt_to_text(source_path)
    if suffix == ".rtf":
        return rtf_to_text(source_path)
    if suffix == ".doc":
        return binary_doc_to_text(source_path)
    raise RuntimeError("Формат файла не поддерживается")


def read_text_file(source_path):
    for encoding in ("utf-8", "cp1251", "utf-16"):
        try:
            return source_path.read_text(encoding=encoding)
        except UnicodeError:
            continue
    return source_path.read_text(encoding="utf-8", errors="ignore")


def normalize_with_textutil(source_path):
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


def xml_text_from_zip(source_path, xml_name):
    with zipfile.ZipFile(source_path, "r") as archive:
        root = ET.fromstring(archive.read(xml_name))
    parts = []
    for node in root.iter():
        if node.tag.endswith("}t") or node.tag.endswith("}tab"):
            parts.append(node.text or "\t")
        elif node.tag.endswith("}br") or node.tag.endswith("}p"):
            parts.append("\n")
    return "\n".join(line.strip() for line in "".join(parts).splitlines() if line.strip())


def docx_to_text(source_path):
    return xml_text_from_zip(source_path, "word/document.xml")


def odt_to_text(source_path):
    return xml_text_from_zip(source_path, "content.xml")


def rtf_to_text(source_path):
    text = read_text_file(source_path)
    text = re.sub(r"\\'[0-9a-fA-F]{2}", " ", text)
    text = re.sub(r"\\[a-zA-Z]+-?\d* ?", " ", text)
    text = text.replace("{", " ").replace("}", " ").replace("\\", " ")
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


def binary_doc_to_text(source_path):
    data = source_path.read_bytes()
    variants = []
    for encoding in ("utf-16le", "cp1251", "utf-8"):
        text = data.decode(encoding, errors="ignore")
        text = re.sub(r"[^\w\s@.,:;()+\-/«»\"№А-Яа-яЁё]", "\n", text)
        lines = [line.strip() for line in text.splitlines() if len(line.strip()) > 1]
        variants.append("\n".join(lines))
    text = max(variants, key=len)
    if not re.search(r"[А-Яа-яЁё]{3,}", text):
        raise RuntimeError("Не удалось прочитать старый DOC-файл")
    return text


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


def block_after_label(lines, labels, stop_labels):
    start = None
    for index, line in enumerate(lines):
        clean = line.lower().strip(": ")
        if any(clean == label.lower().strip(": ") for label in labels):
            start = index + 1
            break
    if start is None:
        return ""
    end = len(lines)
    stop_set = {label.lower().strip(": ") for label in stop_labels}
    for index in range(start, len(lines)):
        clean = lines[index].lower().strip(": ")
        if clean in stop_set:
            end = index
            break
    return "\n".join(lines[start:end]).strip()


def block_after_section(lines, labels, stop_labels):
    start = None
    for index, line in enumerate(lines):
        clean = line.lower().strip(": ")
        if any(clean == label.lower().strip(": ") for label in labels):
            start = index + 1
            break
    if start is None:
        return ""
    end = len(lines)
    stop_set = {label.lower().strip(": ") for label in stop_labels}
    for index in range(start, len(lines)):
        clean = lines[index].lower().strip(": ")
        if clean in stop_set:
            end = index
            break
    return "\n".join(lines[start:end]).strip()


def education_details(lines, education_level):
    details = (
        collect_numbered_answer(lines, "Наименование учебного заведения")
        or block_after_label(
            lines,
            ["Учебное заведение"],
            ["Курсы и тренинги", "Повышение квалификации", "Повышение квалификации, курсы", "Дополнительное образование", "Иностранные языки и компьютерные навыки", "Иностранные языки", "Навыки", "Дополнительная информация"],
        )
        or block_after_section(
            lines,
            ["Образование"],
            ["Курсы и тренинги", "Повышение квалификации", "Повышение квалификации, курсы", "Дополнительное образование", "Иностранные языки и компьютерные навыки", "Иностранные языки", "Навыки", "Дополнительная информация"],
        )
    )
    detail_lines = details.splitlines()
    if detail_lines and detail_lines[0].strip().lower() == str(education_level or "").strip().lower():
        detail_lines = detail_lines[1:]
    return "\n".join(detail_lines).strip()


def first_match(pattern, text):
    match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
    return match.group(1).strip() if match else ""


def line_after_exact(lines, label):
    target = label.lower().strip(": ")
    for index, line in enumerate(lines):
        if line.lower().strip(": ") == target:
            return lines[index + 1] if index + 1 < len(lines) else ""
    return ""


def block_after_exact(lines, start_label, stop_labels):
    target = start_label.lower().strip(": ")
    start = None
    for index, line in enumerate(lines):
        if line.lower().strip(": ") == target:
            start = index + 1
            break
    if start is None:
        return ""
    stop_set = {label.lower().strip(": ") for label in stop_labels}
    end = len(lines)
    for index in range(start, len(lines)):
        if lines[index].lower().strip(": ") in stop_set:
            end = index
            break
    return "\n".join(lines[start:end]).strip()


def hh_experience_block(lines):
    start = None
    for index, line in enumerate(lines):
        if line.lower().startswith("опыт работы"):
            start = index + 1
            break
    if start is None:
        return ""
    end = len(lines)
    for index in range(start, len(lines)):
        if lines[index].lower().strip(": ") == "образование":
            end = index
            break
    return "\n".join(lines[start:end]).strip()


def hh_salary(lines):
    start = None
    for index, line in enumerate(lines):
        if line.lower().strip(": ") == "желаемая должность и зарплата":
            start = index + 1
            break
    if start is None:
        return ""
    for line in lines[start:]:
        lowered = line.lower()
        if lowered.startswith("опыт работы"):
            break
        if "₽" in line or "руб" in lowered or "на руки" in lowered:
            return line
    return ""


def hh_location(lines):
    value = first_match(r"^Проживает:\s*(.+)$", "\n".join(lines))
    if not value:
        return "", ""
    parts = re.split(r",\s*м\.\s*", value, maxsplit=1, flags=re.IGNORECASE)
    location = parts[0].strip()
    metro = parts[1].strip() if len(parts) > 1 else ""
    return location, metro


def hh_fio(lines):
    for index, line in enumerate(lines):
        if re.match(r"^(женщина|мужчина),", line.lower()):
            for previous in reversed(lines[:index]):
                if previous.strip():
                    return previous.strip()
    return ""


def is_hh_period(line):
    month_names = "январь|февраль|март|апрель|май|июнь|июль|август|сентябрь|октябрь|ноябрь|декабрь"
    return bool(re.fullmatch(rf"({month_names})\s+\d{{4}}\s+—\s+(настоящее время|({month_names})\s+\d{{4}})", line.lower()))


def is_hh_duration(line):
    return bool(re.search(r"\d+\s+(?:год|года|лет|месяц|месяца|месяцев)", line.lower()))


def split_hh_jobs(lines):
    starts = [index for index, line in enumerate(lines) if is_hh_period(line)]
    jobs = []
    role_words = r"(директор|гуверн|нян|воспит|репетитор|учитель|педагог|домработ|помощ)"
    for pos, start in enumerate(starts):
        end = starts[pos + 1] if pos + 1 < len(starts) else len(lines)
        chunk = [line for line in lines[start:end] if line.strip()]
        if not chunk:
            continue
        period = chunk[0]
        cursor = 1
        if cursor < len(chunk) and is_hh_duration(chunk[cursor]):
            period = f"{period}\n{chunk[cursor]}"
            cursor += 1
        company = chunk[cursor] if cursor < len(chunk) else ""
        cursor += 1
        city = ""
        if cursor < len(chunk) and not re.search(role_words, chunk[cursor].lower()) and len(chunk[cursor]) < 80:
            city = chunk[cursor]
            cursor += 1
        place = "\n".join(line for line in [company, city] if line)
        jobs.append({
            "period": period,
            "city": place,
            "site": "",
            "description": "\n".join(chunk[cursor:]).strip(),
        })
    return jobs


def parse_hh_resume(text):
    lines = compact_lines(text)
    data = {field["key"]: "" for field in fields_for_job_count(2)}

    data["fio"] = hh_fio(lines)
    data["email"] = first_match(r"([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})", text)
    data["phone"] = first_match(r"((?:\+7|8|\(?\d{3}\)?)[\d \u00a0()\-]{7,}(?:\s*\([^)]*\))?)", text)
    data["role"] = line_after_exact(lines, "Желаемая должность и зарплата")
    data["salary"] = hh_salary(lines)
    data["citizenship"] = value_after_label(lines, ["Гражданство"])
    data["birth_place_date"] = first_match(r"(?:родился|родилась)\s+(.+)", text)
    data["location"], data["metro"] = hh_location(lines)
    data["education_level"] = line_after_exact(lines, "Образование")

    education = block_after_exact(lines, "Образование", ["Навыки", "Повышение квалификации, курсы"])
    education_lines = education.splitlines()
    if education_lines and education_lines[0] == data["education_level"]:
        education_lines = education_lines[1:]
    data["education"] = "\n".join(education_lines).strip()
    data["courses"] = block_after_exact(lines, "Повышение квалификации, курсы", ["Навыки"])
    data["languages"] = block_after_exact(lines, "Знание языков", ["Навыки", "Опыт вождения"])
    data["driving"] = block_after_exact(lines, "Опыт вождения", ["Дополнительная информация"])
    data["about"] = block_after_exact(lines, "Обо мне", ["Комментарии к резюме", "История общения с кандидатом"])

    jobs = split_hh_jobs(hh_experience_block(lines).splitlines())
    for index, job in enumerate(jobs, 1):
        data[f"job{index}_period"] = job.get("period", "")
        data[f"job{index}_city"] = job.get("city", "")
        data[f"job{index}_site"] = job.get("site", "")
        data[f"job{index}_description"] = job.get("description", "")
    data["_job_count"] = len(jobs)

    return data


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
        or hh_fio(lines)
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
    data["education"] = education_details(lines, data["education_level"])
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


def register_document_namespaces(xml_content):
    for _, namespace in ET.iterparse(BytesIO(xml_content), events=("start-ns",)):
        prefix, uri = namespace
        try:
            ET.register_namespace(prefix, uri)
        except ValueError:
            continue


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


def parse_ru_date(value, default_day=1):
    value = str(value or "").lower()
    match = re.search(r"(\d{1,2})[./-](\d{1,2})[./-](\d{4})", value)
    if match:
        day, month, year = map(int, match.groups())
        try:
            return date(year, month, day)
        except ValueError:
            return None
    match = re.search(r"(?<!\d)(\d{1,2})[./-](\d{4})(?!\d)", value)
    if match:
        month, year = map(int, match.groups())
        try:
            return date(year, month, default_day)
        except ValueError:
            return None
    month_names = "|".join(MONTHS)
    match = re.search(rf"(\d{{1,2}})\s+({month_names})\s+(\d{{4}})", value)
    if match:
        day = int(match.group(1))
        month = MONTHS[match.group(2)]
        year = int(match.group(3))
        try:
            return date(year, month, day)
        except ValueError:
            return None
    match = re.search(rf"({month_names})\s+(\d{{4}})", value)
    if match:
        month = MONTHS[match.group(1)]
        year = int(match.group(2))
        try:
            return date(year, month, default_day)
        except ValueError:
            return None
    return None


def clean_birth_date_text(value):
    return re.sub(r"\s*\(\s*\d+\s*(?:год|года|лет)\s*\)\s*", "", str(value or ""), flags=re.IGNORECASE).strip()


def age_text(value, today=None):
    cleaned = clean_birth_date_text(value)
    birthday = parse_ru_date(cleaned)
    if not birthday:
        return cleaned
    today = today or date.today()
    years = today.year - birthday.year - ((today.month, today.day) < (birthday.month, birthday.day))
    return "\n".join(line for line in [cleaned, f"Полных лет: {years}"] if line)


def find_job_period_dates(period):
    date_pattern = r"\d{1,2}[./-]\d{1,2}[./-]\d{4}|\d{1,2}[./-]\d{4}|[А-Яа-яЁё]+\s+\d{4}"
    values = re.findall(date_pattern, period)
    if len(values) == 1 and re.search(r"настоящее время|по наст", period, re.IGNORECASE):
        return parse_ru_date(values[0]), date.today()
    if len(values) < 2:
        return None, None
    return parse_ru_date(values[0]), parse_ru_date(values[1])


def strip_job_duration(period):
    cleaned = re.sub(r"\s*\(\s*\d+\s*(?:г\.?|год(?:а|ов)?|лет)\s*(?:\d+\s*(?:мес\.?|месяц(?:а|ев)?))?\s*\)\s*$", "", period, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*\(\s*\d+\s*(?:мес\.?|месяц(?:а|ев)?)\s*\)\s*$", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+[1-9]\d?\s*(?:г\.?|год(?:а|ов)?|лет)\s+[1-9]\d?\s*(?:мес\.?|месяц(?:а|ев)?)\s*$", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+[1-9]\d?\s*(?:мес\.?|месяц(?:а|ев)?)\s*$", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def job_duration_text(period, today=None):
    start, end = find_job_period_dates(period)
    if start and not end and re.search(r"настоящее время|по наст", period, re.IGNORECASE):
        end = today or date.today()
    if not start or not end or end < start:
        return ""
    total_months = (end.year - start.year) * 12 + (end.month - start.month)
    years, months = divmod(total_months, 12)
    parts = []
    if years:
        parts.append(f"{years} г.")
    if months or not parts:
        parts.append(f"{months} мес.")
    return " ".join(parts)


def period_with_duration(period):
    base_period = strip_job_duration(str(period or ""))
    duration = job_duration_text(base_period)
    if not duration:
        return base_period
    return f"{base_period}\n({duration})"


def job_summary(data, index):
    city = str(data.get(f"job{index}_city", "") or "").strip()
    site = str(data.get(f"job{index}_site", "") or "").strip()
    description = str(data.get(f"job{index}_description", "") or "").strip()
    lines = []
    if city:
        lines.append(f"Место работы: {city}")
    if site:
        lines.append(f"Сайт / информация: {site}")
    if description:
        lines.append(f"Функционал:\n{description}")
    return "\n".join(lines)


def expand_employment_table(table, job_count):
    rows = table.findall("./w:tr", NS)
    if len(rows) < 2:
        return
    needed = max(job_count, 1)
    template_row = deepcopy(rows[-1])
    for row in rows[needed + 1 :]:
        table.remove(row)
    current_rows = table.findall("./w:tr", NS)
    for _ in range(len(current_rows) - 1, needed):
        table.append(deepcopy(template_row))


def fill_template(data, output_path):
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_docx = Path(temp_dir) / "work.docx"
        shutil.copy2(TEMPLATE_DOCX, temp_docx)
        with zipfile.ZipFile(temp_docx, "r") as zin:
            files = {name: zin.read(name) for name in zin.namelist()}
        register_document_namespaces(files["word/document.xml"])
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
        try:
            birth_cell = tables[0].findall("./w:tr", NS)[5].findall("./w:tc", NS)[1]
            set_cell_text(birth_cell, age_text(data.get("birth_place_date", "")))
        except IndexError:
            pass
        set_by_pos(1, 1, 1, "family")
        set_by_pos(1, 2, 1, "registration")
        set_by_pos(1, 3, 1, "location")
        set_by_pos(1, 4, 1, "metro")
        set_by_pos(1, 5, 1, "criminal_record")
        set_by_pos(1, 6, 1, "languages")
        set_by_pos(1, 7, 1, "medical_book")
        set_by_pos(1, 8, 1, "driving")
        set_by_pos(2, 1, 0, "about")
        set_by_pos(2, 3, 0, "agency_comment")
        set_by_pos(3, 1, 0, "education_level")
        set_by_pos(3, 1, 1, "education")
        set_by_pos(3, 2, 1, "courses")
        job_count = count_jobs(data)
        expand_employment_table(tables[4], job_count)
        for index in range(1, max(job_count, 1) + 1):
            try:
                row = tables[4].findall("./w:tr", NS)[index]
                cells = row.findall("./w:tc", NS)
            except IndexError:
                continue
            set_cell_text(cells[0], period_with_duration(data.get(f"job{index}_period", "")))
            set_cell_text(cells[1], job_summary(data, index), bold_first_line=True)
        set_by_pos(5, 1, 1, "recommendations")

        files["word/document.xml"] = ET.tostring(root, encoding="utf-8", xml_declaration=True)
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zout:
            for name, content in files.items():
                zout.writestr(name, content)


def load_settings():
    if not SETTINGS_PATH.exists():
        return {}
    try:
        return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_settings(settings):
    SETTINGS_PATH.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")


def last_save_dir():
    value = load_settings().get("last_save_dir")
    if value and Path(value).exists():
        return Path(value)
    return READY_DIR


def remember_save_dir(path):
    settings = load_settings()
    settings["last_save_dir"] = str(Path(path).parent)
    save_settings(settings)


def apple_script_text(value):
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def choose_save_path_macos(initial_dir, initial_file):
    script = (
        "set chosenFile to choose file name "
        "with prompt " + apple_script_text("Сохранить резюме") + " "
        "default name " + apple_script_text(initial_file) + " "
        "default location POSIX file " + apple_script_text(str(initial_dir)) + "\n"
        "POSIX path of chosenFile"
    )
    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    if result.returncode != 0:
        if "-128" in result.stderr:
            return ""
        raise RuntimeError(result.stderr.strip() or "Не удалось открыть окно сохранения")
    return result.stdout.strip()


def choose_save_path_tk(initial_dir, initial_file):
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    try:
        root.attributes("-topmost", True)
        return filedialog.asksaveasfilename(
            parent=root,
            initialdir=str(initial_dir),
            initialfile=initial_file,
            defaultextension=".docx",
            filetypes=[("Word document", "*.docx")],
            title="Сохранить резюме",
        )
    finally:
        root.destroy()


def choose_save_path(initial_dir, initial_file):
    if sys.platform == "darwin":
        return choose_save_path_macos(initial_dir, initial_file)
    return choose_save_path_tk(initial_dir, initial_file)


def safe_filename(name):
    cleaned = re.sub(r"[^\wа-яА-ЯёЁ ._-]+", "_", name, flags=re.UNICODE).strip()
    return cleaned or "resume"


@app.route("/")
def index():
    return render_template("index.html", fields=fields_for_job_count(2), app_mode=APP_MODE)


@app.route("/login", methods=["GET", "POST"])
def login():
    if not IS_CLOUD or not APP_PASSWORD:
        return redirect(url_for("index"))
    error = ""
    if request.method == "POST":
        password = request.form.get("password", "")
        if hmac.compare_digest(password, APP_PASSWORD):
            session["authenticated"] = True
            return redirect(url_for("index"))
        error = "Неверный пароль"
    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Вход</title>
  <link rel="stylesheet" href="/static/styles.css">
</head>
<body class="login-page">
  <form class="login-form" method="post">
    <h1>Конструктор резюме</h1>
    <p>Введите пароль доступа</p>
    <input name="password" type="password" autofocus>
    <button type="submit">Войти</button>
    <div class="login-error">{error}</div>
  </form>
</body>
</html>"""


@app.post("/upload")
def upload():
    ensure_dirs()
    uploaded = request.files.get("file")
    if not uploaded:
        return jsonify({"error": "Файл не выбран"}), 400
    source = request.form.get("source", "auto")
    original_name = safe_filename(uploaded.filename)
    session_id = uuid.uuid4().hex
    saved_path = UPLOAD_DIR / f"{session_id}_{original_name}"
    uploaded.save(saved_path)
    if not IS_CLOUD:
        shutil.copy2(saved_path, START_DIR / original_name)
    text = normalize_to_text(saved_path)
    data = parse_hh_resume(text) if source == "hh" else parse_resume(text)
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
    temp_output = Path(tempfile.gettempdir()) / f"{uuid.uuid4().hex}_{output_name}"
    fill_template(data, temp_output)
    if IS_CLOUD:
        output_path = READY_DIR / f"{uuid.uuid4().hex}_{output_name}"
        shutil.move(str(temp_output), output_path)
        SESSIONS[session_id]["data"] = data
        SESSIONS[session_id]["output"] = str(output_path)
        return send_file(
            output_path,
            as_attachment=True,
            download_name=output_name,
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    selected_path = choose_save_path(last_save_dir(), output_name)
    if not selected_path:
        temp_output.unlink(missing_ok=True)
        SESSIONS[session_id].pop("output", None)
        return jsonify({"cancelled": True, "message": "Сохранение отменено"})
    output_path = Path(selected_path)
    if output_path.suffix.lower() != ".docx":
        output_path = output_path.with_suffix(".docx")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(temp_output, output_path)
    temp_output.unlink(missing_ok=True)
    remember_save_dir(output_path)
    SESSIONS[session_id]["data"] = data
    SESSIONS[session_id]["output"] = str(output_path)
    return jsonify({"filename": output_name, "path": str(output_path)})


@app.post("/open-output-folder")
def open_output_folder():
    if IS_CLOUD:
        return jsonify({"error": "В cloud-режиме папка открывается на устройстве пользователя"}), 400
    payload = request.get_json(force=True)
    session_id = payload.get("session_id")
    session = SESSIONS.get(session_id)
    if not session or not session.get("output"):
        return jsonify({"error": "Сначала сохраните файл"}), 400
    output_path = Path(session["output"])
    if not output_path.exists():
        return jsonify({"error": "Сохраненный файл не найден"}), 404
    folder = output_path.parent
    if sys.platform == "darwin":
        subprocess.Popen(["open", str(folder)])
    elif sys.platform.startswith("win"):
        subprocess.Popen(["explorer", str(folder)])
    else:
        subprocess.Popen(["xdg-open", str(folder)])
    return jsonify({"ok": True})


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
    host = "0.0.0.0" if IS_CLOUD else "127.0.0.1"
    port = int(os.environ.get("PORT", "5000"))
    app.run(host=host, port=port, debug=False)
