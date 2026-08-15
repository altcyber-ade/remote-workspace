from __future__ import annotations

import re
import sys

from PySide6.QtCore import QEvent, Qt, Signal, QTimer
from PySide6.QtGui import QAction, QFontMetrics, QKeyEvent, QKeySequence, QTextCursor
from PySide6.QtWidgets import QApplication, QMenu, QPlainTextEdit


class TerminalWidget(QPlainTextEdit):
    """Small VT-style terminal surface for the interactive SSH PTY.

    This is intentionally not a full xterm implementation, but unlike the
    earlier renderer it understands the control sequences used by readline,
    bash/zsh history, tab completion, carriage-return redraws and backspace.
    """

    input_ready = Signal(str)
    terminal_resized = Signal(int, int)

    MAX_SCROLLBACK_LINES = 6000

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Terminal")
        self.setReadOnly(True)
        self.setUndoRedoEnabled(False)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        self._lines = [""]
        self._cursor_row = 0
        self._cursor_col = 0
        self._saved_cursor = (0, 0)
        self._pending_control = ""
        self._columns = 120
        self._rows = 36

        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.setInterval(120)
        self._resize_timer.timeout.connect(self._emit_terminal_size)

        self._render()

    # ------------------------------------------------------------------
    # Rendering / terminal output
    # ------------------------------------------------------------------
    def append_output(self, text: str):
        if not text:
            return

        data = self._pending_control + text
        self._pending_control = ""
        i = 0

        while i < len(data):
            ch = data[i]

            if ch == "\x1b":
                consumed = self._consume_escape(data, i)
                if consumed is None:
                    self._pending_control = data[i:]
                    break
                i = consumed
                continue

            if ch == "\r":
                self._cursor_col = 0
            elif ch == "\n":
                self._linefeed()
            elif ch == "\b":
                self._cursor_col = max(0, self._cursor_col - 1)
            elif ch == "\t":
                self._cursor_col = ((self._cursor_col // 8) + 1) * 8
                self._ensure_column(self._cursor_col)
            elif ch in ("\x00", "\x07", "\x0b", "\x0c"):
                # NUL/BEL/VT/FF do not need a visible glyph here.
                if ch in ("\x0b", "\x0c"):
                    self._linefeed()
            elif ord(ch) < 32 or ch == "\x7f":
                # Ignore other C0 control characters as display glyphs.
                pass
            else:
                self._draw_char(ch)

            i += 1

        self._trim_scrollback()
        self._render()

    def show_system_message(self, text: str):
        self.append_output(f"\r\n[{text}]\r\n")

    def _consume_escape(self, data: str, start: int):
        """Return index after sequence, or None if the chunk is incomplete."""
        if start + 1 >= len(data):
            return None

        kind = data[start + 1]

        # CSI: ESC [ ... final-byte
        if kind == "[":
            j = start + 2
            while j < len(data):
                if 0x40 <= ord(data[j]) <= 0x7E:
                    body = data[start + 2:j]
                    final = data[j]
                    self._handle_csi(body, final)
                    return j + 1
                j += 1
            return None

        # OSC: ESC ] ... BEL or ST (ESC \)
        if kind == "]":
            j = start + 2
            while j < len(data):
                if data[j] == "\x07":
                    return j + 1
                if data[j] == "\x1b":
                    if j + 1 >= len(data):
                        return None
                    if data[j + 1] == "\\":
                        return j + 2
                j += 1
            return None

        # Common two-character ESC sequences.
        if kind == "7":
            self._saved_cursor = (self._cursor_row, self._cursor_col)
        elif kind == "8":
            self._cursor_row, self._cursor_col = self._saved_cursor
            self._ensure_row(self._cursor_row)
        elif kind == "D":  # IND
            self._linefeed()
        elif kind == "E":  # NEL
            self._cursor_col = 0
            self._linefeed()
        elif kind == "M":  # RI
            self._cursor_row = max(self._viewport_origin(), self._cursor_row - 1)
        elif kind == "c":  # RIS
            self._reset_terminal()
        # Charset and keypad mode sequences are safe to ignore visually.

        return start + 2

    def _parse_params(self, body: str):
        # Strip private/intermediate markers used by xterm modes.
        cleaned = body
        while cleaned and cleaned[0] in "?><!":
            cleaned = cleaned[1:]

        if not cleaned:
            return []

        params = []
        for part in cleaned.split(";"):
            if part == "":
                params.append(None)
            else:
                try:
                    params.append(int(part))
                except ValueError:
                    params.append(None)
        return params

    @staticmethod
    def _param(params, index=0, default=1):
        if index >= len(params) or params[index] in (None, 0):
            return default
        return params[index]

    def _handle_csi(self, body: str, final: str):
        params = self._parse_params(body)

        if final == "A":  # CUU
            self._cursor_row = max(
                self._viewport_origin(),
                self._cursor_row - self._param(params),
            )
        elif final == "B":  # CUD
            self._cursor_row += self._param(params)
            self._ensure_row(self._cursor_row)
        elif final == "C":  # CUF
            self._cursor_col += self._param(params)
            self._ensure_column(self._cursor_col)
        elif final == "D":  # CUB
            self._cursor_col = max(0, self._cursor_col - self._param(params))
        elif final == "E":  # CNL
            self._cursor_row += self._param(params)
            self._cursor_col = 0
            self._ensure_row(self._cursor_row)
        elif final == "F":  # CPL
            self._cursor_row = max(
                self._viewport_origin(),
                self._cursor_row - self._param(params),
            )
            self._cursor_col = 0
        elif final in ("G", "`"):  # CHA/HPA
            self._cursor_col = max(0, self._param(params) - 1)
            self._ensure_column(self._cursor_col)
        elif final in ("H", "f"):  # CUP/HVP
            row = self._param(params, 0, 1)
            col = self._param(params, 1, 1)
            self._cursor_row = self._viewport_origin() + max(0, row - 1)
            self._cursor_col = max(0, col - 1)
            self._ensure_row(self._cursor_row)
            self._ensure_column(self._cursor_col)
        elif final == "d":  # VPA
            row = self._param(params, 0, 1)
            self._cursor_row = self._viewport_origin() + max(0, row - 1)
            self._ensure_row(self._cursor_row)
        elif final == "K":  # EL
            self._erase_in_line(params[0] if params else 0)
        elif final == "J":  # ED
            self._erase_in_display(params[0] if params else 0)
        elif final == "P":  # DCH
            self._delete_chars(self._param(params))
        elif final == "@":  # ICH
            self._insert_chars(self._param(params))
        elif final == "X":  # ECH
            self._erase_chars(self._param(params))
        elif final == "s":
            self._saved_cursor = (self._cursor_row, self._cursor_col)
        elif final == "u":
            self._cursor_row, self._cursor_col = self._saved_cursor
            self._ensure_row(self._cursor_row)
        elif final == "S":  # SU
            self._scroll_up(self._param(params))
        elif final == "T":  # SD
            self._scroll_down(self._param(params))
        # SGR (m), mode toggles (h/l), margins (r), device queries, etc.
        # affect styling/modes but do not need literal characters rendered.

    def _draw_char(self, ch: str):
        self._ensure_row(self._cursor_row)
        line = self._lines[self._cursor_row]

        if self._cursor_col > len(line):
            line += " " * (self._cursor_col - len(line))

        if self._cursor_col < len(line):
            line = (
                line[:self._cursor_col]
                + ch
                + line[self._cursor_col + 1:]
            )
        else:
            line += ch

        self._lines[self._cursor_row] = line
        self._cursor_col += 1

    def _linefeed(self):
        self._cursor_row += 1
        self._ensure_row(self._cursor_row)

    def _ensure_row(self, row: int):
        while len(self._lines) <= row:
            self._lines.append("")

    def _ensure_column(self, col: int):
        self._ensure_row(self._cursor_row)
        line = self._lines[self._cursor_row]
        if col > len(line):
            self._lines[self._cursor_row] = line + (" " * (col - len(line)))

    def _erase_in_line(self, mode: int):
        self._ensure_row(self._cursor_row)
        line = self._lines[self._cursor_row]

        if mode == 1:
            if self._cursor_col >= len(line):
                line = " " * len(line)
            else:
                line = (" " * (self._cursor_col + 1)) + line[self._cursor_col + 1:]
        elif mode == 2:
            line = ""
            self._cursor_col = 0
        else:
            line = line[:self._cursor_col]

        self._lines[self._cursor_row] = line

    def _erase_in_display(self, mode: int):
        origin = self._viewport_origin()
        bottom = max(origin, min(len(self._lines) - 1, origin + self._rows - 1))

        if mode == 3:
            self._lines = [""]
            self._cursor_row = 0
            self._cursor_col = 0
            return

        if mode == 2:
            for row in range(origin, bottom + 1):
                self._lines[row] = ""
            self._cursor_row = origin
            self._cursor_col = 0
            return

        if mode == 1:
            for row in range(origin, self._cursor_row):
                self._lines[row] = ""
            self._erase_in_line(1)
            return

        self._erase_in_line(0)
        for row in range(self._cursor_row + 1, bottom + 1):
            self._lines[row] = ""

    def _delete_chars(self, count: int):
        self._ensure_row(self._cursor_row)
        line = self._lines[self._cursor_row]
        if self._cursor_col < len(line):
            self._lines[self._cursor_row] = (
                line[:self._cursor_col]
                + line[self._cursor_col + count:]
            )

    def _insert_chars(self, count: int):
        self._ensure_row(self._cursor_row)
        line = self._lines[self._cursor_row]
        if self._cursor_col > len(line):
            line += " " * (self._cursor_col - len(line))
        self._lines[self._cursor_row] = (
            line[:self._cursor_col]
            + (" " * count)
            + line[self._cursor_col:]
        )

    def _erase_chars(self, count: int):
        self._ensure_row(self._cursor_row)
        line = self._lines[self._cursor_row]
        if self._cursor_col > len(line):
            return
        end = min(len(line), self._cursor_col + count)
        self._lines[self._cursor_row] = (
            line[:self._cursor_col]
            + (" " * (end - self._cursor_col))
            + line[end:]
        )

    def _scroll_up(self, count: int):
        origin = self._viewport_origin()
        for _ in range(count):
            insert_at = min(len(self._lines), origin + self._rows)
            self._lines.insert(insert_at, "")
            if origin < len(self._lines):
                self._lines.pop(origin)

    def _scroll_down(self, count: int):
        origin = self._viewport_origin()
        for _ in range(count):
            self._lines.insert(origin, "")
            bottom = origin + self._rows
            if bottom < len(self._lines):
                self._lines.pop(bottom)

    def _viewport_origin(self):
        # Absolute row corresponding to terminal row 1.
        return max(0, len(self._lines) - self._rows)

    def _reset_terminal(self):
        self._lines = [""]
        self._cursor_row = 0
        self._cursor_col = 0
        self._saved_cursor = (0, 0)

    def _trim_scrollback(self):
        excess = len(self._lines) - self.MAX_SCROLLBACK_LINES
        if excess <= 0:
            return
        del self._lines[:excess]
        self._cursor_row = max(0, self._cursor_row - excess)
        saved_row, saved_col = self._saved_cursor
        self._saved_cursor = (max(0, saved_row - excess), saved_col)

    def _render(self):
        # Avoid displaying raw control glyphs. The internal model only contains
        # printable characters and spaces.
        text = "\n".join(self._lines)
        self.setPlainText(text)

        row = max(0, min(self._cursor_row, len(self._lines) - 1))
        col = max(0, min(self._cursor_col, len(self._lines[row])))

        absolute = sum(len(line) + 1 for line in self._lines[:row]) + col
        cursor = self.textCursor()
        cursor.setPosition(min(absolute, len(text)))
        self.setTextCursor(cursor)
        self.ensureCursorVisible()

    # ------------------------------------------------------------------
    # Clipboard
    # ------------------------------------------------------------------
    def _copy_selection(self):
        cursor = self.textCursor()
        if cursor.hasSelection():
            text = cursor.selectedText().replace("\u2029", "\n")
            QApplication.clipboard().setText(text)

    def _paste_clipboard(self):
        text = QApplication.clipboard().text()
        if not text:
            return

        # A copied shell command often carries a final newline. Sending that
        # newline immediately executes the command, which is surprising in a
        # GUI paste operation. Keep internal newlines but remove trailing ones.
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = text.rstrip("\n")

        if not text:
            return

        text = text.replace("\n", "\r")
        self.input_ready.emit(text)

    def _select_all_terminal(self):
        self.selectAll()

    def _show_context_menu(self, pos):
        menu = QMenu(self)

        copy_action = QAction("Copy", self)
        copy_action.setShortcut(QKeySequence.StandardKey.Copy)
        copy_action.setEnabled(self.textCursor().hasSelection())
        copy_action.triggered.connect(self._copy_selection)

        paste_action = QAction("Paste", self)
        paste_action.setShortcut(QKeySequence.StandardKey.Paste)
        paste_action.setEnabled(bool(QApplication.clipboard().text()))
        paste_action.triggered.connect(self._paste_clipboard)

        select_all_action = QAction("Select All", self)
        select_all_action.setShortcut(QKeySequence.StandardKey.SelectAll)
        select_all_action.triggered.connect(self._select_all_terminal)

        menu.addAction(copy_action)
        menu.addAction(paste_action)
        menu.addSeparator()
        menu.addAction(select_all_action)
        menu.exec(self.viewport().mapToGlobal(pos))

    @staticmethod
    def _is_standard_shortcut(event: QKeyEvent, standard_key) -> bool:
        try:
            return event.matches(standard_key)
        except TypeError:
            return False

    # ------------------------------------------------------------------
    # Keyboard -> PTY
    # ------------------------------------------------------------------
    def event(self, event):
        """Intercept Tab before Qt uses it for focus traversal.

        QWidget handles Tab/Shift+Tab as focus-navigation keys before
        keyPressEvent(), so terminal completion must be captured here.
        """
        if event.type() == QEvent.Type.KeyPress:
            key = event.key()
            modifiers = event.modifiers()

            if key == Qt.Key.Key_Tab:
                if modifiers & Qt.KeyboardModifier.ShiftModifier:
                    # Back-tab / reverse completion sequence.
                    self.input_ready.emit("\x1b[Z")
                else:
                    self.input_ready.emit("\t")
                event.accept()
                return True

            if key == Qt.Key.Key_Backtab:
                self.input_ready.emit("\x1b[Z")
                event.accept()
                return True

        return super().event(event)

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        modifiers = event.modifiers()

        # Platform-aware native clipboard shortcuts. On macOS this means
        # Command-C / Command-V / Command-A.
        if self._is_standard_shortcut(event, QKeySequence.StandardKey.Copy):
            self._copy_selection()
            return
        if self._is_standard_shortcut(event, QKeySequence.StandardKey.Paste):
            self._paste_clipboard()
            return
        if self._is_standard_shortcut(event, QKeySequence.StandardKey.SelectAll):
            self._select_all_terminal()
            return

        if sys.platform == "darwin":
            physical_ctrl = bool(modifiers & Qt.KeyboardModifier.MetaModifier)
            command_held = bool(modifiers & Qt.KeyboardModifier.ControlModifier)

            if physical_ctrl and (modifiers & Qt.KeyboardModifier.ShiftModifier):
                if key == Qt.Key.Key_C:
                    self._copy_selection()
                    return
                if key == Qt.Key.Key_V:
                    self._paste_clipboard()
                    return

            if physical_ctrl and key == Qt.Key.Key_C:
                self.input_ready.emit("\x03")
                return

            control_for_terminal = physical_ctrl
        else:
            physical_ctrl = bool(modifiers & Qt.KeyboardModifier.ControlModifier)
            command_held = False

            if physical_ctrl and (modifiers & Qt.KeyboardModifier.ShiftModifier):
                if key == Qt.Key.Key_C:
                    self._copy_selection()
                    return
                if key == Qt.Key.Key_V:
                    self._paste_clipboard()
                    return

            if physical_ctrl and key == Qt.Key.Key_C:
                if self.textCursor().hasSelection():
                    self._copy_selection()
                else:
                    self.input_ready.emit("\x03")
                return

            control_for_terminal = physical_ctrl

        if control_for_terminal:
            key_map = {
                Qt.Key.Key_A: "\x01",
                Qt.Key.Key_B: "\x02",
                Qt.Key.Key_D: "\x04",
                Qt.Key.Key_E: "\x05",
                Qt.Key.Key_F: "\x06",
                Qt.Key.Key_G: "\x07",
                Qt.Key.Key_H: "\x08",
                Qt.Key.Key_I: "\x09",
                Qt.Key.Key_J: "\x0a",
                Qt.Key.Key_K: "\x0b",
                Qt.Key.Key_L: "\x0c",
                Qt.Key.Key_M: "\x0d",
                Qt.Key.Key_N: "\x0e",
                Qt.Key.Key_O: "\x0f",
                Qt.Key.Key_P: "\x10",
                Qt.Key.Key_Q: "\x11",
                Qt.Key.Key_R: "\x12",
                Qt.Key.Key_S: "\x13",
                Qt.Key.Key_T: "\x14",
                Qt.Key.Key_U: "\x15",
                Qt.Key.Key_V: "\x16",
                Qt.Key.Key_W: "\x17",
                Qt.Key.Key_X: "\x18",
                Qt.Key.Key_Y: "\x19",
                Qt.Key.Key_Z: "\x1a",
            }
            if key in key_map:
                self.input_ready.emit(key_map[key])
                return

        special = {
            Qt.Key.Key_Return: "\r",
            Qt.Key.Key_Enter: "\r",
            Qt.Key.Key_Backspace: "\x7f",
            Qt.Key.Key_Tab: "\t",
            Qt.Key.Key_Escape: "\x1b",
            Qt.Key.Key_Up: "\x1b[A",
            Qt.Key.Key_Down: "\x1b[B",
            Qt.Key.Key_Right: "\x1b[C",
            Qt.Key.Key_Left: "\x1b[D",
            Qt.Key.Key_Home: "\x1b[H",
            Qt.Key.Key_End: "\x1b[F",
            Qt.Key.Key_Delete: "\x1b[3~",
            Qt.Key.Key_Insert: "\x1b[2~",
            Qt.Key.Key_PageUp: "\x1b[5~",
            Qt.Key.Key_PageDown: "\x1b[6~",
            Qt.Key.Key_F1: "\x1bOP",
            Qt.Key.Key_F2: "\x1bOQ",
            Qt.Key.Key_F3: "\x1bOR",
            Qt.Key.Key_F4: "\x1bOS",
            Qt.Key.Key_F5: "\x1b[15~",
            Qt.Key.Key_F6: "\x1b[17~",
            Qt.Key.Key_F7: "\x1b[18~",
            Qt.Key.Key_F8: "\x1b[19~",
            Qt.Key.Key_F9: "\x1b[20~",
            Qt.Key.Key_F10: "\x1b[21~",
            Qt.Key.Key_F11: "\x1b[23~",
            Qt.Key.Key_F12: "\x1b[24~",
        }

        if key in special:
            self.input_ready.emit(special[key])
            return

        text = event.text()
        if text and not command_held and not (
            modifiers & Qt.KeyboardModifier.AltModifier
        ):
            self.input_ready.emit(text)
            return

        super().keyPressEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._resize_timer.start()

    def _emit_terminal_size(self):
        metrics = QFontMetrics(self.font())
        char_width = max(1, metrics.horizontalAdvance("M"))
        line_height = max(1, metrics.height())

        viewport = self.viewport().size()
        columns = max(20, viewport.width() // char_width)
        rows = max(5, viewport.height() // line_height)

        self._columns = columns
        self._rows = rows
        self.terminal_resized.emit(columns, rows)
