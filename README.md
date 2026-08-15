# Remote Workspace — V2.9

Remote Workspace is a Python/PySide6 SSH and SFTP desktop client with a neon dark UI, saved connections, multi-tab SSH sessions, local/remote file browsing, recursive transfers, and secure credential storage through the operating system keyring.

## macOS build

The macOS build targets a Universal 2 app for both Apple Silicon and Intel Macs.

### Quick start

Use a python.org Universal 2 Python 3.13 installation, then create the build environment:

```bash
/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m venv .build-venv
source .build-venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller
```

For the Universal 2 build, `cffi` and `cryptography` must also be Universal 2 binaries. The known-good setup used during development is:

```bash
python -m pip uninstall -y cffi
ARCHFLAGS="-arch arm64 -arch x86_64" \
python -m pip install --no-binary=cffi cffi

python -m pip uninstall -y cryptography
python -m pip install --only-binary=:all: "cryptography==44.0.1"
```

Generate the app icon if needed:

```bash
iconutil -c icns assets/RemoteWorkspace.iconset -o assets/RemoteWorkspace.icns
```

Build:

```bash
rm -rf build dist
python -m PyInstaller RemoteWorkspace.spec --clean --noconfirm
```

Verify the bundle is Universal 2:

```bash
python packaging/check_universal.py "dist/Remote Workspace.app"
```

Create the DMG:

```bash
chmod +x create_dmg.command
./create_dmg.command
```

For machines you control, the unsigned build can be used, although Gatekeeper may require right-click → Open on first launch. For clean distribution, use the included `sign_app.command` and `notarize_app.command` scripts with your own Apple Developer credentials.

## Windows AMD64 build

Windows builds should be produced on a Windows 10/11 x64 machine. PyInstaller does not cross-compile the Windows executable from macOS.

### Requirements

Install **Python 3.13 64-bit** from python.org and make sure the Python launcher (`py`) is installed.

### One-click build

From the repository root, run:

```bat
build_windows_amd64.bat
```

The script:

1. verifies that Python 3.13 is 64-bit,
2. creates a fresh `.build-venv`,
3. installs the project requirements and PyInstaller,
4. builds using `RemoteWorkspace-Windows.spec`, and
5. verifies that the packaged executable exists.

The finished portable application is created at:

```text
dist\Remote Workspace\Remote Workspace.exe
```

This is a PyInstaller **one-folder** build. Copy the entire:

```text
dist\Remote Workspace\
```

folder to another Windows AMD64 machine. Do not copy only `Remote Workspace.exe`, because the accompanying `_internal` directory contains the bundled Python runtime and dependencies.

The destination machine does **not** need Python installed.

### Manual Windows build

If you prefer to build manually:

```bat
py -3.13 -m venv .build-venv
call .build-venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller
python -m PyInstaller --clean --noconfirm RemoteWorkspace-Windows.spec
```

Saved credentials use Python `keyring`, which uses the Windows credential backend on Windows rather than macOS Keychain.

## Current features

- saved SSH destinations
- password and private-key authentication
- multi-tab SSH sessions
- interactive PTY-backed shell
- native macOS clipboard shortcuts
- cursor-aware terminal redraw handling
- shell command history with Up/Down
- terminal Tab completion
- SFTP local and remote browser
- recursive folder upload/download
- Finder/local drag-and-drop upload
- remote rename, delete, and new-folder operations
- transfer progress/history
- remembered local/remote paths per connection
- searchable connection sidebar
- neon dark interface

## Version history

### V2.9

Terminal Tab/Shift+Tab are intercepted before Qt focus traversal so shell/readline completion stays inside the terminal.

### V2.8

Introduced a cursor-aware VT-style renderer for common shell redraw behavior, fixed pasted trailing newlines auto-executing commands, history redraw, Backspace display, and SFTP path completion.

### V2.7

Corrected macOS Command/Control shortcut handling using Qt's platform-aware standard key matching.

### V2.6

Added terminal clipboard support and right-click Copy/Paste/Select All.

## macOS bundle identity

Bundle identifier: `net.alcyber.remoteworkspace`
