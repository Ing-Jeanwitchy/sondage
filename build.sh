#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "==> Enstalasyon depandans Python yo..."
pip install -r requirements.txt

echo "==> Koleksyon fichye estatik Django (WhiteNoise)..."
python manage.py collectstatic --no-input

echo "==> Ekzekisyon migrasyon baz de done PostgreSQL..."
python manage.py migrate

echo "==> Senkwonizasyon tradiksyon yo nan baz de done..."
python manage.py seed_translations
