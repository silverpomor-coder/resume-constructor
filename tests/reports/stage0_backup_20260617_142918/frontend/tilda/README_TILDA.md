# Tilda operator widget

Это рабочее место оператора для вставки в Tilda через блок T123.

## Файлы

- `index.html` - HTML блока.
- `style.css` - scoped-стили, все завязано на `#resume-constructor-widget`.
- `app.js` - логика загрузки, распознавания, фото и скачивания DOCX.

## Настройка API

В файле `app.js` замени:

```javascript
const API_BASE_URL = "https://api.service-agency.info";
```

Это текущий публичный адрес backend.

`ACCESS_KEY` пока не используется backend-ом. Он оставлен как заготовка:

```javascript
const ACCESS_KEY = "";
```

## Вставка в Tilda T123

Готовый вариант для Tilda T123: используйте файл `frontend/tilda/tilda_single_block.html`. Скопируйте его содержимое целиком и вставьте в HTML-код блока T123.

Минимальный вариант:

1. Вставь HTML из `index.html`.
2. Вставь CSS из `style.css` в тег `<style>...</style>`.
3. Вставь JS из `app.js` в тег `<script>...</script>`.
4. Удали строки с `<link rel="stylesheet" href="./style.css">` и `<script src="./app.js"></script>`, если CSS/JS вставлены внутрь T123.

## Backend

Для Tilda нужен CORS. Backend читает переменную:

```bash
CORS_ALLOWED_ORIGINS="https://www.service-agency.info"
```

Для теста можно оставить:

```bash
CORS_ALLOWED_ORIGINS="*"
```

Если `APP_PASSWORD` включен, браузеру может понадобиться авторизованная cookie backend-домена. Для MVP проще тестировать Tilda-виджет без `APP_PASSWORD` или на той же доверенной закрытой странице.

## Риск MVP

Без авторизации backend доступен всем, кто знает адрес. Для публичного сайта лучше включить пароль, ограничить `CORS_ALLOWED_ORIGINS` конкретным доменом и позже добавить ключ доступа.
