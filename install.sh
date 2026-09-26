#!/usr/bin/env bash
set -euo pipefail

REPO="/Seaman6969/PrivateGPT_unipvc_estg_ei_is_2026_2027"
APP_NAME="PrivateGPT"
BINARY_NAME="PrivateGPT-x86_64.AppImage"
INSTALL_DIR="${HOME}/.local/bin"
VERSION="${PRIVATEGPT_VERSION:-latest}"

info()  { printf '\033[1;34m[info]\033[0m  %s\n' "$*"; }
warn()  { printf '\033[1;33m[warn]\033[0m  %s\n' "$*" >&2; }
error() { printf '\033[1;31m[error]\033[0m %s\n' "$*" >&2; exit 1; }

# --- platform check ----------------------------------------------------------
[ "$(uname -s)" = "Linux" ] || error "This installer targets Linux."
[ "$(uname -m)" = "x86_64" ] || error "Only x86_64 is supported (got: $(uname -m))."

# --- resolve download URL ----------------------------------------------------
if [ "$VERSION" = "latest" ]; then
    DOWNLOAD_URL="https://github.com/${REPO}/releases/latest/download/${BINARY_NAME}"
else
    DOWNLOAD_URL="https://github.com/${REPO}/releases/download/${VERSION}/${BINARY_NAME}"
fi

command -v curl >/dev/null 2>&1 || error "curl is required."

# --- install -----------------------------------------------------------------
mkdir -p "$INSTALL_DIR"
TARGET="${INSTALL_DIR}/${BINARY_NAME}"

info "Downloading ${APP_NAME}..."
curl -fL --progress-bar -o "${TARGET}.tmp" "$DOWNLOAD_URL" \
    || error "Download failed: ${DOWNLOAD_URL}"
mv "${TARGET}.tmp" "$TARGET"
chmod +x "$TARGET"

# --- PATH (only if needed) ---------------------------------------------------
if ! case ":${PATH}:" in *:"${INSTALL_DIR}":*) true;; *) false;; esac; then
    for rc in "$HOME/.bashrc" "$HOME/.zshrc"; do
        [ -f "$rc" ] || continue
        grep -q "${INSTALL_DIR}" "$rc" || \
            echo "export PATH=\"${INSTALL_DIR}:\$PATH\"" >> "$rc"
    done
fi

# --- FUSE check: use extract-and-run if libfuse2 is missing ------------------
RUN_FLAGS=()
if ! ldconfig -p 2>/dev/null | grep -q 'libfuse\.so\.2'; then
    warn "libfuse2 not detected — falling back to --appimage-extract-and-run."
    RUN_FLAGS=(--appimage-extract-and-run)
fi

# --- launch ------------------------------------------------------------------
info "Launching ${APP_NAME}..."
exec "$TARGET" "${RUN_FLAGS[@]}"