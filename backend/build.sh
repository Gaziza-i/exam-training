#!/usr/bin/env bash
# Render build script: устанавливает зависимости, собирает статику и применяет миграции.
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate

# Наполняем базу демо-данными при первом деплое (безопасно перезапускать — get_or_create).
python manage.py seed_demo
