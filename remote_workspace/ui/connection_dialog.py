from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from remote_workspace.core.models import ConnectionProfile


class ConnectionDialog(QDialog):
    def __init__(
        self,
        profile: ConnectionProfile | None = None,
        existing_password: str | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Connection")
        self.setMinimumWidth(560)
        self.profile = profile or ConnectionProfile.new()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 18)
        outer.setSpacing(14)

        title = QLabel("Connection")
        title.setStyleSheet("font-size: 16pt; font-weight: 700; color: #ffffff;")
        outer.addWidget(title)

        intro = QLabel(
            "Save an SSH destination. Credentials can be stored securely "
            "in the macOS Keychain through the system keyring."
        )
        intro.setObjectName("Muted")
        intro.setWordWrap(True)
        outer.addWidget(intro)

        panel = QFrame()
        panel.setStyleSheet(
            "QFrame { background: #0a1622; border: 1px solid #1f3346;"
            "border-radius: 10px; }"
        )
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(16, 16, 16, 16)

        form = QFormLayout()
        form.setSpacing(11)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.name_edit = QLineEdit(self.profile.name)
        self.name_edit.setPlaceholderText("e.g. Production VPS")

        self.host_edit = QLineEdit(self.profile.host)
        self.host_edit.setPlaceholderText("example.com or 192.168.1.10")

        self.port_edit = QSpinBox()
        self.port_edit.setRange(1, 65535)
        self.port_edit.setValue(self.profile.port)

        self.user_edit = QLineEdit(self.profile.username)
        self.user_edit.setPlaceholderText("e.g. ubuntu")

        self.auth_combo = QComboBox()
        self.auth_combo.addItem("Password", "password")
        self.auth_combo.addItem("Private key", "key")
        idx = self.auth_combo.findData(self.profile.auth_type)
        self.auth_combo.setCurrentIndex(max(0, idx))

        self.password_edit = QLineEdit(existing_password or "")
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)

        self.save_password_check = QCheckBox(
            "Save password/passphrase in macOS Keychain"
        )
        self.save_password_check.setChecked(self.profile.save_password)

        key_row = QWidget()
        key_layout = QHBoxLayout(key_row)
        key_layout.setContentsMargins(0, 0, 0, 0)
        key_layout.setSpacing(7)

        self.key_edit = QLineEdit(self.profile.key_path)
        self.key_edit.setPlaceholderText("Path to private key")

        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse_key)
        key_layout.addWidget(self.key_edit, 1)
        key_layout.addWidget(browse)

        self.trust_check = QCheckBox(
            "Trust and remember previously unknown host keys"
        )
        self.trust_check.setChecked(self.profile.trust_new_hosts)
        self.trust_check.setToolTip(
            "Enable this only when you trust the first connection target."
        )

        form.addRow("Name", self.name_edit)
        form.addRow("Host / IP", self.host_edit)
        form.addRow("Port", self.port_edit)
        form.addRow("Username", self.user_edit)
        form.addRow("Authentication", self.auth_combo)
        form.addRow("Credential", self.password_edit)
        form.addRow("", self.save_password_check)
        form.addRow("Private key", key_row)
        form.addRow("", self.trust_check)

        panel_layout.addLayout(form)
        outer.addWidget(panel)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        save_btn = buttons.button(QDialogButtonBox.StandardButton.Save)
        save_btn.setObjectName("Primary")
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

        self.auth_combo.currentIndexChanged.connect(self._sync_auth_ui)
        self._sync_auth_ui()

    def _browse_key(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Select private key", "", "All files (*)"
        )
        if filename:
            self.key_edit.setText(filename)

    def _sync_auth_ui(self):
        using_key = self.auth_combo.currentData() == "key"
        self.key_edit.setEnabled(using_key)
        self.password_edit.setPlaceholderText(
            "Private-key passphrase (optional)"
            if using_key
            else "SSH password"
        )

    def _validate_and_accept(self):
        if not self.name_edit.text().strip():
            self.name_edit.setFocus()
            return
        if not self.host_edit.text().strip():
            self.host_edit.setFocus()
            return
        self.accept()

    def result_profile(self) -> ConnectionProfile:
        return ConnectionProfile(
            id=self.profile.id,
            name=self.name_edit.text().strip(),
            host=self.host_edit.text().strip(),
            port=self.port_edit.value(),
            username=self.user_edit.text().strip(),
            auth_type=self.auth_combo.currentData(),
            key_path=self.key_edit.text().strip(),
            save_password=self.save_password_check.isChecked(),
            trust_new_hosts=self.trust_check.isChecked(),
            local_path=self.profile.local_path,
            remote_path=self.profile.remote_path,
        )

    def result_password(self) -> str:
        return self.password_edit.text()
