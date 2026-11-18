#!/usr/bin/env sh
set -eu
app_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
python_cmd=${PYTHON:-python3}
"$python_cmd" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else "Python 3.11 or newer is required.")'
if ! command -v ffmpeg >/dev/null 2>&1; then
    printf '%s\n' 'Install FFmpeg with libass first. On Debian/Ubuntu: sudo apt install ffmpeg fonts-noto-core python3-venv' >&2
    exit 1
fi
if ! ffmpeg -hide_banner -filters 2>/dev/null | grep -q 'subtitles'; then
    printf '%s\n' 'This FFmpeg build needs libass subtitle rendering.' >&2
    exit 1
fi
"$python_cmd" -m venv "$app_dir/.venv"
"$app_dir/.venv/bin/python" -m pip install -r "$app_dir/requirements.txt"
chmod +x "$app_dir/videoai"
printf '%s\n' "Installed. Start with: $app_dir/videoai"
