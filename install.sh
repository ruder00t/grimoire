#!/usr/bin/env bash
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SOURCE="$SCRIPT_DIR/grim.py"
BINDIR="${BINDIR:-/usr/local/bin}"
TARGET="$BINDIR/grim"

run_priv() {
    if [ "$(id -u)" -eq 0 ]; then
        "$@"
    elif command -v sudo >/dev/null 2>&1; then
        sudo "$@"
    else
        echo "error: root privileges required for: $*" >&2
        return 1
    fi
}

bindir_writable() {
    if [ -d "$BINDIR" ]; then
        [ -w "$BINDIR" ]
    else
        [ -w "$(dirname "$BINDIR")" ]
    fi
}

put_launcher() {
    if bindir_writable; then
        mkdir -p "$BINDIR"
        install -m 0755 "$1" "$TARGET"
    else
        run_priv mkdir -p "$BINDIR"
        run_priv install -m 0755 "$1" "$TARGET"
    fi
}

if [ "${1:-}" = "--uninstall" ]; then
    if [ -e "$TARGET" ]; then
        if bindir_writable; then rm -f "$TARGET"; else run_priv rm -f "$TARGET"; fi
        echo "Removed $TARGET"
    else
        echo "Nothing to remove at $TARGET"
    fi
    exit 0
fi

if [ ! -f "$SOURCE" ]; then
    echo "error: grim.py not found next to this script ($SOURCE)" >&2
    exit 1
fi

PY="$(command -v python3 || true)"
if [ -z "$PY" ]; then
    echo "error: python3 is not installed or not on PATH." >&2
    exit 1
fi

if ! "$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)'; then
    echo "error: Python 3.8 or newer is required." >&2
    exit 1
fi

if ! bindir_writable && [ "$(id -u)" -ne 0 ] && ! command -v sudo >/dev/null 2>&1; then
    echo "error: cannot write $BINDIR and sudo is unavailable." >&2
    echo "Re-run as root, or install somewhere you own:" >&2
    echo "    BINDIR=\"\$HOME/.local/bin\" bash install.sh" >&2
    exit 1
fi

# Ensure grim.py is readable by everyone (does not touch the executable bit,
# so git sees no change); best-effort.
run_priv chmod a+r "$SOURCE" 2>/dev/null || chmod a+r "$SOURCE" 2>/dev/null || true

# Install a small launcher so grim.py needs neither an execute bit nor a
# specific owner. It runs grim.py with the python3 found at install time.
tmp="$(mktemp)"
printf '#!/bin/sh\nexec "%s" "%s" "$@"\n' "$PY" "$SOURCE" > "$tmp"
chmod 0755 "$tmp"
put_launcher "$tmp"
rm -f "$tmp"
echo "Installed $TARGET (runs $SOURCE)"

case ":$PATH:" in
    *":$BINDIR:"*) ;;
    *)
        echo
        echo "note: $BINDIR is not on your PATH. Add it to your shell config:"
        echo "    export PATH=\"$BINDIR:\$PATH\""
        ;;
esac

have_clipboard() {
    command -v wl-copy >/dev/null 2>&1 || command -v xclip >/dev/null 2>&1 \
        || command -v xsel >/dev/null 2>&1 || command -v pbcopy >/dev/null 2>&1
}

if have_clipboard; then
    :
elif [ "$(uname)" = "Darwin" ]; then
    :
else
    if [ "${XDG_SESSION_TYPE:-}" = "wayland" ]; then
        pkg="wl-clipboard"
    else
        pkg="xclip"
    fi
    echo
    echo "No clipboard tool found; installing $pkg..."
    installed=1
    if command -v apt-get >/dev/null 2>&1; then
        run_priv apt-get install -y "$pkg" && installed=0
    elif command -v dnf >/dev/null 2>&1; then
        run_priv dnf install -y "$pkg" && installed=0
    elif command -v pacman >/dev/null 2>&1; then
        run_priv pacman -S --noconfirm "$pkg" && installed=0
    elif command -v zypper >/dev/null 2>&1; then
        run_priv zypper install -y "$pkg" && installed=0
    else
        echo "No supported package manager found."
        echo "Install one of wl-clipboard / xclip / xsel manually."
        installed=0
    fi
    if [ "$installed" -ne 0 ]; then
        echo "warning: clipboard install failed; install $pkg manually."
    fi
fi

echo
echo "Done. Run 'grim --help' to get started."
