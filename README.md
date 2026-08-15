# Remote Workspace — V2.5 Universal macOS Distribution

This package is set up to produce a portable macOS release for both Apple Silicon and Intel Macs.

## Quick start

Double-click:

`build_distribution.command`

That attempts a Universal 2 build, verifies the architectures in the app bundle, and creates:

`dist/Remote Workspace.app`

and:

`dist/Remote-Workspace-2.5-Universal.dmg`

The receiving Mac does not need Python installed.

## Universal 2 requirement

PyInstaller can build `arm64`, `x86_64`, or `universal2` apps on macOS, but a Universal 2 build requires the Python runtime and native dependencies used during the build to contain both architectures.

For the simplest setup, use a Universal 2 Python installer from python.org on the build Mac.

The included build script scans Mach-O files inside the finished `.app` and fails if it finds components missing `arm64` or `x86_64`.

## DMG

`create_dmg.command` creates a compressed DMG with:

- `Remote Workspace.app`
- an `Applications` shortcut

so the app can be installed by dragging it to Applications.

## Signing and notarization

For machines you control, the unsigned build can be used, although Gatekeeper may require right-click → Open on first launch.

For clean distribution to other users, use an Apple Developer Program account with a Developer ID Application certificate, then run:

`./sign_app.command`

Store notarization credentials in Keychain with Apple's `notarytool`, then run:

`./notarize_app.command`

Finally recreate the DMG:

`./create_dmg.command`

No Apple credentials are embedded in this project.

## Version

Remote Workspace 2.5  
Bundle identifier: `net.alcyber.remoteworkspace`


## V2.6 clipboard update

The terminal now supports native macOS clipboard shortcuts:

- Command-C copies selected terminal text
- Command-V pastes clipboard text into the SSH session
- Command-A selects all terminal text
- Control-C copies when text is selected; otherwise it sends the SSH interrupt character
- Control-Shift-C / Control-Shift-V provide terminal-style copy/paste
- Right-click provides Copy, Paste, and Select All
- Multi-line pasted text is normalized for terminal Enter handling


## V2.7 macOS clipboard correction

V2.6 incorrectly assumed that Qt's MetaModifier represented the macOS Command
key. Qt intentionally swaps Command and Control on Apple platforms.

V2.7 now uses Qt's platform-aware StandardKey matching:

- Command-C: copy selected terminal text
- Command-V: paste clipboard into SSH
- Command-A: select all
- Physical Control-C: send terminal interrupt (^C)
- Control-Shift-C / Control-Shift-V: explicit terminal-style clipboard shortcuts
- Right-click: Copy / Paste / Select All


## V2.8 terminal/input fixes

This release replaces the old "strip ANSI and append text" terminal renderer
with a cursor-aware VT-style renderer for common interactive shell behavior.

Fixes include:

- pasted commands no longer execute merely because the clipboard had a trailing newline
- carriage-return/redraw sequences no longer create repeated prompts
- shell Up/Down history redraw works
- terminal Tab completion redraw works
- backspace no longer renders control-character squares
- common cursor movement and erase sequences are interpreted instead of displayed
- local SFTP path bar supports Tab completion
- remote SFTP path bar supports Tab completion from the currently displayed directory

The terminal is still intentionally lighter than a complete xterm emulator, but
normal bash/zsh/readline interaction is now handled as a terminal screen rather
than as an append-only text log.


## V2.9 terminal Tab fix

Qt normally consumes Tab/Shift+Tab for widget focus traversal before a
QPlainTextEdit's keyPressEvent is called.

The terminal now intercepts these keys in QWidget.event():

- Tab is sent to the SSH PTY as `\t` for shell/readline completion
- Shift+Tab sends the terminal back-tab sequence
- focus stays in the terminal instead of jumping to the SFTP controls
