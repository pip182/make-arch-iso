"""PyQt compatibility layer"""
HAS_PYQT6 = False
HAS_PYQT5 = False

try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QPushButton, QLabel, QTextEdit, QLineEdit, QFileDialog,
        QProgressBar, QGroupBox, QCheckBox, QMessageBox,
        QListWidget, QListWidgetItem, QComboBox, QDialog
    )
    from PyQt6.QtCore import QThread, pyqtSignal, Qt
    from PyQt6.QtGui import QFont, QTextCursor, QColor, QIcon, QPixmap, QPainter
    HAS_PYQT6 = True
except ImportError:
    try:
        from PyQt5.QtWidgets import (
            QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
            QPushButton, QLabel, QTextEdit, QLineEdit, QFileDialog,
            QProgressBar, QGroupBox, QCheckBox, QMessageBox,
            QListWidget, QListWidgetItem, QComboBox, QDialog
        )
        from PyQt5.QtCore import QThread, pyqtSignal, Qt
        from PyQt5.QtGui import QFont, QTextCursor, QColor, QIcon, QPixmap, QPainter
        HAS_PYQT5 = True
    except ImportError:
        pass
