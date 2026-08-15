#!/bin/zsh
set -euo pipefail
cd "$(dirname "$0")"

APP="dist/Remote Workspace.app"
ZIP="dist/Remote-Workspace-2.5-notarize.zip"

if [[ ! -d "$APP" ]]; then
  echo "App not found."
  exit 1
fi

echo "This uses an Apple notarytool Keychain profile."
echo ""
read "PROFILE?Profile name [RemoteWorkspaceNotary]: "
PROFILE="${PROFILE:-RemoteWorkspaceNotary}"

rm -f "$ZIP"
ditto -c -k --keepParent "$APP" "$ZIP"

xcrun notarytool submit "$ZIP" \
  --keychain-profile "$PROFILE" \
  --wait

xcrun stapler staple "$APP"
xcrun stapler validate "$APP"
spctl --assess --type execute --verbose "$APP"

echo ""
echo "Notarized successfully."
echo "Run ./create_dmg.command again for the final DMG."
