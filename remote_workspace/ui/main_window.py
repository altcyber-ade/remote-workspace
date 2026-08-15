from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from remote_workspace.core.models import ConnectionProfile
from remote_workspace.core.storage import ConnectionStore
from .connection_dialog import ConnectionDialog
from .session_tab import SessionTab


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Remote Workspace")
        self.resize(1380, 860)
        self.setMinimumSize(980, 640)

        self.store = ConnectionStore()
        self.profiles = self.store.load()

        self._build_ui()
        self._build_actions()
        self._refresh_connections()

    def _build_ui(self):
        root = QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)

        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        root_layout.addWidget(splitter)

        # Sidebar
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setMinimumWidth(285)
        sidebar.setMaximumWidth(390)

        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(16, 18, 16, 14)
        side_layout.setSpacing(10)

        brand_row = QHBoxLayout()
        brand_icon = QLabel("⌘")
        brand_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_icon.setFixedSize(42, 42)
        brand_icon.setStyleSheet(
            "font-size: 20pt; font-weight: 700; color: white;"
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "stop:0 #138cff, stop:1 #6747ff);"
            "border: 1px solid #398fff; border-radius: 10px;"
        )

        brand_text = QVBoxLayout()
        title = QLabel("Remote Workspace")
        title.setObjectName("AppTitle")
        subtitle = QLabel("SSH & SFTP Client")
        subtitle.setObjectName("AppSubtitle")
        brand_text.addWidget(title)
        brand_text.addWidget(subtitle)

        brand_row.addWidget(brand_icon)
        brand_row.addLayout(brand_text, 1)
        side_layout.addLayout(brand_row)
        side_layout.addSpacing(6)

        self.add_button = QPushButton("＋  New connection")
        self.add_button.setObjectName("Primary")
        self.add_button.setMinimumHeight(42)
        self.add_button.clicked.connect(self.add_connection)
        side_layout.addWidget(self.add_button)
        side_layout.addSpacing(4)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search connections")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self._filter_connections)
        side_layout.addWidget(self.search_edit)

        section_row = QHBoxLayout()
        section = QLabel("CONNECTIONS")
        section.setObjectName("SectionTitle")
        self.count_label = QLabel()
        self.count_label.setObjectName("Muted")
        section_row.addWidget(section)
        section_row.addStretch(1)
        section_row.addWidget(self.count_label)
        side_layout.addLayout(section_row)

        self.connection_list = QListWidget()
        self.connection_list.setObjectName("ConnectionList")
        self.connection_list.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.connection_list.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.connection_list.customContextMenuRequested.connect(
            self._show_connection_menu
        )
        self.connection_list.itemDoubleClicked.connect(
            lambda _: self.connect_selected()
        )
        side_layout.addWidget(self.connection_list, 1)

        side_buttons = QHBoxLayout()
        self.edit_button = QPushButton("✎  Edit")
        self.connect_button = QPushButton("⚡  Connect")
        self.connect_button.setObjectName("Primary")
        self.edit_button.clicked.connect(self.edit_selected)
        self.connect_button.clicked.connect(self.connect_selected)
        side_buttons.addWidget(self.edit_button)
        side_buttons.addWidget(self.connect_button, 1)
        side_layout.addLayout(side_buttons)

        # Workspace
        workspace = QWidget()
        work_layout = QVBoxLayout(workspace)
        work_layout.setContentsMargins(10, 10, 10, 10)
        work_layout.setSpacing(8)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self.close_session_tab)

        welcome = QWidget()
        welcome_layout = QVBoxLayout(welcome)
        welcome_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        welcome_title = QLabel("Remote Workspace")
        welcome_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_title.setStyleSheet(
            "font-size: 26pt; font-weight: 700; color: #f5f9ff;"
        )
        welcome_sub = QLabel(
            "Connect to a saved destination to open an SSH terminal\n"
            "and manage local / remote files side-by-side."
        )
        welcome_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_sub.setObjectName("Muted")
        welcome_sub.setStyleSheet("font-size: 11pt; line-height: 1.4;")

        welcome_hint = QLabel(
            "Tip: double-click a connection on the left to connect."
        )
        welcome_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_hint.setStyleSheet(
            "color: #59aaff; background: #0b1d2d;"
            "border: 1px solid #173b57; border-radius: 8px;"
            "padding: 9px 14px;"
        )

        welcome_layout.addStretch(1)
        welcome_layout.addWidget(welcome_title)
        welcome_layout.addSpacing(8)
        welcome_layout.addWidget(welcome_sub)
        welcome_layout.addSpacing(18)
        welcome_layout.addWidget(welcome_hint, 0, Qt.AlignmentFlag.AlignCenter)
        welcome_layout.addStretch(1)

        self.tabs.addTab(welcome, "Welcome")
        self.tabs.tabBar().setTabButton(
            0, self.tabs.tabBar().ButtonPosition.RightSide, None
        )
        work_layout.addWidget(self.tabs)

        splitter.addWidget(sidebar)
        splitter.addWidget(workspace)
        splitter.setSizes([315, 1065])

        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Ready")

        self.connection_list.itemSelectionChanged.connect(
            self._update_button_state
        )
        self._update_button_state()

    def _build_actions(self):
        new_action = QAction("New connection", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self.add_connection)

        connect_action = QAction("Connect", self)
        connect_action.setShortcut(QKeySequence("Ctrl+Return"))
        connect_action.triggered.connect(self.connect_selected)

        self.addAction(new_action)
        self.addAction(connect_action)

    def _profile_label(self, profile: ConnectionProfile) -> str:
        userhost = (
            f"{profile.username + '@' if profile.username else ''}{profile.host}"
        )
        return f"●  {profile.name}\n    {userhost}"

    def _refresh_connections(self, select_id: str | None = None):
        self.connection_list.clear()
        for profile in sorted(self.profiles, key=lambda p: p.name.casefold()):
            item = QListWidgetItem(self._profile_label(profile))
            item.setData(Qt.ItemDataRole.UserRole, profile.id)
            item.setToolTip(
                f"{profile.name}\n"
                f"{profile.username + '@' if profile.username else ''}"
                f"{profile.host}:{profile.port}"
            )
            self.connection_list.addItem(item)
            if select_id == profile.id:
                self.connection_list.setCurrentItem(item)

        self.count_label.setText(str(len(self.profiles)))
        self._filter_connections(self.search_edit.text())
        self._update_button_state()

    def _filter_connections(self, text: str):
        needle = text.strip().casefold()
        for row in range(self.connection_list.count()):
            item = self.connection_list.item(row)
            profile_id = item.data(Qt.ItemDataRole.UserRole)
            profile = next((p for p in self.profiles if p.id == profile_id), None)
            haystack = ""
            if profile:
                haystack = " ".join(
                    [profile.name, profile.host, profile.username]
                ).casefold()
            item.setHidden(bool(needle and needle not in haystack))

    def _selected_profile(self) -> ConnectionProfile | None:
        item = self.connection_list.currentItem()
        if not item or item.isHidden():
            return None
        profile_id = item.data(Qt.ItemDataRole.UserRole)
        return next((p for p in self.profiles if p.id == profile_id), None)

    def _update_button_state(self):
        selected = self._selected_profile() is not None
        self.edit_button.setEnabled(selected)
        self.connect_button.setEnabled(selected)

    def add_connection(self):
        dialog = ConnectionDialog(parent=self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return

        profile = dialog.result_profile()
        password = dialog.result_password()
        self.profiles.append(profile)
        self._persist_profile_password(profile, password)
        self.store.save(self.profiles)
        self._refresh_connections(profile.id)
        self.statusBar().showMessage(f"Saved {profile.name}", 3000)

    def edit_selected(self):
        profile = self._selected_profile()
        if not profile:
            return

        password = (
            self.store.get_password(profile.id) if profile.save_password else None
        )
        dialog = ConnectionDialog(
            profile=profile,
            existing_password=password,
            parent=self,
        )
        if dialog.exec() != dialog.DialogCode.Accepted:
            return

        updated = dialog.result_profile()
        new_password = dialog.result_password()
        self.profiles = [
            updated if p.id == profile.id else p for p in self.profiles
        ]
        self._persist_profile_password(updated, new_password)
        self.store.save(self.profiles)
        self._refresh_connections(updated.id)
        self.statusBar().showMessage(f"Updated {updated.name}", 3000)

    def _persist_profile_password(
        self, profile: ConnectionProfile, password: str
    ):
        if profile.save_password and password:
            try:
                self.store.set_password(profile.id, password)
            except Exception as exc:
                QMessageBox.warning(
                    self,
                    "Credential storage",
                    "The connection was saved, but the credential could not "
                    f"be stored in the OS keyring:\n\n{exc}",
                )
        elif not profile.save_password:
            self.store.delete_password(profile.id)

    def connect_selected(self):
        profile = self._selected_profile()
        if not profile:
            return

        password = (
            self.store.get_password(profile.id) if profile.save_password else None
        )
        if profile.auth_type == "password" and not password:
            password = self._ask_for_password(profile)
            if password is None:
                return

        tab = SessionTab(
            profile=profile,
            password=password,
            known_hosts_file=str(self.store.known_hosts_file),
        )
        tab.status_changed.connect(self.statusBar().showMessage)
        tab.paths_changed.connect(self._save_profile_paths)

        index = self.tabs.addTab(tab, profile.name)
        self.tabs.setCurrentIndex(index)

    def _save_profile_paths(self, profile_id: str, local_path: str, remote_path: str):
        changed = False
        for profile in self.profiles:
            if profile.id == profile_id:
                if profile.local_path != local_path:
                    profile.local_path = local_path
                    changed = True
                if profile.remote_path != remote_path:
                    profile.remote_path = remote_path
                    changed = True
                break
        if changed:
            self.store.save(self.profiles)

    def _ask_for_password(self, profile: ConnectionProfile) -> str | None:
        from PySide6.QtWidgets import QInputDialog, QLineEdit

        value, ok = QInputDialog.getText(
            self,
            "SSH credential",
            f"Password for {profile.username or 'user'}@{profile.host}:",
            QLineEdit.EchoMode.Password,
        )
        return value if ok else None

    def close_session_tab(self, index: int):
        if index == 0:
            return
        widget = self.tabs.widget(index)
        if isinstance(widget, SessionTab):
            widget.shutdown()
        self.tabs.removeTab(index)
        widget.deleteLater()

    def _show_connection_menu(self, position):
        item = self.connection_list.itemAt(position)
        if not item:
            return
        self.connection_list.setCurrentItem(item)

        menu = QMenu(self)
        connect_action = menu.addAction("Connect")
        edit_action = menu.addAction("Edit")
        menu.addSeparator()
        delete_action = menu.addAction("Delete")

        chosen = menu.exec(self.connection_list.viewport().mapToGlobal(position))
        if chosen == connect_action:
            self.connect_selected()
        elif chosen == edit_action:
            self.edit_selected()
        elif chosen == delete_action:
            self.delete_selected()

    def delete_selected(self):
        profile = self._selected_profile()
        if not profile:
            return

        answer = QMessageBox.question(
            self,
            "Delete connection",
            f"Delete '{profile.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        self.profiles = [p for p in self.profiles if p.id != profile.id]
        self.store.delete_password(profile.id)
        self.store.save(self.profiles)
        self._refresh_connections()
        self.statusBar().showMessage(f"Deleted {profile.name}", 3000)

    def closeEvent(self, event):
        for index in range(1, self.tabs.count()):
            widget = self.tabs.widget(index)
            if isinstance(widget, SessionTab):
                widget.shutdown()
        event.accept()
