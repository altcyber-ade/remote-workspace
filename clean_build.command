#!/bin/zsh
set -e
cd "$(dirname "$0")"
rm -rf build dist .build-venv
rm -f assets/RemoteWorkspace.icns
echo "Build artifacts removed."
