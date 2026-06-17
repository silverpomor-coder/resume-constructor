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
MAX_PHOTO_MB = int(os.environ.get("MAX_PHOTO_MB", "5"))
CORS_ALLOWED_ORIGINS = os.environ.get("CORS_ALLOWED_ORIGINS", "*")
CLEANUP_MAX_AGE_SECONDS = int(os.environ.get("CLEANUP_MAX_AGE_SECONDS", str(3 * 60 * 60)))
CLEANUP_INTERVAL_SECONDS = 15 * 60
TEMPLATE_DOCX_NAME = "CV_sample_v2.docx"
TEMPLATE_DOCX = RESOURCE_DIR / TEMPLATE_DOCX_NAME
if not TEMPLATE_DOCX.exists():
    TEMPLATE_DOCX = START_DIR / TEMPLATE_DOCX_NAME
SHABLON_DOCX_NAME = "shablon.docx"
SHABLON_DOCX = RESOURCE_DIR / SHABLON_DOCX_NAME
if not SHABLON_DOCX.exists():
    SHABLON_DOCX = START_DIR / SHABLON_DOCX_NAME

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_NS}
ET.register_namespace("w", W_NS)
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
W14_NS = "http://schemas.microsoft.com/office/word/2010/wordml"
WP_NS = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
PIC_NS = "http://schemas.openxmlformats.org/drawingml/2006/picture"
MC_NS = "http://schemas.openxmlformats.org/markup-compatibility/2006"
ET.register_namespace("a", A_NS)
ET.register_namespace("w14", W14_NS)
ET.register_namespace("wp", WP_NS)
ET.register_namespace("r", R_NS)
ET.register_namespace("pic", PIC_NS)
ET.register_namespace("mc", MC_NS)
PHOTO_REL_ID = "rId8"
PHOTO_MEDIA_PREFIX = "word/media/candidate_photo"
PHOTO_BOX_EMU = 1967865
IMAGE_CONTENT_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}
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


def allowed_cors_origin(origin):
    allowed = [item.strip() for item in CORS_ALLOWED_ORIGINS.split(",") if item.strip()]
    if not allowed:
        return ""
    if "*" in allowed:
        return origin or "*"
    return origin if origin in allowed else ""


