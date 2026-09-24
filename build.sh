#!/usr/bin/env bash
# Exit on error
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

# Ensure Deno JS runtime is available for yt-dlp on Linux
if ! command -v deno &> /dev/null; then
    curl -fsSL https://deno.land/install.sh | sh || true
fi

python manage.py migrate --no-input
python manage.py collectstatic --no-input

