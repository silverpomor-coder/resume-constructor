(function () {
  const API_BASE_URL = "https://api.service-agency.info";
  const ACCESS_KEY = "";

  const root = document.getElementById("resume-constructor-widget");
  if (!root) return;

  const DEFAULT_FIELDS = [
    { key: "role", label: "Должность / желаемая роль" },
    { key: "salary", label: "Ожидаемый размер оплаты" },
    { key: "fio", label: "ФИО" },
    { key: "citizenship", label: "Гражданство" },
    { key: "birth_place_date", label: "Место и дата рождения" },
    { key: "family", label: "Семейное положение / дети" },
    { key: "registration", label: "Место регистрации" },
    { key: "location", label: "Фактическое местонахождение" },
    { key: "metro", label: "Метро / станция электрички" },
    { key: "criminal_record", label: "Наличие судимости" },
    { key: "languages", label: "Знание иностранных языков" },
    { key: "medical_book", label: "Наличие медицинской книжки" },
    { key: "driving", label: "Водительские права, стаж, собственный автомобиль" },
    { key: "agency_comment", label: "Комментарий Агентства" },
    { key: "education_level", label: "Образование" },
    { key: "education", label: "Учебное заведение, год окончания" },
    { key: "courses", label: "Повышение квалификации, курсы" },
    { key: "recommendations", label: "Наличие рекомендаций" },
  ];

  let fieldDefs = DEFAULT_FIELDS;
  let currentSession = "";
  let currentSource = "auto";

  const fileInput = root.querySelector("[data-rc-file]");
  const sourceButtons = root.querySelectorAll("[data-rc-source]");
  const saveButton = root.querySelector("[data-rc-save]");
  const healthButton = root.querySelector("[data-rc-health]");
  const statusLine = root.querySelector("[data-rc-status]");
  const sourceText = root.querySelector("[data-rc-source-text]");
  const editorForm = root.querySelector("[data-rc-editor]");
  const photoInput = root.querySelector("[data-rc-photo]");
  const photoPreview = root.querySelector("[data-rc-photo-preview]");
  const photoPlaceholder = root.querySelector("[data-rc-photo-placeholder]");
  const photoStatus = root.querySelector("[data-rc-photo-status]");
  const deletePhotoButton = root.querySelector("[data-rc-delete-photo]");

  function apiUrl(path) {
    return `${API_BASE_URL.replace(/\/$/, "")}${path}`;
  }

  function absoluteUrl(url) {
    if (!url) return "";
    if (/^https?:\/\//i.test(url)) return url;
    return apiUrl(url.startsWith("/") ? url : `/${url}`);
  }

  function requestOptions(options) {
    const next = Object.assign({ credentials: "include" }, options || {});
    next.headers = Object.assign({}, next.headers || {});
    if (ACCESS_KEY) next.headers["X-Access-Key"] = ACCESS_KEY;
    return next;
  }

  function setStatus(text) {
    statusLine.textContent = text;
  }

  function applyFieldStyles(label, title, input) {
    label.style.display = "block";
    label.style.padding = "10px 0";
    label.style.borderBottom = "1px solid #eeeeee";
    title.style.display = "block";
    title.style.marginBottom = "6px";
    title.style.fontWeight = "700";
    input.style.width = "100%";
    input.style.minHeight = "38px";
    input.style.resize = "vertical";
    input.style.padding = "8px";
    input.style.border = "1px solid #bbbbbb";
    input.style.borderRadius = "4px";
    input.style.font = "inherit";
    input.style.lineHeight = "1.35";
  }

  function visibleFields(fields) {
    return (fields || []).filter((field) => {
      const key = field.key || "";
      return !["email", "phone", "telephone", "mobile", "candidate_phone"].includes(key)
        && !/^job\d+_(site|url|website)$/i.test(key);
    });
  }

  function savePayload() {
    const data = collectFormData();
    for (const key of ["email", "phone", "telephone", "mobile", "candidate_phone"]) {
      delete data[key];
    }
    return data;
  }

  function rebuildForm(fields) {
    const nextFields = visibleFields(fields && fields.length ? fields : DEFAULT_FIELDS);
    fieldDefs = nextFields.length ? nextFields : visibleFields(DEFAULT_FIELDS);
    editorForm.innerHTML = "";
    for (const field of fieldDefs) {
      const label = document.createElement("label");
      label.className = "rc-field";
      const title = document.createElement("span");
      title.textContent = field.label;
      const input = document.createElement("textarea");
      input.name = field.key;
      input.rows = 2;
      applyFieldStyles(label, title, input);
      label.append(title, input);
      editorForm.appendChild(label);
    }
  }

  function collectFormData() {
    const data = {};
    for (const field of fieldDefs) {
      const input = editorForm.elements[field.key];
      data[field.key] = input ? input.value : "";
    }
    return data;
  }

  function fillForm(data) {
    for (const field of fieldDefs) {
      const input = editorForm.elements[field.key];
      if (input) input.value = data[field.key] || "";
    }
  }

  function resetPhotoBlock() {
    photoInput.value = "";
    photoPreview.hidden = true;
    photoPreview.removeAttribute("src");
    photoPlaceholder.hidden = false;
    photoStatus.textContent = "Фото не загружено";
    deletePhotoButton.disabled = true;
  }

  function showPhoto(url, filename) {
    photoPreview.src = absoluteUrl(url);
    photoPreview.hidden = false;
    photoPlaceholder.hidden = true;
    photoStatus.textContent = filename ? `Фото загружено: ${filename}` : "Фото загружено";
    deletePhotoButton.disabled = false;
  }

  function setSource(source) {
    currentSource = source;
    sourceButtons.forEach((button) => {
      button.classList.toggle("rc-active", button.dataset.rcSource === currentSource);
    });
  }

  async function readJson(response) {
    const text = await response.text();
    if (!text) return {};
    try {
      return JSON.parse(text);
    } catch (error) {
      return { error: text };
    }
  }

  function downloadFilename(disposition) {
    const encoded = disposition.match(/filename\*=UTF-8''([^;]+)/i);
    if (encoded) return decodeURIComponent(encoded[1]);
    const plain = disposition.match(/filename="?([^";]+)"?/i);
    return plain ? plain[1] : "resume.docx";
  }

  async function uploadSelectedFile() {
    const file = fileInput.files[0];
    if (!file) return;
    setStatus("Файл загружается и распознается...");
    const formData = new FormData();
    formData.append("file", file);
    formData.append("source", currentSource);
    const response = await fetch(apiUrl("/upload"), requestOptions({ method: "POST", body: formData }));
    const result = await readJson(response);
    if (!response.ok) {
      setStatus(result.error || "Не удалось загрузить файл");
      return;
    }
    currentSession = result.session_id;
    sourceText.textContent = result.text || "";
    rebuildForm(result.fields);
    fillForm(result.data || {});
    resetPhotoBlock();
    saveButton.disabled = false;
    setStatus(`Загружен файл: ${result.filename}`);
  }

  async function uploadPhoto() {
    const file = photoInput.files[0];
    if (!file) return;
    if (!currentSession) {
      photoStatus.textContent = "Сначала загрузите резюме";
      photoInput.value = "";
      return;
    }
    photoStatus.textContent = "Фото загружается...";
    const formData = new FormData();
    formData.append("session_id", currentSession);
    formData.append("photo", file);
    const response = await fetch(apiUrl("/upload-photo"), requestOptions({ method: "POST", body: formData }));
    const result = await readJson(response);
    if (!response.ok) {
      photoStatus.textContent = result.error || "Не удалось загрузить фото";
      photoInput.value = "";
      return;
    }
    showPhoto(result.url || `/photo/${currentSession}`, result.filename);
  }

  async function deletePhoto() {
    if (!currentSession) return;
    const response = await fetch(apiUrl("/delete-photo"), requestOptions({
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: currentSession }),
    }));
    const result = await readJson(response);
    if (!response.ok) {
      photoStatus.textContent = result.error || "Не удалось удалить фото";
      return;
    }
    resetPhotoBlock();
  }

  async function saveDocx() {
    if (!currentSession) return;
    setStatus("Файл сохраняется...");
    const response = await fetch(apiUrl("/save"), requestOptions({
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: currentSession, data: savePayload() }),
    }));
    const contentType = response.headers.get("Content-Type") || "";
    if (response.ok && contentType.includes("application/vnd.openxmlformats-officedocument")) {
      const blob = await response.blob();
      const disposition = response.headers.get("Content-Disposition") || "";
      const filename = downloadFilename(disposition);
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      URL.revokeObjectURL(link.href);
      link.remove();
      setStatus(`Скачано: ${filename}`);
      return;
    }
    const result = await readJson(response);
    setStatus(result.error || "Не удалось сохранить файл");
  }

  async function checkHealth() {
    setStatus("Проверяю backend...");
    const response = await fetch(apiUrl("/health"), requestOptions({ method: "GET" }));
    const result = await readJson(response);
    setStatus(response.ok && result.ok ? "Backend доступен" : "Backend недоступен");
  }

  sourceButtons.forEach((button) => {
    button.addEventListener("click", async () => {
      if (button.dataset.rcSource === currentSource) return;
      setSource(button.dataset.rcSource);
      await uploadSelectedFile();
    });
  });
  fileInput.addEventListener("change", uploadSelectedFile);
  photoInput.addEventListener("change", uploadPhoto);
  deletePhotoButton.addEventListener("click", deletePhoto);
  saveButton.addEventListener("click", saveDocx);
  healthButton.addEventListener("click", checkHealth);

  rebuildForm(DEFAULT_FIELDS);
}());
