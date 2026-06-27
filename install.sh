#!/usr/bin/env bash
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SOURCE="$SCRIPT_DIR/grim.py"
BINDIR="${BINDIR:-$HOME/.local/bin}"
TARGET="$BINDIR/grim"

if [ "${1:-}" = "--uninstall" ]; then
    if [ -L "$TARGET" ]; then
        rm -f "$TARGET"
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

if ! command -v python3 >/dev/null 2>&1; then
    echo "error: python3 is not installed or not on PATH." >&2
    exit 1
fi

if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)'; then
    echo "error: Python 3.8 or newer is required." >&2
    exit 1
fi

chmod +x "$SOURCE"
mkdir -p "$BINDIR"
ln -sf "$SOURCE" "$TARGET"
echo "Linked $TARGET -> $SOURCE"

case ":$PATH:" in
    *":$BINDIR:"*) ;;
    *)
        echo
        echo "note: $BINDIR is not on your PATH."
        echo "Add this to your ~/.bashrc or ~/.zshrc, then open a new shell:"
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
        sudo apt-get install -y "$pkg" && installed=0
    elif command -v dnf >/dev/null 2>&1; then
        sudo dnf install -y "$pkg" && installed=0
    elif command -v pacman >/dev/null 2>&1; then
        sudo pacman -S --noconfirm "$pkg" && installed=0
    elif command -v zypper >/dev/null 2>&1; then
        sudo zypper install -y "$pkg" && installed=0
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
