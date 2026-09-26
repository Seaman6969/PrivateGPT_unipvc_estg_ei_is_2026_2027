#!/bin/bash
set -e

cd "$(dirname "$0")"

APP_NAME="PrivateGPT"
OUTPUT="${APP_NAME}-x86_64.AppImage"

echo ">>> Sourcing virtual environment"
source v/bin/activate

echo ">>> Cleaning previous build artifacts"
rm -rf build dist "${APP_NAME}.AppDir" "${OUTPUT}"

echo ">>> Building binary with PyInstaller"
pyinstaller --clean --noconfirm privategpt.spec

echo ">>> Assembling AppDir"
mkdir -p "${APP_NAME}.AppDir/usr/bin"
mkdir -p "${APP_NAME}.AppDir/usr/share/icons/hicolor/256x256/apps"
cp -a dist/privategpt/* "${APP_NAME}.AppDir/usr/bin/"
cp assets/icon.png "${APP_NAME}.AppDir/${APP_NAME}.png"
cp assets/icon.png "${APP_NAME}.AppDir/usr/share/icons/hicolor/256x256/apps/${APP_NAME}.png"

cat > "${APP_NAME}.AppDir/${APP_NAME}.desktop" << 'EOF'
[Desktop Entry]
Name=PrivateGPT
Comment=Private procurement assistant
Exec=privategpt
Icon=PrivateGPT
Type=Application
Categories=Utility;
Terminal=false
EOF

cat > "${APP_NAME}.AppDir/AppRun" << 'EOF'
#!/bin/sh
HERE="$(dirname "$(readlink -f "${0}")")"
exec "${HERE}/usr/bin/privategpt" "$@"
EOF

chmod +x "${APP_NAME}.AppDir/AppRun"
chmod +x "${APP_NAME}.AppDir/usr/bin/privategpt"

echo ">>> Generating AppImage"
ARCH=x86_64 ./appimagetool --appimage-extract-and-run "${APP_NAME}.AppDir" "${OUTPUT}"

echo ">>> Cleaning temporary bytecode if any"
find . -not -path "./v*" -not -path "./${APP_NAME}.AppDir*" -not -path "./dist*" -not -path "./build*" \( -name "*pycache*" -o -name "*.pyc" \) -delete 2>/dev/null || true

echo
echo ">>> Build complete: $(pwd)/${OUTPUT}"
