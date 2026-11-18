#!/usr/bin/env sh
set -eu
app_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
bin_dir="${XDG_BIN_HOME:-$HOME/.local/bin}"
chmod +x "$app_dir/Cyber" "$app_dir/videoai"
mkdir -p "$bin_dir"
if [ -e "$bin_dir/Cyber" ] || [ -L "$bin_dir/Cyber" ]; then
    if [ "$(readlink -f -- "$bin_dir/Cyber")" != "$app_dir/Cyber" ]; then
        printf '%s\n' "A different Cyber command already exists at $bin_dir/Cyber." >&2
        exit 1
    fi
else
    ln -s "$app_dir/Cyber" "$bin_dir/Cyber"
fi
"$app_dir/Cyber" --setup
case ":$PATH:" in
    *":$bin_dir:"*) printf '%s\n' "Start with: Cyber" ;;
    *) printf '%s\n' "Add $bin_dir to PATH, then run Cyber. For this session: export PATH=\"$bin_dir:\$PATH\"" ;;
esac
