#!/bin/zsh
set -euo pipefail
cd "$(dirname "$0")"

APP="dist/Remote Workspace.app"
ENTITLEMENTS="packaging/entitlements.plist"

if [[ ! -d "$APP" ]]; then
  echo "App not found. Build it first."
  exit 1
fi

echo "Developer ID Application identities:"
security find-identity -v -p codesigning | grep "Developer ID Application" || true
echo ""
read "IDENTITY?Paste the full Developer ID Application identity: "

if [[ -z "$IDENTITY" ]]; then
  echo "No identity entered."
  exit 1
fi

codesign \
  --force \
  --deep \
  --options runtime \
  --timestamp \
  --entitlements "$ENTITLEMENTS" \
  --sign "$IDENTITY" \
  "$APP"

codesign --verify --deep --strict --verbose=2 "$APP"
spctl --assess --type execute --verbose "$APP" || true

echo "Signed: $APP"
