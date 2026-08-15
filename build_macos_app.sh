#!/bin/zsh
set -euo pipefail

cd "$(dirname "$0")"

echo ""
echo "Remote Workspace — macOS App Builder"
echo "===================================="
echo ""

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 was not found."
  echo "Install Python 3 first, then run this script again."
  exit 1
fi

echo "[1/6] Creating build virtual environment..."
python3 -m venv .build-venv
source .build-venv/bin/activate

echo "[2/6] Installing dependencies..."
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller

echo "[3/6] Creating macOS .icns app icon..."
rm -f assets/RemoteWorkspace.icns
iconutil -c icns assets/RemoteWorkspace.iconset -o assets/RemoteWorkspace.icns

echo "[4/6] Cleaning previous builds..."
rm -rf build dist

echo "[5/6] Building Remote Workspace.app..."
pyinstaller --clean --noconfirm RemoteWorkspace.spec

echo "[6/6] Done."
echo ""
echo "Your app is here:"
echo "  $(pwd)/dist/Remote Workspace.app"
echo ""
echo "To launch it:"
echo '  open "dist/Remote Workspace.app"'
echo ""
echo "If macOS blocks the first launch because the app is unsigned:"
echo '  xattr -dr com.apple.quarantine "dist/Remote Workspace.app"'
echo ""
