#!/usr/bin/env sh
set -eu
app_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
bin_dir="${XDG_BIN_HOME:-$HOME/.local/bin}"
chmod +x "$app_dir/Cyber" "$app_dir/videoai"
mkdir -p "$bin_dir"
for command in Cyber videoai; do
    if [ -e "$bin_dir/$command" ] || [ -L "$bin_dir/$command" ]; then
        if [ "$(readlink -f -- "$bin_dir/$command")" != "$app_dir/$command" ]; then
            printf '%s\n' "A different command already exists at $bin_dir/$command." >&2
            exit 1
        fi
    else
        ln -s "$app_dir/$command" "$bin_dir/$command"
    fi
done
"$app_dir/Cyber" --setup
case ":$PATH:" in
    *":$bin_dir:"*) printf '%s\n' "Start with: videoai" ;;
    *) printf '%s\n' "Add $bin_dir to PATH, then run videoai. For this session: export PATH=\"$bin_dir:\$PATH\"" ;;
esac
