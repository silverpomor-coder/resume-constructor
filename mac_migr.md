# Запуск приложения на другом Mac из iCloud

Инструкция для локального запуска проекта из iCloud Drive на новом Mac.

## 1. Дождаться синхронизации iCloud

Открой Finder и проверь, что папка проекта уже появилась:

```text
iCloud Drive/Codex/ССА код/resume_project/Constructor_resume
```

Если рядом с файлами есть значок облака, дождись загрузки или нажми правой кнопкой по папке проекта и выбери загрузку на Mac.

## 2. Открыть Терминал и войти в проект

```bash
cd "$HOME/Library/Mobile Documents/com~apple~CloudDocs/Codex/ССА код/resume_project/Constructor_resume"
```

Проверить, что ты в нужной папке:

```bash
pwd
ls
```

В списке должны быть файлы:

```text
app.py
requirements.txt
templates
static
Start
CV_sample_v2.docx
```

## 3. Проверить Python

```bash
python3 --version
```

Если появилась версия Python, например `Python 3.11...` или `Python 3.12...`, переходи к разделу 5.

Если команда не найдена или Python слишком старый, установи Python.

## 4. Установить Python при необходимости

### Вариант через Homebrew

Проверить Homebrew:

```bash
brew --version
```

Если Homebrew не установлен, установить его:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

После установки закрой и снова открой Терминал.

Установить Python:

```bash
brew install python
```

Проверить:

```bash
python3 --version
pip3 --version
```

Если macOS попросит установить Command Line Tools, согласись. Либо запусти:

```bash
xcode-select --install
```

## 5. Создать отдельное окружение для приложения

Чтобы не смешивать зависимости с системой, создаем отдельное окружение вне iCloud:

```bash
mkdir -p "$HOME/.venvs"
python3 -m venv "$HOME/.venvs/constructor_resume"
```

Активировать окружение:

```bash
source "$HOME/.venvs/constructor_resume/bin/activate"
```

В начале строки терминала должно появиться:

```text
(constructor_resume)
```

## 6. Установить зависимости приложения

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Проверить Flask:

```bash
python -c "import flask; print('Flask OK')"
```

## 7. Проверить macOS-инструмент чтения документов

Для чтения `.doc`, `.docx`, `.rtf` на Mac используется встроенный `textutil`.

```bash
which textutil
```

Нормальный результат:

```text
/usr/bin/textutil
```

## 8. Запустить приложение

Каждый раз перед запуском:

```bash
cd "$HOME/Library/Mobile Documents/com~apple~CloudDocs/Codex/ССА код/resume_project/Constructor_resume"
source "$HOME/.venvs/constructor_resume/bin/activate"
python app.py
```

Если все хорошо, появится строка примерно такого вида:

```text
Running on http://127.0.0.1:5000
```

## 9. Открыть приложение в браузере

В новом окне Терминала можно выполнить:

```bash
open http://127.0.0.1:5000
```

Или открыть этот адрес вручную в браузере:

```text
http://127.0.0.1:5000
```

Важно: не открывай файл `templates/index.html` напрямую. Приложение работает только через адрес `http://127.0.0.1:5000`.

## 10. Проверить работу

1. Выбери режим `HH`.
2. Нажми `Загрузить`.
3. Выбери тестовый файл:

```text
Start/test_Муратова.doc
```

4. Проверь, что распозналось ФИО.
5. Нажми `Сохранить`.
6. Выбери место сохранения в системном окне.
7. Нажми `Открыть` и проверь, что открылась папка с сохраненным DOCX.

## 11. Если путь сохранения остался от старого Mac

Приложение запоминает последнюю папку сохранения в файле:

```text
app_settings.json
```

Если на новом Mac путь неудобный или старый, можно сбросить настройку:

```bash
rm -f app_settings.json
```

После следующего сохранения приложение запомнит новую папку.

## 12. Остановка приложения

В окне Терминала, где запущено приложение, нажми:

```text
Control + C
```

## 13. Быстрый запуск после первой настройки

После первой установки обычно нужны только эти команды:

```bash
cd "$HOME/Library/Mobile Documents/com~apple~CloudDocs/Codex/ССА код/resume_project/Constructor_resume"
source "$HOME/.venvs/constructor_resume/bin/activate"
python app.py
```

Открыть:

```bash
open http://127.0.0.1:5000
```

## 14. Запуск двойным кликом

В корне проекта есть файл:

```text
Запуск_Конструктора.command
```

Его можно открыть двойным кликом. Он сам:

1. Перейдет в папку проекта.
2. Создаст Python-окружение, если его еще нет.
3. Установит зависимости из `requirements.txt`.
4. Запустит приложение.
5. Откроет браузер с адресом приложения.

Если macOS не разрешит открыть файл, выполни один раз:

```bash
cd "$HOME/Library/Mobile Documents/com~apple~CloudDocs/Codex/ССА код/resume_project/Constructor_resume"
chmod +x "Запуск_Конструктора.command"
```

После этого снова открой файл двойным кликом.
