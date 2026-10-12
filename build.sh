#!/usr/bin/env bash
# Render build: Django + yt-dlp + FFmpeg backend
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt
pip install -U yt-dlp

# Ensure Deno JS runtime is stored inside the project repository so Render preserves it in runtime
DENO_DIR="$PWD/.deno"
export DENO_INSTALL="$DENO_DIR"
export PATH="$DENO_DIR/bin:$PATH"
if [ ! -f "$DENO_DIR/bin/deno" ]; then
    curl -fsSL https://deno.land/install.sh | DENO_INSTALL="$DENO_DIR" sh || true
fi
mkdir -p "$PWD/bin"
if [ -f "$DENO_DIR/bin/deno" ]; then
    cp "$DENO_DIR/bin/deno" "$PWD/bin/deno" || true
    chmod +x "$PWD/bin/deno" || true
fi
export PATH="$PWD/bin:$PATH"
deno --version || true

# FFmpeg comes from imageio-ffmpeg (pip), no apt needed on free tier.
python -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())" || true

python manage.py migrate --no-input
python manage.py collectstatic --no-input --clear