FIELDS = [
    {"key": "role", "label": "Должность / желаемая роль"},
    {"key": "salary", "label": "Ожидаемый размер оплаты"},
    {"key": "fio", "label": "ФИО"},
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
    protected_paths = set()
    for session_id, data in list(SESSIONS.items()):
        if data.get("updated_at", data.get("created_at", now)) < cutoff:
            for key in ("source", "output", "photo_path"):
                value = data.get(key)
                if value:
                    Path(value).unlink(missing_ok=True)
            SESSIONS.pop(session_id, None)
            continue
        for key in ("source", "output", "photo_path"):
            value = data.get(key)
            if value:
                protected_paths.add(str(Path(value)))
    for directory in (UPLOAD_DIR, READY_DIR):
        if not directory.exists():
            continue
        for path in directory.iterdir():
            if path.is_file() and str(path) not in protected_paths and path.stat().st_mtime < cutoff:
                path.unlink(missing_ok=True)
    for session_id, data in list(SESSIONS.items()):
        output = data.get("output")
        source = data.get("source")
        photo = data.get("photo_path")
        if (output and not Path(output).exists()) or (source and not Path(source).exists()) or (photo and not Path(photo).exists()):
            SESSIONS.pop(session_id, None)


@app.before_request
def before_request():
    cleanup_old_files()
    if request.method == "OPTIONS":
        return None
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


@app.after_request
def add_cors_headers(response):
    origin = allowed_cors_origin(request.headers.get("Origin", ""))
    if origin:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Vary"] = "Origin"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Access-Key"
        response.headers["Access-Control-Expose-Headers"] = "Content-Disposition"
    return response


@app.errorhandler(RequestEntityTooLarge)
def upload_too_large(error):
    return jsonify({"error": f"Файл слишком большой. Максимум: {MAX_UPLOAD_MB} МБ"}), 413


def jpeg_size(data):
    if not data.startswith(b"\xff\xd8"):
        return None
    index = 2
    while index < len(data) - 9:
        if data[index] != 0xFF:
            index += 1
            continue
        marker = data[index + 1]
        index += 2
        if marker in (0xD8, 0xD9):
            continue
        length = int.from_bytes(data[index:index + 2], "big")
        if 0xC0 <= marker <= 0xC3:
            height = int.from_bytes(data[index + 3:index + 5], "big")
            width = int.from_bytes(data[index + 5:index + 7], "big")
            return width, height
        index += length
    return None


def png_size(data):
    if data[:8] != b"\x89PNG\r\n\x1a\n" or len(data) < 24:
        return None
    width = int.from_bytes(data[16:20], "big")
    height = int.from_bytes(data[20:24], "big")
    return width, height


def image_info(data):
    size = png_size(data)
    if size:
        return ".png", "image/png", size
    size = jpeg_size(data)
    if size:
        return ".jpeg", "image/jpeg", size
    return "", "", None


def photo_dimensions(photo_path):
    data = Path(photo_path).read_bytes()
    _, _, size = image_info(data)
    return size or (PHOTO_BOX_EMU, PHOTO_BOX_EMU)


def fitted_photo_extent(width, height):
    if not width or not height:
        return PHOTO_BOX_EMU, PHOTO_BOX_EMU
    scale = min(PHOTO_BOX_EMU / width, PHOTO_BOX_EMU / height)
    return max(1, int(width * scale)), max(1, int(height * scale))


def delete_session_photo(session_data):
    photo_path = session_data.get("photo_path")
    if photo_path:
        Path(photo_path).unlink(missing_ok=True)
    session_data.pop("photo_path", None)
    session_data.pop("photo_filename", None)


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


def normalize_spaces(value):
    return re.sub(r"\s+", " ", str(value or "").replace("\u00a0", " ")).strip()


def extract_email(text):
    return first_match(r"\b([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})\b", text)


def phone_digits(value):
    return re.sub(r"\D", "", value or "")


def is_valid_phone(value):
    digits = phone_digits(value)
    if len(digits) == 10:
        return digits.startswith("9")
    if len(digits) == 11:
        return digits.startswith(("7", "8")) and digits[1] == "9"
    return False


def extract_phone(text):
    pattern = re.compile(
        r"(?<!\d)(?:\+?\s*[78][\s\u00a0-]*)?\(?\d{3}\)?[\s\u00a0-]*\d{3}[\s\u00a0-]*\d{2}[\s\u00a0-]*\d{2}(?!\d)"
    )
    for match in pattern.finditer(text):
        candidate = normalize_spaces(match.group(0))
        if is_valid_phone(candidate):
            return candidate
    return ""


def value_after_label_filtered(lines, labels, validator=None, max_lookahead=3):
    validator = validator or (lambda value: True)
    lowered = [line.lower().strip(": ") for line in lines]
    for label in labels:
        target = label.lower().strip(": ")
        for index, clean in enumerate(lowered):
            if clean == target or clean.startswith(target + ":"):
                original = lines[index]
                candidates = []
                if ":" in original:
                    candidates.append(original.split(":", 1)[1].strip())
                candidates.extend(lines[index + 1:index + 1 + max_lookahead])
                for candidate in candidates:
                    candidate = normalize_spaces(candidate)
                    if candidate and not re.fullmatch(r"\d+\.?", candidate) and validator(candidate):
                        return candidate
    return ""


def amount_from_text(value):
    digits = re.sub(r"\D", "", value or "")
    return int(digits) if digits else 0


def is_money_value(value):
    text = normalize_spaces(value)
    lowered = text.lower()
    if not re.search(r"\d", text):
        return False
    has_money_word = any(token in lowered for token in ("₽", "руб", "р.", "р ", "на руки"))
    has_large_amount = bool(re.search(r"\b\d{2,3}(?:[ \u00a0]\d{3})+\b|\b\d{5,}\b", text))
    return (has_money_word or has_large_amount) and amount_from_text(text) >= 10000


def clean_salary_value(value):
    value = normalize_spaces(value)
    value = re.sub(
        r"^(?:зарплата|ожидаемый размер оплаты|ожидаемый размер зарплаты|желаемый доход|уровень дохода|желаемый уровень заработной платы)\s*:?\s*",
        "",
        value,
        flags=re.IGNORECASE,
    )
    if ":" in value:
        after = value.split(":", 1)[1].strip()
        if is_money_value(after):
            return after
    return value


def extract_salary_from_lines(lines, labels):
    value = value_after_label_filtered(lines, labels, is_money_value)
    if value:
        return clean_salary_value(value)
    for index, line in enumerate(lines):
        if any(label.lower() in line.lower() for label in labels):
            for candidate in lines[index:index + 4]:
                if is_money_value(candidate):
                    return clean_salary_value(candidate)
    return ""


def clean_web_references(value):
    text = str(value or "")
    if not text:
        return ""
    site_pattern = r"(?:https?://)?(?:www\.)?[A-Za-z0-9А-Яа-яЁё-]+(?:\.[A-Za-zА-Яа-яЁё]{2,})(?:/[^\s,;)\]]*)?"
    text = re.sub(rf"\[\[?[^\]\n]*{site_pattern}[^\]\n]*\]\([^)]+\)\]?(?:\([^)]+\))?", "", text, flags=re.IGNORECASE)
    text = re.sub(rf"\[[^\]\n]*{site_pattern}[^\]\n]*\]\([^)]+\)", "", text, flags=re.IGNORECASE)
    text = re.sub(site_pattern, "", text, flags=re.IGNORECASE)
    text = re.sub(r"[ \t]*,[ \t]*(?=\n|$)", "", text)
    text = re.sub(r",[ \t]*,", ",", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return "\n".join(line.strip(" ,;") for line in text.splitlines()).strip()


def clean_job_fields(data):
    for key in list(data.keys()):
        if re.fullmatch(r"job\d+_(city|site|description)", key):
            data[key] = clean_web_references(data.get(key, ""))
    return data


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
    if start is not None:
        for line in lines[start:]:
            lowered = line.lower()
            if lowered.startswith("опыт работы"):
                break
            if is_money_value(line):
                return normalize_spaces(line)
    return extract_salary_from_lines(lines, ["Ожидаемый размер зарплаты"])


def split_location_metro(value):
    value = normalize_spaces(value)
    if not value:
        return "", ""
    metro = ""
    location = value
    match = re.search(r"(?:^|[,;]\s*)(?:м\.|метро)\s*([^,;]+)", value, re.IGNORECASE)
    if match:
        metro = clean_metro_value(match.group(1))
        location = value[:match.start()].strip(" ,;")
    return location.strip(), metro.strip()


def clean_metro_value(value):
    value = normalize_spaces(value)
    value = re.sub(r"^(?:м\.|метро|станция метро|ст\.?\s*м\.?)\s*", "", value, flags=re.IGNORECASE)
    return value.strip(" ,;")


def hh_location(lines):
    value = first_match(r"^Проживает:\s*(.+)$", "\n".join(lines))
    if not value:
        return "", ""
    return split_location_metro(value)


def is_driving_line(value):
    lowered = normalize_spaces(value).lower()
    return any(token in lowered for token in (
        "права категории",
        "водительские права",
        "водительское удостоверение",
        "опыт вождения",
        "наличие в/у",
        "в/у",
        "собственный автомобиль",
        "личный автомобиль",
        "имеется автомобиль",
        "категория b",
        "категория в",
    ))


def extract_driving(lines, text, hh=False):
    if hh:
        block = block_after_exact(lines, "Опыт вождения", ["Дополнительная информация"])
        if block:
            return block

    labels = [
        "Наличие водительских прав",
        "Водительские права",
        "Права категории",
        "Опыт вождения",
        "Наличие В/У",
        "В/У",
        "Водительское удостоверение",
        "Наличие водительских прав. Фактический опыт вождения автомобиля.",
    ]
    value = value_after_label_filtered(lines, labels, lambda item: bool(item and not item.endswith("?")), max_lookahead=4)
    found = []
    if value:
        if re.fullmatch(r"[A-ZА-ЯЁ](?:\s*,\s*[A-ZА-ЯЁ])*", value, re.IGNORECASE):
            value = f"Права категории {value}"
        found.append(value)
    for line in lines:
        if is_driving_line(line):
            found.append(line)
    unique = []
    for item in found:
        item = normalize_spaces(item)
        if item and item.lower() not in {saved.lower() for saved in unique}:
            unique.append(item)
    return "\n".join(unique[:4]).strip()


def extract_registration(lines):
    return value_after_label_filtered(lines, [
        "Место регистрации",
        "Регистрация",
        "Адрес регистрации",
        "Постоянная регистрация",
        "Прописка",
        "Прописка по паспорту",
        "Место регистрации по паспорту",
    ], lambda value: not is_money_value(value))


def extract_location_and_metro(lines, text):
    raw_location = value_after_label_filtered(lines, [
        "Фактическое местонахождение",
        "Фактическое местонахождения",
        "Адрес фактического проживания",
        "Фактический адрес",
        "Место жительства",
        "Адрес проживания",
        "Проживает",
        "Город проживания",
        "Место рождения и жительства",
    ], lambda value: not is_money_value(value), max_lookahead=3)
    if not raw_location:
        raw_location = first_match(r"^Проживает:\s*(.+)$", "\n".join(lines))
    location, metro_from_location = split_location_metro(raw_location)

    district = value_after_label_filtered(lines, ["Район проживания"], lambda value: not is_money_value(value))
    if district and location:
        location = f"{location}; {district}"

    raw_metro = value_after_label_filtered(lines, [
        "Метро",
        "Станция метро",
        "Ближайшее метро",
        "Ближайшая станция метро",
        "Метро / станция электрички",
        "Станция электрички",
        "м.",
    ], lambda value: not is_money_value(value), max_lookahead=2)
    metro = clean_metro_value(raw_metro) or metro_from_location
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
    data["email"] = extract_email(text)
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
    data["driving"] = extract_driving(lines, text, hh=True)
    jobs = split_hh_jobs(hh_experience_block(lines).splitlines())
    for index, job in enumerate(jobs, 1):
        data[f"job{index}_period"] = job.get("period", "")
        data[f"job{index}_city"] = job.get("city", "")
        data[f"job{index}_site"] = job.get("site", "")
        data[f"job{index}_description"] = job.get("description", "")
    data["_job_count"] = len(jobs)

    return clean_job_fields(data)


def parse_resume(text):
    lines = compact_lines(text)
    data = {field["key"]: "" for field in fields_for_job_count(2)}

    data["email"] = extract_email(text)
    data["fio"] = (
        value_after_label(lines, ["Ф.И.О.", "ФИО"])
        or first_match(r"^([А-ЯЁ][а-яё]+ [А-ЯЁ][а-яё]+ [А-ЯЁ][а-яё]+)$", "\n".join(lines[:8]))
        or hh_fio(lines)
    )
    role_from_form = first_match(r"Анкета на вакансию\s+[«\"]([^»\"]+)[»\"]", text)
    data["role"] = value_after_label(lines, ["Желаемая должность"]) or role_from_form
    if not data["role"] and "Желаемая должность и зарплата" in text:
        data["role"] = value_after_label(lines, ["Желаемая должность и зарплата"])

    data["salary"] = extract_salary_from_lines(lines, [
        "Зарплата",
        "Ожидаемый размер оплаты",
        "Желаемый доход",
        "Уровень дохода",
        "Желаемый уровень заработной платы",
    ])
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
    data["registration"] = extract_registration(lines)
    data["location"], data["metro"] = extract_location_and_metro(lines, text)
    data["driving"] = extract_driving(lines, text)
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

    return clean_job_fields(data)


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


def remove_word_generated_ids(root):
    for element in root.iter():
        element.attrib.pop(f"{{{W14_NS}}}paraId", None)
        element.attrib.pop(f"{{{W14_NS}}}textId", None)


def remove_markup_compatibility_ignorable(root):
    root.attrib.pop(f"{{{MC_NS}}}Ignorable", None)


def remove_empty_row_properties(root):
    removed = 0
    for row in root.findall(".//w:tr", NS):
        trpr = row.find("./w:trPr", NS)
        if trpr is not None and not trpr.attrib and not list(trpr):
            row.remove(trpr)
            removed += 1
    return removed


def remove_empty_text_runs(root):
    removed_texts = 0
    removed_runs = 0
    parent_map = {child: parent for parent in root.iter() for child in parent}

    for text_node in list(root.findall(".//w:t", NS)):
        if text_node.text not in (None, ""):
            continue
        run = parent_map.get(text_node)
        if run is None or run.tag != f"{{{W_NS}}}r":
            continue
        run.remove(text_node)
        removed_texts += 1

    parent_map = {child: parent for parent in root.iter() for child in parent}
    for run in list(root.findall(".//w:r", NS)):
        children = list(run)
        if children and any(child.tag != f"{{{W_NS}}}rPr" for child in children):
            continue
        parent = parent_map.get(run)
        if parent is None:
            continue
        parent.remove(run)
        removed_runs += 1

    return removed_texts, removed_runs


def should_clean_word_generated_ids(part_name):
    return (
        part_name == "word/document.xml"
        or part_name.startswith("word/header")
        or part_name.startswith("word/footer")
        or part_name in {"word/footnotes.xml", "word/endnotes.xml"}
    )


def clean_word_generated_ids_in_parts(files):
    for name, content in list(files.items()):
        if not should_clean_word_generated_ids(name):
            continue
        try:
            root = ET.fromstring(content)
        except ET.ParseError:
            continue
        remove_word_generated_ids(root)
        files[name] = ET.tostring(root, encoding="utf-8", xml_declaration=True)


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
    city = clean_web_references(data.get(f"job{index}_city", ""))
    description = clean_web_references(data.get(f"job{index}_description", ""))
    lines = []
    if city:
        lines.append(f"Место работы: {city}")
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


def clear_row_height(row):
    trpr = row.find("./w:trPr", NS)
    if trpr is None:
        return
    for height in list(trpr.findall("./w:trHeight", NS)):
        trpr.remove(height)
    if not trpr.attrib and not list(trpr):
        row.remove(trpr)


def remove_table_rows(table, start_index, count):
    rows = table.findall("./w:tr", NS)
    for row in rows[start_index:start_index + count]:
        table.remove(row)


def row_text(row):
    return "".join(row.itertext())


def remove_rows_with_text(table, needle):
    for row in list(table.findall("./w:tr", NS)):
        if needle.lower() in row_text(row).lower():
            table.remove(row)


def insert_label_value_rows(table, insert_index, items):
    rows = table.findall("./w:tr", NS)
    if not rows:
        return
    template_row = deepcopy(rows[min(insert_index, len(rows) - 1)])
    for offset, (label, value) in enumerate(items):
        row = deepcopy(template_row)
        cells = row.findall("./w:tc", NS)
        if len(cells) >= 2:
            set_cell_text(cells[0], label)
            set_cell_text(cells[1], value)
        table.insert(insert_index + offset, row)


def ensure_content_type(files, extension, content_type):
    content_types_name = "[Content_Types].xml"
    if content_types_name not in files:
        return
    ns = {"ct": "http://schemas.openxmlformats.org/package/2006/content-types"}
    root = ET.fromstring(files[content_types_name])
    clean_extension = extension.lstrip(".")
    for node in root.findall("./ct:Default", ns):
        if node.attrib.get("Extension", "").lower() == clean_extension:
            node.set("ContentType", content_type)
            files[content_types_name] = ET.tostring(root, encoding="utf-8", xml_declaration=True)
            return
    ET.SubElement(root, "{http://schemas.openxmlformats.org/package/2006/content-types}Default", {
        "Extension": clean_extension,
        "ContentType": content_type,
    })
    files[content_types_name] = ET.tostring(root, encoding="utf-8", xml_declaration=True)


def document_relationships(files):
    rels_name = "word/_rels/document.xml.rels"
    root = ET.fromstring(files[rels_name])
    return rels_name, root


def remove_photo_relationship(rels_root):
    for rel in list(rels_root):
        if rel.attrib.get("Id") == PHOTO_REL_ID:
            rels_root.remove(rel)
            return


def set_photo_relationship(rels_root, target):
    for rel in rels_root:
        if rel.attrib.get("Id") == PHOTO_REL_ID:
            rel.set("Target", target)
            return
    ET.SubElement(rels_root, f"{{{REL_NS}}}Relationship", {
        "Id": PHOTO_REL_ID,
        "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image",
        "Target": target,
    })


def next_relationship_id(rels_root):
    used = {rel.attrib.get("Id", "") for rel in rels_root}
    index = 1
    while f"rId{index}" in used:
        index += 1
    return f"rId{index}"


def remove_relationships_by_target_prefix(rels_root, target_prefix):
    for rel in list(rels_root):
        if rel.attrib.get("Target", "").startswith(target_prefix):
            rels_root.remove(rel)


def add_image_relationship(rels_root, target):
    rel_id = next_relationship_id(rels_root)
    ET.SubElement(rels_root, f"{{{REL_NS}}}Relationship", {
        "Id": rel_id,
        "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image",
        "Target": target,
    })
    return rel_id


def update_photo_drawing_size(photo_cell, width, height):
    cx, cy = fitted_photo_extent(width, height)
    for extent in photo_cell.findall(f".//{{{WP_NS}}}extent"):
        extent.set("cx", str(cx))
        extent.set("cy", str(cy))
    for extent in photo_cell.findall(f".//{{{PIC_NS}}}spPr/{{{A_NS}}}xfrm/{{{A_NS}}}ext"):
        extent.set("cx", str(cx))
        extent.set("cy", str(cy))


def update_template_photo(files, tables, photo_path):
    try:
        photo_cell = tables[0].findall("./w:tr", NS)[2].findall("./w:tc", NS)[1]
    except IndexError:
        return
    rels_name, rels_root = document_relationships(files)
    files.pop("word/media/image1.jpeg", None)
    files.pop("word/media/candidate_photo.jpeg", None)
    files.pop("word/media/candidate_photo.png", None)

    if not photo_path:
        set_cell_text(photo_cell, "")
        remove_photo_relationship(rels_root)
        files[rels_name] = ET.tostring(rels_root, encoding="utf-8", xml_declaration=True)
        return

    photo_bytes = Path(photo_path).read_bytes()
    extension, content_type, dimensions = image_info(photo_bytes)
    if not dimensions:
        set_cell_text(photo_cell, "")
        remove_photo_relationship(rels_root)
        files[rels_name] = ET.tostring(rels_root, encoding="utf-8", xml_declaration=True)
        return
    media_name = f"{PHOTO_MEDIA_PREFIX}{extension}"
    files[media_name] = photo_bytes
    set_photo_relationship(rels_root, media_name.replace("word/", ""))
    ensure_content_type(files, extension, content_type)
    update_photo_drawing_size(photo_cell, *dimensions)
    files[rels_name] = ET.tostring(rels_root, encoding="utf-8", xml_declaration=True)


def build_inline_picture(rel_id, width, height, name="candidate_photo"):
    cx, cy = fitted_photo_extent(width, height)
    drawing = ET.Element(f"{{{W_NS}}}drawing")
    inline = ET.SubElement(drawing, f"{{{WP_NS}}}inline", {
        "distT": "0",
        "distB": "0",
        "distL": "0",
        "distR": "0",
    })
    ET.SubElement(inline, f"{{{WP_NS}}}extent", {"cx": str(cx), "cy": str(cy)})
    ET.SubElement(inline, f"{{{WP_NS}}}effectExtent", {"l": "0", "t": "0", "r": "0", "b": "0"})
    ET.SubElement(inline, f"{{{WP_NS}}}docPr", {"id": str(uuid.uuid4().int % 100000), "name": name})
    frame = ET.SubElement(inline, f"{{{WP_NS}}}cNvGraphicFramePr")
    ET.SubElement(frame, f"{{{A_NS}}}graphicFrameLocks", {"noChangeAspect": "1"})
    graphic = ET.SubElement(inline, f"{{{A_NS}}}graphic")
    graphic_data = ET.SubElement(graphic, f"{{{A_NS}}}graphicData", {
        "uri": "http://schemas.openxmlformats.org/drawingml/2006/picture",
    })
    picture = ET.SubElement(graphic_data, f"{{{PIC_NS}}}pic")
    non_visual = ET.SubElement(picture, f"{{{PIC_NS}}}nvPicPr")
    ET.SubElement(non_visual, f"{{{PIC_NS}}}cNvPr", {"id": "1", "name": name})
    ET.SubElement(non_visual, f"{{{PIC_NS}}}cNvPicPr")
    blip_fill = ET.SubElement(picture, f"{{{PIC_NS}}}blipFill")
    blip = ET.SubElement(blip_fill, f"{{{A_NS}}}blip")
    blip.set(f"{{{R_NS}}}embed", rel_id)
    stretch = ET.SubElement(blip_fill, f"{{{A_NS}}}stretch")
    ET.SubElement(stretch, f"{{{A_NS}}}fillRect")
    shape = ET.SubElement(picture, f"{{{PIC_NS}}}spPr")
    transform = ET.SubElement(shape, f"{{{A_NS}}}xfrm")
    ET.SubElement(transform, f"{{{A_NS}}}off", {"x": "0", "y": "0"})
    ET.SubElement(transform, f"{{{A_NS}}}ext", {"cx": str(cx), "cy": str(cy)})
    geometry = ET.SubElement(shape, f"{{{A_NS}}}prstGeom", {"prst": "rect"})
    ET.SubElement(geometry, f"{{{A_NS}}}avLst")
    return drawing


def set_cell_picture(cell, rel_id, width, height, name="candidate_photo"):
    for child in list(cell):
        if child.tag == f"{{{W_NS}}}p":
            cell.remove(child)
    paragraph = ET.SubElement(cell, f"{{{W_NS}}}p")
    paragraph_properties = ET.SubElement(paragraph, f"{{{W_NS}}}pPr")
    ET.SubElement(paragraph_properties, f"{{{W_NS}}}jc", {f"{{{W_NS}}}val": "center"})
    run = ET.SubElement(paragraph, f"{{{W_NS}}}r")
    run.append(build_inline_picture(rel_id, width, height, name=name))


def update_template_photo_v3(files, tables, photo_path):
    try:
        photo_cell = tables[0].findall("./w:tr", NS)[2].findall("./w:tc", NS)[1]
    except IndexError:
        return
    rels_name, rels_root = document_relationships(files)
    remove_relationships_by_target_prefix(rels_root, "media/candidate_photo")
    files.pop("word/media/candidate_photo.jpeg", None)
    files.pop("word/media/candidate_photo.png", None)

    if not photo_path:
        set_cell_text(photo_cell, "")
        files[rels_name] = ET.tostring(rels_root, encoding="utf-8", xml_declaration=True)
        return

    photo_bytes = Path(photo_path).read_bytes()
    extension, content_type, dimensions = image_info(photo_bytes)
    if not dimensions:
        set_cell_text(photo_cell, "")
        files[rels_name] = ET.tostring(rels_root, encoding="utf-8", xml_declaration=True)
        return
    media_name = f"{PHOTO_MEDIA_PREFIX}{extension}"
    files[media_name] = photo_bytes
    rel_id = add_image_relationship(rels_root, media_name.replace("word/", ""))
    ensure_content_type(files, extension, content_type)
    set_cell_picture(photo_cell, rel_id, *dimensions)
    files[rels_name] = ET.tostring(rels_root, encoding="utf-8", xml_declaration=True)


def sanitize_document_xml(root, files):
    remove_word_generated_ids(root)
    remove_markup_compatibility_ignorable(root)
    remove_empty_row_properties(root)
    remove_empty_text_runs(root)
    files["word/document.xml"] = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    clean_word_generated_ids_in_parts(files)


def fill_template_legacy(data, output_path, photo_path=None):
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_docx = Path(temp_dir) / "work.docx"
        shutil.copy2(TEMPLATE_DOCX, temp_docx)
        with zipfile.ZipFile(temp_docx, "r") as zin:
            files = {name: zin.read(name) for name in zin.namelist()}
        register_document_namespaces(files["word/document.xml"])
        root = ET.fromstring(files["word/document.xml"])
        tables = root.findall(".//w:tbl", NS)
        update_template_photo(files, tables, photo_path)

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
        remove_rows_with_text(tables[1], "Телефон")
        remove_rows_with_text(tables[1], "Электронная почта")
        set_by_pos(2, 3, 0, "agency_comment")
        try:
            remove_table_rows(tables[2], 0, 2)
        except IndexError:
            pass
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
            clear_row_height(row)
            set_cell_text(cells[0], period_with_duration(data.get(f"job{index}_period", "")))
            set_cell_text(cells[1], job_summary(data, index), bold_first_line=True)
        set_by_pos(5, 1, 1, "recommendations")

        sanitize_document_xml(root, files)
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zout:
            for name, content in files.items():
                zout.writestr(name, content)


def fill_template_v3(data, output_path, photo_path=None):
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_docx = Path(temp_dir) / "work.docx"
        shutil.copy2(SHABLON_DOCX, temp_docx)
        with zipfile.ZipFile(temp_docx, "r") as zin:
            files = {name: zin.read(name) for name in zin.namelist()}
        register_document_namespaces(files["word/document.xml"])
        root = ET.fromstring(files["word/document.xml"])
        tables = root.findall(".//w:tbl", NS)

        def set_by_pos(table_index, row_index, cell_index, key, bold_first_line=False, transform=None):
            try:
                row = tables[table_index].findall("./w:tr", NS)[row_index]
                cell = row.findall("./w:tc", NS)[cell_index]
            except IndexError:
                return
            value = data.get(key, "")
            if transform:
                value = transform(value)
            set_cell_text(cell, value, bold_first_line=bold_first_line)

        update_template_photo_v3(files, tables, photo_path)

        set_by_pos(0, 0, 0, "role", bold_first_line=True)
        set_by_pos(0, 1, 1, "salary")
        set_by_pos(0, 3, 1, "fio")
        set_by_pos(0, 4, 1, "citizenship")
        set_by_pos(0, 5, 1, "birth_place_date", transform=age_text)

        set_by_pos(1, 1, 1, "family")
        set_by_pos(1, 2, 1, "registration")
        set_by_pos(1, 3, 1, "location")
        set_by_pos(1, 4, 1, "metro")
        set_by_pos(1, 5, 1, "criminal_record")
        set_by_pos(1, 6, 1, "languages")
        set_by_pos(1, 7, 1, "driving")

        set_by_pos(2, 1, 0, "education_level")
        set_by_pos(2, 1, 1, "education")
        try:
            course_row = tables[2].findall("./w:tr", NS)[2]
            course_cells = course_row.findall("./w:tc", NS)
            if len(course_cells) >= 2:
                set_cell_text(course_cells[0], "Повышение квалификации, курсы")
                set_cell_text(course_cells[1], data.get("courses", ""))
        except IndexError:
            pass

        job_count = count_jobs(data)
        expand_employment_table(tables[3], job_count)
        for index in range(1, max(job_count, 1) + 1):
            try:
                row = tables[3].findall("./w:tr", NS)[index]
                cells = row.findall("./w:tc", NS)
            except IndexError:
                continue
            clear_row_height(row)
            if len(cells) >= 2:
                set_cell_text(cells[0], period_with_duration(data.get(f"job{index}_period", "")))
                set_cell_text(cells[1], job_summary(data, index), bold_first_line=True)

        set_by_pos(4, 1, 1, "recommendations")
        set_by_pos(4, 3, 0, "agency_comment")

        sanitize_document_xml(root, files)
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zout:
            for name, content in files.items():
                zout.writestr(name, content)


def fill_template(data, output_path, photo_path=None):
    if SHABLON_DOCX.exists():
        return fill_template_v3(data, output_path, photo_path)
    return fill_template_legacy(data, output_path, photo_path)


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
    now = time.time()
    SESSIONS[session_id] = {"source": str(saved_path), "filename": original_name, "text": text, "data": data, "created_at": now, "updated_at": now}
    return jsonify({
        "session_id": session_id,
        "filename": original_name,
        "text": text,
        "data": data,
        "fields": fields_for_job_count(data.get("_job_count", 0)),
    })


@app.post("/upload-photo")
def upload_photo():
    ensure_dirs()
    session_id = request.form.get("session_id", "")
    if session_id not in SESSIONS:
        return jsonify({"error": "Сначала загрузите резюме"}), 400
    uploaded = request.files.get("photo")
    if not uploaded:
        return jsonify({"error": "Фото не выбрано"}), 400
    original_name = uploaded.filename or ""
    extension = Path(original_name).suffix.lower()
    if extension not in IMAGE_CONTENT_TYPES:
        return jsonify({"error": "Поддерживаются только JPG и PNG"}), 400
    data = uploaded.read()
    if len(data) > MAX_PHOTO_MB * 1024 * 1024:
        return jsonify({"error": f"Фото слишком большое. Максимум: {MAX_PHOTO_MB} МБ"}), 413
    real_extension, content_type, dimensions = image_info(data)
    if real_extension not in IMAGE_CONTENT_TYPES or not dimensions:
        return jsonify({"error": "Файл не похож на корректное JPG/PNG фото"}), 400
    session_data = SESSIONS[session_id]
    delete_session_photo(session_data)
    photo_name = f"{session_id}_{uuid.uuid4().hex}{real_extension}"
    photo_path = UPLOAD_DIR / photo_name
    photo_path.write_bytes(data)
    session_data["photo_path"] = str(photo_path)
    session_data["photo_filename"] = safe_filename(original_name)
    session_data["updated_at"] = time.time()
    return jsonify({
        "ok": True,
        "filename": session_data["photo_filename"],
        "url": url_for("photo_preview", session_id=session_id, _=uuid.uuid4().hex),
        "width": dimensions[0],
        "height": dimensions[1],
    })


@app.post("/delete-photo")
def delete_photo():
    payload = request.get_json(force=True)
    session_id = payload.get("session_id", "")
    if session_id not in SESSIONS:
        return jsonify({"error": "Сначала загрузите резюме"}), 400
    delete_session_photo(SESSIONS[session_id])
    SESSIONS[session_id]["updated_at"] = time.time()
    return jsonify({"ok": True})


@app.get("/photo/<session_id>")
def photo_preview(session_id):
    session_data = SESSIONS.get(session_id)
    if not session_data or not session_data.get("photo_path"):
        return jsonify({"error": "Фото не загружено"}), 404
    photo_path = Path(session_data["photo_path"])
    if not photo_path.exists() or photo_path.parent != UPLOAD_DIR:
        return jsonify({"error": "Фото не найдено"}), 404
    return send_file(photo_path)


@app.post("/save")
def save():
    ensure_dirs()
    payload = request.get_json(force=True)
    session_id = payload.get("session_id")
    data = payload.get("data") or {}
    if session_id not in SESSIONS:
        return jsonify({"error": "Сначала загрузите файл"}), 400
    session_data = SESSIONS[session_id]
    fio = data.get("fio") or Path(SESSIONS[session_id]["filename"]).stem
    output_name = "CV_" + safe_filename(fio).replace(" ", "_") + ".docx"
    temp_output = Path(tempfile.gettempdir()) / f"{uuid.uuid4().hex}_{output_name}"
    fill_template(data, temp_output, session_data.get("photo_path"))
    if IS_CLOUD:
        output_path = READY_DIR / f"{uuid.uuid4().hex}_{output_name}"
        shutil.move(str(temp_output), output_path)
        session_data["data"] = data
        session_data["output"] = str(output_path)
        session_data["updated_at"] = time.time()
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
    session_data["data"] = data
    session_data["output"] = str(output_path)
    session_data["updated_at"] = time.time()
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
