#!/usr/bin/env bash
set -euo pipefail

REPO="Seaman6969/PrivateGPT_unipvc_estg_ei_is_2026_2027"  
APP_NAME="PrivateGPT"
BINARY_NAME="PrivateGPT-x86_64.AppImage"
INSTALL_DIR="${HOME}/.local/bin"
VERSION="${PRIVATEGPT_VERSION:-latest}"

info()  { printf '\033[1;34m[info]\033[0m  %s\n' "$*"; }
warn()  { printf '\033[1;33m[warn]\033[0m  %s\n' "$*" >&2; }
error() { printf '\033[1;31m[error]\033[0m %s\n' "$*" >&2; exit 1; }

ensure_ollama() {
    if command -v ollama >/dev/null 2>&1; then
        info "ollama já está instalado: $(command -v ollama)"
        return 0
    fi

    info "ollama não encontrado. A tentar instalador oficial..."

    # --- tentativa 1: instalador oficial (silencioso) -----------------
    if curl -fsSL https://ollama.com/install.sh 2>/dev/null | sh >/dev/null 2>&1; then
        hash -r  # limpar cache do PATH
        if command -v ollama >/dev/null 2>&1; then
            info "ollama instalado via instalador oficial."
            return 0
        fi
    fi

    warn "Instalador oficial falhou. A descarregar binário estático..."

    # --- tentativa 2: binário estático do GitHub ----------------------
    local tmp url
    tmp="$(mktemp -d)"
    url="https://github.com/ollama/ollama/releases/latest/download/ollama-linux-amd64"

    if ! curl -fL --progress-bar -o "$tmp/ollama" "$url"; then
        warn "Não consegui descarregar o binário do ollama."
        warn "Instala manualmente: https://ollama.com/download"
        rm -rf "$tmp"
        return 1
    fi

    if [ ! -s "$tmp/ollama" ]; then
        warn "Binário vazio após download."
        rm -rf "$tmp"
        return 1
    fi

    # instalar em /usr/local/bin (requer sudo)
    if [ -w /usr/local/bin ]; then
        install -m 0755 "$tmp/ollama" /usr/local/bin/ollama
    elif command -v sudo >/dev/null 2>&1; then
        sudo install -m 0755 "$tmp/ollama" /usr/local/bin/ollama
    else
        warn "Sem permissão para escrever em /usr/local/bin e sem sudo."
        warn "Instala manualmente como root:"
        warn "  install -m 0755 $tmp/ollama /usr/local/bin/ollama"
        rm -rf "$tmp"
        return 1
    fi

    rm -rf "$tmp"
    hash -r

    if command -v ollama >/dev/null 2>&1; then
        info "ollama instalado em $(command -v ollama)."
        return 0
    fi

    warn "Instalação do ollama falhou."
    return 1
}

[ "$(uname -s)" = "Linux" ] || error "This installer targets Linux."
[ "$(uname -m)" = "x86_64" ] || error "Only x86_64 is supported (got: $(uname -m))."

if [ "$VERSION" = "latest" ]; then
    DOWNLOAD_URL="https://github.com/${REPO}/releases/latest/download/${BINARY_NAME}"
else
    DOWNLOAD_URL="https://github.com/${REPO}/releases/download/${VERSION}/${BINARY_NAME}"
fi

command -v curl >/dev/null 2>&1 || error "curl is required."

mkdir -p "$INSTALL_DIR"
TARGET="${INSTALL_DIR}/${BINARY_NAME}"

info "Downloading ${APP_NAME}..."
curl -fL --progress-bar -o "${TARGET}.tmp" "$DOWNLOAD_URL" \
    || error "Download failed: ${DOWNLOAD_URL}"
mv "${TARGET}.tmp" "$TARGET"
chmod +x "$TARGET"

if ! case ":${PATH}:" in *:"${INSTALL_DIR}":*) true;; *) false;; esac; then
    for rc in "$HOME/.bashrc" "$HOME/.zshrc"; do
        [ -f "$rc" ] || continue
        grep -q "${INSTALL_DIR}" "$rc" || \
            echo "export PATH=\"${INSTALL_DIR}:\$PATH\"" >> "$rc"
    done
fi

RUN_FLAGS=()
if ! ldconfig -p 2>/dev/null | grep -q 'libfuse\.so\.2'; then
    warn "libfuse2 not detected — falling back to --appimage-extract-and-run."
    RUN_FLAGS=(--appimage-extract-and-run)
fi

info "Launching ${APP_NAME}..."
exec "$TARGET" "${RUN_FLAGS[@]+"${RUN_FLAGS[@]}"}"
