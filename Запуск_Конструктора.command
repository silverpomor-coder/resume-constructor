#!/bin/zsh

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$HOME/.venvs/constructor_resume"

cd "$PROJECT_DIR"

echo "Конструктор резюме"
echo "Папка проекта: $PROJECT_DIR"
echo ""

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 не найден."
  echo "Установи Python по инструкции из файла mac_migr.md."
  echo ""
  read "reply?Нажми Enter, чтобы закрыть окно..."
  exit 1
fi

if [ ! -d "$VENV_DIR" ]; then
  echo "Создаю окружение Python..."
  python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

echo "Проверяю зависимости..."
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo ""
echo "Запускаю приложение..."
echo "Адрес: http://127.0.0.1:5000"
echo "Чтобы остановить приложение, закрой это окно или нажми Control+C."
echo ""

python desktop_launcher.py
