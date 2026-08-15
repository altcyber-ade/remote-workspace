from __future__ import annotations

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from remote_workspace.core.models import ConnectionProfile
from remote_workspace.core.ssh_session import SSHSession
from .file_browser import FileBrowser
from .terminal_widget import TerminalWidget


class SessionTab(QWidget):
    status_changed = Signal(str)
    paths_changed = Signal(str, str, str)

    def __init__(self, profile, password, known_hosts_file, parent=None):
        super().__init__(parent)
        self.profile = profile
        self._connected = False
        self._closing = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        header = QFrame()
        header.setStyleSheet(
            "QFrame { background: #091521; border: 1px solid #1d3043;"
            "border-radius: 8px; }"
        )
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 8, 10, 8)

        host_icon = QLabel("▣")
        host_icon.setStyleSheet("color: #27e05f; font-size: 14pt;")
        self.status_label = QLabel(
            f"{profile.username + '@' if profile.username else ''}"
            f"{profile.host}"
        )
        self.status_label.setStyleSheet("font-weight: 700; color: #f4f8fc;")

        self.state_dot = QLabel("●")
        self.state_dot.setStyleSheet("color: #688096;")
        self.state_label = QLabel("Connecting…")
        self.state_label.setObjectName("Muted")

        self.disconnect_button = QPushButton("⏏  Disconnect")
        self.disconnect_button.setObjectName("Danger")
        self.disconnect_button.clicked.connect(self.disconnect)

        header_layout.addWidget(host_icon)
        header_layout.addWidget(self.status_label)
        header_layout.addStretch(1)
        header_layout.addWidget(self.state_dot)
        header_layout.addWidget(self.state_label)
        header_layout.addSpacing(8)
        header_layout.addWidget(self.disconnect_button)

        terminal_panel = QFrame()
        terminal_panel.setStyleSheet(
            "QFrame { background: #07111b; border: 1px solid #1b3044;"
            "border-radius: 9px; }"
        )
        terminal_layout = QVBoxLayout(terminal_panel)
        terminal_layout.setContentsMargins(8, 8, 8, 8)
        terminal_layout.setSpacing(7)

        terminal_header = QHBoxLayout()
        terminal_badge = QLabel("TERMINAL")
        terminal_badge.setObjectName("TerminalBadge")
        terminal_header.addWidget(terminal_badge)
        terminal_header.addStretch(1)
        terminal_layout.addLayout(terminal_header)

        self.terminal = TerminalWidget()
        self.terminal.show_system_message(
            f"Connecting to {profile.host}:{profile.port}…"
        )
        terminal_layout.addWidget(self.terminal, 1)

        self.files = FileBrowser(
            local_path=profile.local_path,
            remote_path=profile.remote_path,
        )
        self.files.setEnabled(False)

        self.workspace_splitter = QSplitter(Qt.Orientation.Vertical)
        self.workspace_splitter.setChildrenCollapsible(False)
        self.workspace_splitter.addWidget(terminal_panel)
        self.workspace_splitter.addWidget(self.files)
        # Give SFTP substantially more room by default. The user can still
        # drag the splitter to rebalance terminal vs files at any time.
        self.workspace_splitter.setStretchFactor(0, 4)
        self.workspace_splitter.setStretchFactor(1, 6)
        self.workspace_splitter.setSizes([300, 520])

        layout.addWidget(header)
        layout.addWidget(self.workspace_splitter, 1)

        self.thread = QThread(self)
        self.session = SSHSession(profile, password, known_hosts_file)
        self.session.moveToThread(self.thread)

        self.thread.started.connect(self.session.connect)
        self.session.output.connect(self.terminal.append_output)
        self.session.connected.connect(self._on_connected)
        self.session.disconnected.connect(self._on_disconnected)
        self.session.error.connect(self._on_error)

        self.terminal.input_ready.connect(self.session.send)
        self.terminal.terminal_resized.connect(self.session.resize)

        self.files.request_remote_list.connect(self.session.list_remote)
        self.files.request_upload.connect(self.session.upload_path)
        self.files.request_download.connect(self.session.download_path)
        self.files.request_remote_rename.connect(self.session.remote_rename)
        self.files.request_remote_delete.connect(self.session.remote_delete)
        self.files.request_remote_mkdir.connect(self.session.remote_mkdir)
        self.files.paths_changed.connect(self._on_paths_changed)

        self.session.remote_listing.connect(self.files.set_remote_listing)
        self.session.sftp_error.connect(self._on_sftp_error)
        self.session.transfer_started.connect(self.files.transfer_started)
        self.session.transfer_progress.connect(self.files.set_transfer_progress)
        self.session.transfer_finished.connect(self._on_transfer_finished)
        self.session.transfer_failed.connect(self._on_transfer_failed)
        self.session.remote_mutation_finished.connect(self._on_remote_mutation)

        self.thread.start()

    def _on_connected(self):
        self._connected = True
        self.state_dot.setStyleSheet("color: #2ee65c;")
        self.state_label.setText("Connected")
        self.state_label.setObjectName("Success")
        self.files.setEnabled(True)
        self.terminal.show_system_message("Connected")
        self.terminal.setFocus()
        self.status_changed.emit(f"Connected • {self.profile.name}")
        self.files.request_remote_list.emit(self.profile.remote_path or ".")

    def _on_disconnected(self):
        self._connected = False
        self.state_dot.setStyleSheet("color: #66798d;")
        self.state_label.setText("Disconnected")
        self.disconnect_button.setEnabled(False)
        self.files.setEnabled(False)
        if not self._closing:
            self.terminal.show_system_message("Disconnected")
        self.status_changed.emit(f"Disconnected • {self.profile.name}")

    def _on_error(self, message):
        self.state_dot.setStyleSheet("color: #ff5f6a;")
        self.state_label.setText("Error")
        self.terminal.show_system_message(message)
        self.status_changed.emit(message)

    def _on_sftp_error(self, message):
        self.status_changed.emit(message)
        QMessageBox.warning(self, "SFTP", message)

    def _on_transfer_finished(self, message, refresh_path):
        self.files.transfer_done(message)
        self.status_changed.emit(message)
        self.files.request_remote_list.emit(self.files.remote_path)
        self.files.set_local_directory(self.files.local_directory)

    def _on_transfer_failed(self, message):
        self.files.transfer_failed(message)
        self.status_changed.emit(message)
        QMessageBox.warning(self, "Transfer", message)

    def _on_remote_mutation(self, message, refresh_path):
        self.status_changed.emit(message)
        self.files.request_remote_list.emit(refresh_path)

    def _on_paths_changed(self, local_path, remote_path):
        self.paths_changed.emit(self.profile.id, local_path, remote_path)

    def disconnect(self):
        self.session.disconnect()

    def shutdown(self):
        self._closing = True
        self.session.disconnect()
        if self.thread.isRunning():
            self.thread.quit()
            self.thread.wait(1500)
