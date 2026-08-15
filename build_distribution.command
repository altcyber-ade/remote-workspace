#!/bin/zsh
set -euo pipefail
cd "$(dirname "$0")"

./build_universal_app.command
./create_dmg.command

echo ""
echo "Universal distribution build complete."
echo ""
echo "For clean external distribution:"
echo "  ./sign_app.command"
echo "  ./notarize_app.command"
echo "  ./create_dmg.command"
