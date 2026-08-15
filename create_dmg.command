#!/bin/zsh
set -euo pipefail
cd "$(dirname "$0")"

APP="dist/Remote Workspace.app"
DMG="dist/Remote-Workspace-2.9-Universal.dmg"
STAGE="build/dmg-stage"

if [[ ! -d "$APP" ]]; then
  echo "App not found. Run ./build_universal_app.command first."
  exit 1
fi

rm -rf "$STAGE"
mkdir -p "$STAGE"
cp -R "$APP" "$STAGE/"
ln -s /Applications "$STAGE/Applications"

rm -f "$DMG"
hdiutil create \
  -volname "Remote Workspace" \
  -srcfolder "$STAGE" \
  -ov \
  -format UDZO \
  "$DMG"

echo ""
echo "Created:"
echo "  $(pwd)/$DMG"
