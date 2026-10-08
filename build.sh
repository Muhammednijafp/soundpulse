#!/usr/bin/env bash
# Render build: Django + yt-dlp + FFmpeg backend
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

# Ensure Deno JS runtime is available for yt-dlp YouTube deciphering
export DENO_INSTALL="${DENO_INSTALL:-$HOME/.deno}"
export PATH="$DENO_INSTALL/bin:$PATH"
if ! command -v deno >/dev/null 2>&1; then
    curl -fsSL https://deno.land/install.sh | sh || true
fi
export PATH="$DENO_INSTALL/bin:$PATH"
deno --version || true

# FFmpeg comes from imageio-ffmpeg (pip), no apt needed on free tier.
python -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())" || true

python manage.py migrate --no-input
python manage.py collectstatic --no-input --clear
