const fileInput = document.getElementById("fileInput");
const sourceButtons = document.querySelectorAll(".source-button");
const saveButton = document.getElementById("saveButton");
const openFolderButton = document.getElementById("openFolderButton");
const statusLine = document.getElementById("status");
const sourceText = document.getElementById("sourceText");
const editorForm = document.getElementById("editorForm");
const preview = document.getElementById("preview");
const workspace = document.querySelector(".workspace");
const photoInput = document.getElementById("photoInput");
const photoPreview = document.getElementById("photoPreview");
const photoPlaceholder = document.getElementById("photoPlaceholder");
const photoStatus = document.getElementById("photoStatus");
const deletePhotoButton = document.getElementById("deletePhotoButton");

let currentSession = "";
let currentSource = "auto";
const isCloudMode = window.APP_MODE === "cloud";

if (isCloudMode) {
  openFolderButton.hidden = true;
}

function rebuildForm(fields) {
  window.FIELD_DEFS = fields;
  editorForm.innerHTML = "";
  for (const field of window.FIELD_DEFS) {
    const label = document.createElement("label");
    label.className = "field";
    const title = document.createElement("span");
    title.textContent = field.label;
    const input = document.createElement("textarea");
    input.name = field.key;
    input.rows = 2;
    label.append(title, input);
    editorForm.appendChild(label);
  }
}

function collectFormData() {
  const data = {};
  for (const field of window.FIELD_DEFS) {
    const input = editorForm.elements[field.key];
    data[field.key] = input ? input.value : "";
  }
  return data;
}

function fillForm(data) {
  for (const field of window.FIELD_DEFS) {
    const input = editorForm.elements[field.key];
    if (input) input.value = data[field.key] || "";
  }
  renderPreview();
}

function renderPreview() {
  const data = collectFormData();
  preview.innerHTML = "";
  for (const field of window.FIELD_DEFS) {
    const block = document.createElement("div");
    block.className = "preview-block";
    const title = document.createElement("div");
    title.className = "preview-title";
    title.textContent = field.label;
    const value = document.createElement("div");
    value.className = "preview-value";
    value.textContent = data[field.key] || "";
    block.append(title, value);
    preview.appendChild(block);
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
  photoPreview.src = url;
  photoPreview.hidden = false;
  photoPlaceholder.hidden = true;
  photoStatus.textContent = filename ? `Фото загружено: ${filename}` : "Фото загружено";
  deletePhotoButton.disabled = false;
}

function setSource(source) {
  currentSource = source;
  sourceButtons.forEach((button) => {
    button.classList.toggle("active", button.dataset.source === currentSource);
  });
}

async function uploadSelectedFile() {
  const file = fileInput.files[0];
  if (!file) return;
  statusLine.textContent = "Файл загружается и распознается...";
  const formData = new FormData();
  formData.append("file", file);
  formData.append("source", currentSource);
  const response = await fetch("/upload", { method: "POST", body: formData });
  const result = await response.json();
  if (!response.ok) {
    statusLine.textContent = result.error || "Не удалось загрузить файл";
    return;
  }
  currentSession = result.session_id;
  sourceText.textContent = result.text || "";
  rebuildForm(result.fields || window.FIELD_DEFS);
  fillForm(result.data || {});
  resetPhotoBlock();
  saveButton.disabled = false;
  openFolderButton.disabled = true;
  statusLine.textContent = `Загружен файл: ${result.filename}`;
}

sourceButtons.forEach((button) => {
  button.addEventListener("click", async () => {
    if (button.dataset.source === currentSource) return;
    setSource(button.dataset.source);
    await uploadSelectedFile();
  });
});

fileInput.addEventListener("change", uploadSelectedFile);

editorForm.addEventListener("input", renderPreview);

photoInput.addEventListener("change", async () => {
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
  const response = await fetch("/upload-photo", { method: "POST", body: formData });
  const result = await response.json();
  if (!response.ok) {
    photoStatus.textContent = result.error || "Не удалось загрузить фото";
    photoInput.value = "";
    return;
  }
  showPhoto(result.url, result.filename);
});

deletePhotoButton.addEventListener("click", async () => {
  if (!currentSession) return;
  const response = await fetch("/delete-photo", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: currentSession }),
  });
  const result = await response.json();
  if (!response.ok) {
    photoStatus.textContent = result.error || "Не удалось удалить фото";
    return;
  }
  resetPhotoBlock();
});

saveButton.addEventListener("click", async () => {
  if (!currentSession) return;
  statusLine.textContent = "Файл сохраняется...";
  const response = await fetch("/save", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: currentSession, data: collectFormData() }),
  });
  const contentType = response.headers.get("Content-Type") || "";
  if (response.ok && contentType.includes("application/vnd.openxmlformats-officedocument")) {
    const blob = await response.blob();
    const disposition = response.headers.get("Content-Disposition") || "";
    const match = disposition.match(/filename\*=UTF-8''([^;]+)|filename="?([^"]+)"?/);
    const filename = match ? decodeURIComponent(match[1] || match[2]) : "resume.docx";
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    URL.revokeObjectURL(link.href);
    link.remove();
    statusLine.textContent = `Скачано: ${filename}`;
    return;
  }
  const result = await response.json();
  if (result.cancelled) {
    openFolderButton.disabled = true;
    statusLine.textContent = result.message || "Сохранение отменено";
    return;
  }
  if (!response.ok) {
    openFolderButton.disabled = true;
    statusLine.textContent = result.error || "Не удалось сохранить файл";
    return;
  }
  openFolderButton.disabled = false;
  statusLine.textContent = `Сохранено: ${result.filename}`;
});

openFolderButton.addEventListener("click", async () => {
  if (!currentSession) return;
  const response = await fetch("/open-output-folder", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: currentSession }),
  });
  const result = await response.json();
  if (!response.ok) {
    statusLine.textContent = result.error || "Не удалось открыть папку";
  }
});

let drag = null;

document.querySelectorAll(".resizer").forEach((resizer) => {
  resizer.addEventListener("mousedown", (event) => {
    const columns = getComputedStyle(workspace).gridTemplateColumns.split(" ").map(parseFloat);
    drag = { startX: event.clientX, columns, index: [...workspace.children].indexOf(resizer) };
    document.body.style.userSelect = "none";
  });
});

document.addEventListener("mousemove", (event) => {
  if (!drag) return;
  const delta = event.clientX - drag.startX;
  const columns = [...drag.columns];
  const leftIndex = drag.index - 1;
  const rightIndex = drag.index + 1;
  columns[leftIndex] = Math.max(220, columns[leftIndex] + delta);
  columns[rightIndex] = Math.max(260, columns[rightIndex] - delta);
  workspace.style.gridTemplateColumns = columns.map((value, index) => index === 1 || index === 3 ? "6px" : `${value}px`).join(" ");
});

document.addEventListener("mouseup", () => {
  drag = null;
  document.body.style.userSelect = "";
});
