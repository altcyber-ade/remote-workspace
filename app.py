import sys

from PySide6.QtWidgets import QApplication

from remote_workspace.ui.main_window import MainWindow
from remote_workspace.ui.styles import APP_STYLE


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Remote Workspace")
    app.setOrganizationName("RemoteWorkspace")
    app.setStyleSheet(APP_STYLE)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
