from __future__ import annotations

import os
import posixpath
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QDir, QModelIndex, Qt, Signal
from PySide6.QtGui import QAction, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QFileSystemModel,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTreeView,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)


def human_size(size: int) -> str:
    value = float(size)
    units = ["B", "KB", "MB", "GB", "TB"]
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{size} B"


class PathLineEdit(QLineEdit):
    """Address bar that reserves Tab for path completion."""

    tab_pressed = Signal()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Tab:
            self.tab_pressed.emit()
            return
        super().keyPressEvent(event)


class LocalTree(QTreeView):
    dropped_paths = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(True)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            paths = [u.toLocalFile() for u in event.mimeData().urls() if u.toLocalFile()]
            if paths:
                self.dropped_paths.emit(paths)
                event.acceptProposedAction()
                return
        super().dropEvent(event)


class RemoteTree(QTreeWidget):
    files_dropped = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            paths = [u.toLocalFile() for u in event.mimeData().urls() if u.toLocalFile()]
            if paths:
                self.files_dropped.emit(paths)
                event.acceptProposedAction()
                return
        super().dropEvent(event)


class FileBrowser(QWidget):
    request_remote_list = Signal(str)
    request_upload = Signal(str, str)
    request_download = Signal(str, str)
    request_remote_rename = Signal(str, str)
    request_remote_delete = Signal(str)
    request_remote_mkdir = Signal(str)
    paths_changed = Signal(str, str)

    def __init__(self, local_path="", remote_path=".", parent=None):
        super().__init__(parent)
        self.remote_path = remote_path or "."
        self._remote_entries = {}
        self.setMinimumHeight(360)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(7)

        title_row = QHBoxLayout()
        title = QLabel("Files")
        title.setObjectName("SectionTitle")
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh)
        title_row.addWidget(title)
        title_row.addStretch(1)
        title_row.addWidget(self.refresh_button)
        outer.addLayout(title_row)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        outer.addWidget(splitter, 1)

        # Local.
        local_box = QWidget()
        local_layout = QVBoxLayout(local_box)
        local_layout.setContentsMargins(0, 0, 4, 0)
        local_layout.setSpacing(6)

        local_header = QHBoxLayout()
        local_label = QLabel("LOCAL")
        local_label.setObjectName("LocalBadge")
        self.local_up_button = QPushButton("↑")
        self.local_up_button.setFixedWidth(36)
        self.local_up_button.clicked.connect(self.local_up)
        local_header.addWidget(local_label)
        local_header.addStretch(1)
        local_header.addWidget(self.local_up_button)
        local_layout.addLayout(local_header)

        start_local = local_path if local_path and os.path.isdir(local_path) else str(Path.home())
        self.local_path_edit = PathLineEdit(start_local)
        self.local_path_edit.setToolTip("Type a path and press Tab to complete")
        self.local_path_edit.returnPressed.connect(self.go_local_path)
        self.local_path_edit.tab_pressed.connect(self.complete_local_path)
        local_layout.addWidget(self.local_path_edit)

        self.local_model = QFileSystemModel(self)
        self.local_model.setFilter(
            QDir.Filter.AllEntries | QDir.Filter.NoDotAndDotDot | QDir.Filter.Hidden
        )
        self.local_model.setRootPath(start_local)

        self.local_tree = LocalTree()
        self.local_tree.setModel(self.local_model)
        self.local_tree.setRootIndex(self.local_model.index(start_local))
        self.local_tree.setSortingEnabled(True)
        self.local_tree.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        self.local_tree.setAlternatingRowColors(True)
        self.local_tree.setColumnWidth(0, 280)
        self.local_tree.doubleClicked.connect(self.local_double_clicked)
        self.local_tree.dropped_paths.connect(self._handle_local_drop)
        self.local_tree.setMinimumHeight(180)
        local_layout.addWidget(self.local_tree, 1)

        local_actions = QHBoxLayout()
        self.upload_button = QPushButton("↑  Upload →")
        self.upload_button.setObjectName("Primary")
        self.upload_button.clicked.connect(self.upload_selected)
        local_actions.addWidget(self.upload_button)
        local_layout.addLayout(local_actions)

        # Remote.
        remote_box = QWidget()
        remote_layout = QVBoxLayout(remote_box)
        remote_layout.setContentsMargins(4, 0, 0, 0)
        remote_layout.setSpacing(6)

        remote_header = QHBoxLayout()
        remote_label = QLabel("REMOTE")
        remote_label.setObjectName("RemoteBadge")
        self.remote_up_button = QPushButton("↑")
        self.remote_up_button.setFixedWidth(36)
        self.remote_up_button.clicked.connect(self.remote_up)
        remote_header.addWidget(remote_label)
        remote_header.addStretch(1)
        remote_header.addWidget(self.remote_up_button)
        remote_layout.addLayout(remote_header)

        self.remote_path_edit = PathLineEdit(self.remote_path)
        self.remote_path_edit.setToolTip("Type a path and press Tab to complete from the current remote listing")
        self.remote_path_edit.tab_pressed.connect(self.complete_remote_path)
        self.remote_path_edit.returnPressed.connect(
            lambda: self.request_remote_list.emit(self.remote_path_edit.text().strip() or ".")
        )
        remote_layout.addWidget(self.remote_path_edit)

        self.remote_tree = RemoteTree()
        self.remote_tree.setHeaderLabels(["Name", "Size", "Modified"])
        self.remote_tree.setAlternatingRowColors(True)
        self.remote_tree.setColumnWidth(0, 280)
        self.remote_tree.itemDoubleClicked.connect(self.remote_double_clicked)
        self.remote_tree.files_dropped.connect(self._handle_remote_drop)
        self.remote_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.ActionsContextMenu)

        rename_action = QAction("Rename", self.remote_tree)
        rename_action.triggered.connect(self.rename_remote_selected)
        delete_action = QAction("Delete", self.remote_tree)
        delete_action.triggered.connect(self.delete_remote_selected)
        mkdir_action = QAction("New folder", self.remote_tree)
        mkdir_action.triggered.connect(self.new_remote_folder)
        self.remote_tree.addAction(rename_action)
        self.remote_tree.addAction(delete_action)
        self.remote_tree.addAction(mkdir_action)

        self.remote_tree.setMinimumHeight(180)
        remote_layout.addWidget(self.remote_tree, 1)

        self.download_button = QPushButton("←  Download ↓")
        self.download_button.setObjectName("Primary")
        self.download_button.clicked.connect(self.download_selected)
        remote_layout.addWidget(self.download_button)

        splitter.addWidget(local_box)
        splitter.addWidget(remote_box)
        splitter.setSizes([500, 500])

        # Transfer status/queue.
        queue_header = QHBoxLayout()
        queue_title = QLabel("TRANSFERS")
        queue_title.setObjectName("SectionTitle")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        queue_header.addWidget(queue_title)
        queue_header.addStretch(1)
        queue_header.addWidget(self.progress, 1)
        outer.addLayout(queue_header)

        self.transfer_list = QListWidget()
        self.transfer_list.setObjectName("TransferList")
        self.transfer_list.setMinimumHeight(54)
        self.transfer_list.setMaximumHeight(82)
        outer.addWidget(self.transfer_list)

    @property
    def local_directory(self):
        path = self.local_model.filePath(self.local_tree.rootIndex())
        return path or str(Path.home())

    def set_local_directory(self, path):
        path = os.path.abspath(os.path.expanduser(path))
        if not os.path.isdir(path):
            return
        idx = self.local_model.index(path)
        if idx.isValid():
            self.local_tree.setRootIndex(idx)
            self.local_path_edit.setText(path)
            self.paths_changed.emit(path, self.remote_path)

    def go_local_path(self):
        path = os.path.expanduser(self.local_path_edit.text().strip())
        if os.path.isdir(path):
            self.set_local_directory(path)
        else:
            QMessageBox.warning(self, "Local path", "That local directory does not exist.")

    def complete_local_path(self):
        raw = self.local_path_edit.text()
        if not raw:
            raw = self.local_directory

        expanded = os.path.expanduser(raw)

        if os.path.isabs(expanded):
            candidate = expanded
        else:
            candidate = os.path.join(self.local_directory, expanded)

        if candidate.endswith(os.sep):
            directory = candidate
            prefix = ""
        else:
            directory = os.path.dirname(candidate) or self.local_directory
            prefix = os.path.basename(candidate)

        try:
            names = os.listdir(directory)
        except OSError:
            return

        matches = sorted(
            name for name in names
            if name.casefold().startswith(prefix.casefold())
        )
        if not matches:
            return

        completion = matches[0]
        if len(matches) > 1:
            common = os.path.commonprefix(matches)
            if len(common) <= len(prefix):
                return
            completion = common

        completed = os.path.join(directory, completion)
        if len(matches) == 1 and os.path.isdir(completed):
            completed += os.sep

        self.local_path_edit.setText(completed)
        self.local_path_edit.setCursorPosition(len(completed))

    def complete_remote_path(self):
        raw = self.remote_path_edit.text().strip()
        if not raw:
            raw = self.remote_path

        if raw.startswith("/"):
            candidate = raw
        else:
            candidate = posixpath.join(self.remote_path, raw)

        if candidate.endswith("/"):
            directory = posixpath.normpath(candidate)
            prefix = ""
        else:
            directory = posixpath.dirname(candidate) or self.remote_path
            prefix = posixpath.basename(candidate)

        # We can complete immediately from the directory currently displayed.
        if posixpath.normpath(directory) != posixpath.normpath(self.remote_path):
            return

        names = sorted(self._remote_entries.keys(), key=str.casefold)
        matches = [
            name for name in names
            if name.casefold().startswith(prefix.casefold())
        ]
        if not matches:
            return

        completion = matches[0]
        if len(matches) > 1:
            common = posixpath.commonprefix(matches)
            if len(common) <= len(prefix):
                return
            completion = common

        completed = posixpath.join(directory, completion)
        if (
            len(matches) == 1
            and self._remote_entries.get(completion, {}).get("is_dir")
        ):
            completed += "/"

        self.remote_path_edit.setText(completed)
        self.remote_path_edit.setCursorPosition(len(completed))

    def local_up(self):
        parent = os.path.dirname(self.local_directory.rstrip(os.sep))
        if parent:
            self.set_local_directory(parent)

    def local_double_clicked(self, index: QModelIndex):
        if self.local_model.isDir(index):
            self.set_local_directory(self.local_model.filePath(index))

    def refresh(self):
        self.request_remote_list.emit(self.remote_path or ".")
        current = self.local_directory
        self.local_model.setRootPath("")
        self.local_model.setRootPath(current)
        self.local_tree.setRootIndex(self.local_model.index(current))

    def set_remote_listing(self, path, entries):
        self.remote_path = path
        self.remote_path_edit.setText(path)
        self.remote_tree.clear()
        self._remote_entries = {}

        for entry in entries:
            name = entry["name"]
            self._remote_entries[name] = entry
            modified = (
                datetime.fromtimestamp(entry["mtime"]).strftime("%Y-%m-%d %H:%M")
                if entry.get("mtime")
                else ""
            )
            size = "" if entry["is_dir"] else human_size(entry.get("size", 0))
            item = QTreeWidgetItem([
                ("📁 " if entry["is_dir"] else "📄 ") + name,
                size,
                modified,
            ])
            item.setData(0, Qt.ItemDataRole.UserRole, name)
            item.setData(0, Qt.ItemDataRole.UserRole + 1, entry["is_dir"])
            self.remote_tree.addTopLevelItem(item)

        self.paths_changed.emit(self.local_directory, self.remote_path)

    def remote_double_clicked(self, item, column):
        name = item.data(0, Qt.ItemDataRole.UserRole)
        is_dir = bool(item.data(0, Qt.ItemDataRole.UserRole + 1))
        if is_dir:
            self.request_remote_list.emit(posixpath.join(self.remote_path, name))

    def remote_up(self):
        parent = posixpath.dirname((self.remote_path or "/").rstrip("/")) or "/"
        self.request_remote_list.emit(parent)

    def upload_selected(self):
        idx = self.local_tree.currentIndex()
        if not idx.isValid():
            QMessageBox.information(self, "Upload", "Select a local file or folder first.")
            return
        self.request_upload.emit(self.local_model.filePath(idx), self.remote_path)

    def download_selected(self):
        item = self.remote_tree.currentItem()
        if not item:
            QMessageBox.information(self, "Download", "Select a remote file or folder first.")
            return
        name = item.data(0, Qt.ItemDataRole.UserRole)
        remote_path = posixpath.join(self.remote_path, name)
        self.request_download.emit(remote_path, self.local_directory)

    def _handle_remote_drop(self, paths):
        for path in paths:
            self.request_upload.emit(path, self.remote_path)

    def _handle_local_drop(self, paths):
        # Finder/external drops onto local tree simply select the dropped folder
        # or reveal the first item's parent; they do not copy locally.
        if not paths:
            return
        first = paths[0]
        target = first if os.path.isdir(first) else os.path.dirname(first)
        if os.path.isdir(target):
            self.set_local_directory(target)

    def rename_remote_selected(self):
        item = self.remote_tree.currentItem()
        if not item:
            return
        old_name = item.data(0, Qt.ItemDataRole.UserRole)
        new_name, ok = QInputDialog.getText(
            self, "Rename remote item", "New name:", text=old_name
        )
        new_name = new_name.strip()
        if not ok or not new_name or new_name == old_name:
            return
        self.request_remote_rename.emit(
            posixpath.join(self.remote_path, old_name),
            posixpath.join(self.remote_path, new_name),
        )

    def delete_remote_selected(self):
        item = self.remote_tree.currentItem()
        if not item:
            return
        name = item.data(0, Qt.ItemDataRole.UserRole)
        answer = QMessageBox.question(
            self,
            "Delete remote item",
            f"Delete '{name}' recursively if needed?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.request_remote_delete.emit(posixpath.join(self.remote_path, name))

    def new_remote_folder(self):
        name, ok = QInputDialog.getText(self, "New remote folder", "Folder name:")
        name = name.strip()
        if ok and name:
            self.request_remote_mkdir.emit(posixpath.join(self.remote_path, name))

    def transfer_started(self, label):
        item = QListWidgetItem(f"⏳ {label}")
        item.setData(Qt.ItemDataRole.UserRole, label)
        self.transfer_list.addItem(item)
        self.transfer_list.scrollToBottom()
        self.progress.setValue(0)

    def set_transfer_progress(self, label, transferred, total):
        pct = int((transferred / total) * 100) if total else 0
        self.progress.setValue(max(0, min(100, pct)))
        for i in range(self.transfer_list.count() - 1, -1, -1):
            item = self.transfer_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == label:
                item.setText(f"⏳ {label} — {pct}%")
                break

    def transfer_done(self, message):
        self.progress.setValue(100)
        self.transfer_list.addItem(QListWidgetItem(f"✓ {message}"))
        self.transfer_list.scrollToBottom()

    def transfer_failed(self, message):
        self.transfer_list.addItem(QListWidgetItem(f"✕ {message}"))
        self.transfer_list.scrollToBottom()
