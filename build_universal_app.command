#!/bin/zsh
set -euo pipefail
cd "$(dirname "$0")"

APP_NAME="Remote Workspace"
APP_PATH="$(pwd)/dist/${APP_NAME}.app"

echo ""
echo "Remote Workspace — Universal 2 Builder"
echo "======================================"
echo ""

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 was not found."
  exit 1
fi

echo "[1/7] Creating build environment..."
rm -rf .build-venv
python3 -m venv .build-venv
source .build-venv/bin/activate

echo "[2/7] Installing dependencies..."
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller

echo "[3/7] Inspecting build Python..."
PYTHON_BIN="$(python -c 'import sys; print(sys.executable)')"
file "$PYTHON_BIN" || true
lipo -info "$PYTHON_BIN" || true
echo ""
echo "A true Universal 2 build requires a Universal 2 Python runtime and"
echo "Universal 2 compatible native dependencies."
echo ""

echo "[4/7] Creating app icon..."
rm -f assets/RemoteWorkspace.icns
iconutil -c icns assets/RemoteWorkspace.iconset -o assets/RemoteWorkspace.icns

echo "[5/7] Cleaning old output..."
rm -rf build dist

echo "[6/7] Building Universal 2 app..."
if ! pyinstaller --clean --noconfirm RemoteWorkspace.spec; then
  echo ""
  echo "Universal 2 build failed."
  echo "Install a Universal 2 Python from python.org and run this script again."
  exit 1
fi

echo "[7/7] Verifying architectures..."
file "${APP_PATH}/Contents/MacOS/${APP_NAME}"
lipo -info "${APP_PATH}/Contents/MacOS/${APP_NAME}" || true
python packaging/check_universal.py "${APP_PATH}"

echo ""
echo "Built:"
echo "  ${APP_PATH}"
echo ""
echo "Next run:"
echo "  ./create_dmg.command"
