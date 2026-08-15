APP_STYLE = """
/* Base */
QWidget {
    font-family: "SF Pro Display", "SF Pro Text", "Segoe UI", "Inter", sans-serif;
    font-size: 10pt;
    color: #e8eef7;
}

QMainWindow, QWidget#Root {
    background: #07101a;
}

QDialog {
    background: #0b1420;
    color: #e8eef7;
}

QFrame#Sidebar {
    background: #091421;
    border-right: 1px solid #1b2b3d;
}

/* Typography */
QLabel#AppTitle {
    font-size: 17pt;
    font-weight: 700;
    color: #ffffff;
}

QLabel#AppSubtitle {
    font-size: 10pt;
    color: #91a4ba;
}

QLabel#Muted {
    color: #91a4ba;
}

QLabel#SectionTitle {
    color: #aebdd0;
    font-weight: 700;
    font-size: 9pt;
    letter-spacing: 0.7px;
}

QLabel#Success {
    color: #39e75f;
    font-weight: 700;
}

QLabel#TerminalBadge {
    color: #46b7ff;
    background: #0a2235;
    border: 1px solid #17364c;
    border-radius: 5px;
    padding: 3px 8px;
    font-weight: 700;
}

QLabel#RemoteBadge {
    color: #c86bff;
    font-weight: 700;
}

QLabel#LocalBadge {
    color: #4eb7ff;
    font-weight: 700;
}

/* Inputs */
QLineEdit, QSpinBox, QComboBox {
    background: #0c1723;
    border: 1px solid #25384b;
    border-radius: 7px;
    padding: 8px 9px;
    min-height: 20px;
    color: #f4f8fc;
    selection-background-color: #1d7cff;
}

QLineEdit:hover, QSpinBox:hover, QComboBox:hover {
    border-color: #36516c;
}

QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
    border: 1px solid #2d8cff;
    background: #0e1b29;
}

QLineEdit::placeholder {
    color: #6f8196;
}

QComboBox QAbstractItemView {
    background: #0e1926;
    color: #e8eef7;
    border: 1px solid #2a3d50;
    selection-background-color: #1e5fa8;
}

QCheckBox {
    spacing: 8px;
    color: #dbe6f2;
}

QCheckBox::indicator {
    width: 17px;
    height: 17px;
    border-radius: 5px;
    border: 1px solid #3a5067;
    background: #0b1520;
}

QCheckBox::indicator:checked {
    background: #1687ff;
    border: 1px solid #3ca0ff;
}

/* Buttons */
QPushButton {
    background: #111f2e;
    border: 1px solid #2a3e53;
    border-radius: 8px;
    padding: 8px 13px;
    min-height: 20px;
    color: #eaf2fb;
}

QPushButton:hover {
    background: #172b3e;
    border-color: #3a5773;
}

QPushButton:pressed {
    background: #0b1722;
}

QPushButton:disabled {
    color: #627488;
    border-color: #1c2a38;
    background: #0c1620;
}

QPushButton#Primary {
    color: white;
    font-weight: 700;
    border: 1px solid #2a84ff;
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 #087cff,
        stop:0.58 #176dff,
        stop:1 #9b36e8
    );
}

QPushButton#Primary:hover {
    border-color: #63a9ff;
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 #1590ff,
        stop:0.58 #287cff,
        stop:1 #b14af4
    );
}

QPushButton#Danger {
    color: #ff7777;
    border: 1px solid #a43b44;
    background: #211218;
}

QPushButton#Danger:hover {
    background: #32161d;
    border-color: #ff5964;
}

QPushButton#IconButton {
    min-width: 30px;
    max-width: 30px;
    padding: 6px;
}

/* Sidebar list */
QListWidget#ConnectionList {
    background: transparent;
    border: none;
    outline: none;
    padding: 2px;
}

QListWidget#ConnectionList::item {
    color: #dfe9f5;
    border: 1px solid transparent;
    border-radius: 9px;
    padding: 11px 10px;
    margin: 3px 0;
}

QListWidget#ConnectionList::item:hover {
    background: #0e1d2c;
    border-color: #1d344a;
}

QListWidget#ConnectionList::item:selected {
    color: #ffffff;
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 #0c2947,
        stop:1 #122842
    );
    border: 1px solid #187dff;
}

/* Tabs */
QTabWidget::pane {
    border: 1px solid #1b2b3d;
    border-radius: 9px;
    background: #07111b;
    top: -1px;
}

QTabBar::tab {
    background: #0b1723;
    border: 1px solid #1d3042;
    color: #9fb0c4;
    padding: 9px 15px;
    margin-right: 3px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    min-width: 100px;
}

QTabBar::tab:selected {
    color: #ffffff;
    background: #102035;
    border-color: #2b69c9;
    border-bottom-color: #102035;
}

QTabBar::tab:hover:!selected {
    color: #dbe7f5;
    background: #102031;
}

/* Terminal */
QPlainTextEdit#Terminal {
    background: #02070c;
    color: #d7e5ef;
    border: 1px solid #132638;
    border-radius: 8px;
    padding: 10px;
    font-family: "SF Mono", "Cascadia Mono", "Consolas", "Menlo", monospace;
    font-size: 10.5pt;
    selection-background-color: #174a73;
}

/* Trees / lists */
QTreeView, QTreeWidget, QListWidget {
    background: #08131e;
    alternate-background-color: #0a1723;
    border: 1px solid #1b2f42;
    border-radius: 8px;
    outline: none;
}

QTreeView::item, QTreeWidget::item {
    padding: 6px 5px;
    color: #d9e5f2;
}

QTreeView::item:hover, QTreeWidget::item:hover {
    background: #0d2234;
}

QTreeView::item:selected, QTreeWidget::item:selected {
    background: #0e4fa3;
    color: #ffffff;
}

QHeaderView::section {
    background: #0c1a27;
    color: #b5c4d5;
    border: none;
    border-right: 1px solid #1b2d3d;
    border-bottom: 1px solid #1b2d3d;
    padding: 7px;
    font-weight: 600;
}

/* Transfer list */
QListWidget#TransferList {
    background: #07121c;
    border: 1px solid #1b2f42;
    border-radius: 8px;
}

QListWidget#TransferList::item {
    padding: 5px 9px;
    border-bottom: 1px solid #142637;
}

/* Progress */
QProgressBar {
    background: #111d29;
    border: 1px solid #293b4d;
    border-radius: 6px;
    text-align: center;
    color: #ffffff;
    min-height: 18px;
}

QProgressBar::chunk {
    border-radius: 5px;
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 #17d64a,
        stop:0.55 #2a8cff,
        stop:1 #9d3cff
    );
}

/* Splitters */
QSplitter::handle {
    background: #1a2b3b;
}

QSplitter::handle:hover {
    background: #2a78c7;
}

QSplitter::handle:vertical {
    height: 4px;
}

QSplitter::handle:horizontal {
    width: 4px;
}

/* Status / menus / dialogs */
QStatusBar {
    background: #08131e;
    color: #8fa5bc;
    border-top: 1px solid #1b2c3e;
}

QMenu {
    background: #0d1925;
    border: 1px solid #2a3d50;
    border-radius: 7px;
    padding: 4px;
}

QMenu::item {
    padding: 7px 24px 7px 10px;
    border-radius: 5px;
}

QMenu::item:selected {
    background: #153653;
}

QDialogButtonBox QPushButton {
    min-width: 72px;
}

QToolTip {
    background: #101d2b;
    color: #ffffff;
    border: 1px solid #37516b;
    padding: 5px;
}

/* Scrollbars */
QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background: #26394d;
    min-height: 28px;
    border-radius: 5px;
}
QScrollBar::handle:vertical:hover {
    background: #3c5f80;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    background: transparent;
    height: 10px;
    margin: 2px;
}
QScrollBar::handle:horizontal {
    background: #26394d;
    min-width: 28px;
    border-radius: 5px;
}
QScrollBar::handle:horizontal:hover {
    background: #3c5f80;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}
"""
