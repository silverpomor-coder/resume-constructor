# Constructor Resume

Локальное Flask-приложение для распознавания резюме и сохранения результата в корпоративный DOCX.

## Локальный запуск

```bash
cd "/Users/mf/Library/Mobile Documents/com~apple~CloudDocs/Codex/ССА код/resume_project/Constructor_resume"
python3 app.py
```

Открыть:

```bash
open http://127.0.0.1:5000
```

В локальном режиме:

- `Сохранить` открывает системное окно выбора места;
- последняя выбранная папка запоминается в `app_settings.json`;
- `Открыть` открывает папку с сохраненным DOCX.

## Cloud-режим

Cloud-режим включается переменной окружения:

```bash
APP_MODE=cloud APP_PASSWORD="your-password" python3 app.py
```

Для сервера можно указать порт:

```bash
APP_MODE=cloud APP_PASSWORD="your-password" PORT=5000 python3 app.py
```

В cloud-режиме:

- приложение слушает `0.0.0.0`;
- вход защищен паролем из `APP_PASSWORD`;
- если `APP_PASSWORD` не задан, приложение пишет предупреждение в лог;
- `Сохранить` работает как скачивание DOCX через браузер;
- кнопка `Открыть` скрыта;
- исходники и готовые DOCX хранятся во временных папках;
- старые временные файлы автоматически очищаются.

## Настройки cloud

```bash
APP_MODE=cloud
APP_PASSWORD="your-password"
PORT=5000
MAX_UPLOAD_MB=16
CLEANUP_MAX_AGE_SECONDS=10800
```

- `MAX_UPLOAD_MB` ограничивает размер загружаемого файла.
- `CLEANUP_MAX_AGE_SECONDS` задает срок хранения временных файлов, по умолчанию 3 часа.

## Проверка

1. Запустить локально и проверить `Авто`, `HH`, сохранение и кнопку `Открыть`.
2. Запустить с `APP_MODE=cloud APP_PASSWORD=...`.
3. Проверить вход по паролю.
4. Загрузить резюме в режимах `Авто` и `HH`.
5. Нажать `Сохранить` и убедиться, что браузер скачивает DOCX.
