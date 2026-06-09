const fileInput = document.getElementById("fileInput");
const saveButton = document.getElementById("saveButton");
const statusLine = document.getElementById("status");
const sourceText = document.getElementById("sourceText");
const editorForm = document.getElementById("editorForm");
const preview = document.getElementById("preview");
const workspace = document.querySelector(".workspace");

let currentSession = "";

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

fileInput.addEventListener("change", async () => {
  const file = fileInput.files[0];
  if (!file) return;
  statusLine.textContent = "Файл загружается и распознается...";
  const formData = new FormData();
  formData.append("file", file);
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
  saveButton.disabled = false;
  statusLine.textContent = `Загружен файл: ${result.filename}`;
});

editorForm.addEventListener("input", renderPreview);

saveButton.addEventListener("click", async () => {
  if (!currentSession) return;
  statusLine.textContent = "Файл сохраняется...";
  const response = await fetch("/save", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: currentSession, data: collectFormData() }),
  });
  const result = await response.json();
  if (!response.ok) {
    statusLine.textContent = result.error || "Не удалось сохранить файл";
    return;
  }
  statusLine.textContent = `Сохранено: ${result.path}`;
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
