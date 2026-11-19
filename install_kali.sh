#!/usr/bin/env sh
set -eu
app_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
if ! grep -Eq '^ID="?kali"?$' /etc/os-release 2>/dev/null; then
    printf '%s\n' 'This installer targets Kali Linux. On other systems use sh install.sh.' >&2
    exit 1
fi
missing=""
for package in python3 python3-venv ffmpeg mpv fonts-noto-core curl; do
    state=$(dpkg-query -W -f='${db:Status-Status}' "$package" 2>/dev/null || true)
    [ "$state" = installed ] || missing="$missing $package"
done
if [ -n "$missing" ]; then
    printf 'Missing packages:%s\nInstall with APT? [y/N] ' "$missing"
    read -r answer
    case "$answer" in
        y|Y|yes|YES) ;;
        *) printf '%s\n' 'System packages were left alone.'; exit 1 ;;
    esac
    if [ "$(id -u)" -eq 0 ]; then
        apt-get update
        apt-get install $missing
    else
        sudo apt-get update
        sudo apt-get install $missing
    fi
fi
if ! command -v codex >/dev/null 2>&1 && [ ! -x "$HOME/.local/bin/codex" ]; then
    printf '%s\n' 'Installing the official Codex CLI for ChatGPT sign-in.'
    codex_installer=$(mktemp)
    trap 'rm -f -- "$codex_installer"' EXIT
    curl --fail --silent --show-error --location https://chatgpt.com/codex/install.sh -o "$codex_installer"
    sh "$codex_installer"
    rm -f -- "$codex_installer"
    trap - EXIT
fi
sh "$app_dir/install.sh"
test -x "$app_dir/.venv/bin/python" || python3 -m venv "$app_dir/.venv"
"$app_dir/.venv/bin/python" -m pip install -r "$app_dir/requirements-core.txt"
mpv --no-config --version >/dev/null
sample="$app_dir/examples/paise_aaye_ya_gaye.mp4"
if [ -f "$sample" ]; then
    mpv --no-config --hwdec=no --vo=null --ao=null --frames=15 "$sample"
fi
"$app_dir/.venv/bin/python" "$app_dir/main.py" --player-check
