#!/usr/bin/env python3
"""
GUI for creating a live and installable Arch Linux ISO from current installation.

Requires: PyQt6 (pip install PyQt6 or pacman -S python-pyqt6)
"""
import sys
import os

from make_arch_iso.qt_compat import (
    QApplication, HAS_PYQT6, HAS_PYQT5
)
from make_arch_iso.constants import Colors
from make_arch_iso.gui.main_window import ISOBuilderGUI

def main():
    """Main entry point"""
    # Check for root privileges before initializing GUI
    if os.geteuid() != 0:
        print("Error: This application must be run with root privileges")
        print("\nPlease run with:")
        print("  sudo python3 main.py")
        print("\nOr:")
        print("  sudo ./main.py")
        sys.exit(1)

    if not HAS_PYQT6 and not HAS_PYQT5:
        print("Error: PyQt6 or PyQt5 is required")
        print("\nInstall with:")
        print("  sudo pacman -S python-pyqt6")
        print("  or")
        print("  sudo pacman -S python-pyqt5")
        print("  or")
        print("  pip install PyQt6")
        sys.exit(1)

    # Set Qt to use dark theme if available (Qt 6.5+)
    if HAS_PYQT6:
        from PyQt6.QtCore import Qt
        try:
            QApplication.setHighDpiScaleFactorRoundingPolicy(
                Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
            )
        except AttributeError:
            pass

    app = QApplication(sys.argv)

    # Enable dark mode via environment or Qt attribute
    if HAS_PYQT6:
        try:
            # Try to use native dark mode (Qt 6.5+)
            app.setStyleSheet("")
            os.environ['QT_QPA_PLATFORM'] = os.environ.get(
                'QT_QPA_PLATFORM', 'xcb'
            )
        except (AttributeError, KeyError, OSError):
            pass

    # Apply dark theme
    app.setStyle('Fusion')

    dark_palette = app.palette() if HAS_PYQT6 else app.palette()
    if HAS_PYQT6:
        from PyQt6.QtGui import QPalette, QColor
        from PyQt6.QtCore import Qt
    else:
        from PyQt5.QtGui import QPalette, QColor
        from PyQt5.QtCore import Qt

    # Modern dark theme colors - clean and professional
    dark_palette.setColor(QPalette.ColorRole.Window, QColor(30, 30, 30))
    dark_palette.setColor(
        QPalette.ColorRole.WindowText, QColor(240, 240, 240)
    )
    dark_palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
    dark_palette.setColor(
        QPalette.ColorRole.AlternateBase, QColor(35, 35, 35)
    )
    dark_palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(20, 20, 20))
    dark_palette.setColor(
        QPalette.ColorRole.ToolTipText, QColor(240, 240, 240)
    )
    dark_palette.setColor(QPalette.ColorRole.Text, QColor(240, 240, 240))
    dark_palette.setColor(QPalette.ColorRole.Button, QColor(45, 45, 45))
    dark_palette.setColor(
        QPalette.ColorRole.ButtonText, QColor(240, 240, 240)
    )
    dark_palette.setColor(
        QPalette.ColorRole.BrightText, QColor(255, 100, 100)
    )
    dark_palette.setColor(QPalette.ColorRole.Link, QColor(100, 150, 255))
    dark_palette.setColor(QPalette.ColorRole.Highlight, QColor(70, 130, 200))
    dark_palette.setColor(
        QPalette.ColorRole.HighlightedText, QColor(255, 255, 255)
    )

    # Disabled colors for better visual feedback
    dark_palette.setColor(
        QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText,
        QColor(120, 120, 120)
    )
    dark_palette.setColor(
        QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text,
        QColor(120, 120, 120)
    )
    dark_palette.setColor(
        QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText,
        QColor(120, 120, 120)
    )
    dark_palette.setColor(
        QPalette.ColorGroup.Disabled, QPalette.ColorRole.Base,
        QColor(30, 30, 30)
    )
    dark_palette.setColor(
        QPalette.ColorGroup.Disabled, QPalette.ColorRole.Button,
        QColor(30, 30, 30)
    )

    app.setPalette(dark_palette)

    app.setStyleSheet(f"""
        QMainWindow {{
            background-color: {Colors.BG_PRIMARY};
        }}
        QToolTip {{
            color: {Colors.TOOLTIP_TEXT};
            background-color: {Colors.TOOLTIP_BG};
            border: 1px solid {Colors.TOOLTIP_BORDER};
            border-radius: 4px;
            padding: 4px 8px;
        }}
        QGroupBox {{
            border: 1px solid {Colors.BORDER_DEFAULT};
            border-radius: 6px;
            margin-top: 16px;
            padding-top: 12px;
            font-weight: 600;
            color: {Colors.TEXT_SECONDARY};
            background-color: {Colors.BG_TERTIARY};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            background-color: {Colors.BG_TERTIARY};
            padding: 0 8px;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
            border-left: 1px solid {Colors.BORDER_DEFAULT};
            border-top: 1px solid {Colors.BORDER_DEFAULT};
            border-right: 1px solid {Colors.BORDER_DEFAULT};
            padding-top: 6px;
        }}
        QPushButton {{
            background-color: {Colors.BG_BUTTON};
            color: {Colors.TEXT_PRIMARY};
            border: 1px solid {Colors.BORDER_HOVER};
            border-radius: 4px;
            padding: 4px 12px;
            font-weight: 500;
            min-height: 16px;
        }}
        QPushButton:hover {{
            background-color: {Colors.BG_BUTTON_HOVER};
            border: 1px solid {Colors.BORDER_ACTIVE};
        }}
        QPushButton:pressed {{
            background-color: {Colors.BG_BUTTON_PRESSED};
            border: 1px solid {Colors.BORDER_DEFAULT};
        }}
        QPushButton:focus {{
            border: 1px solid {Colors.BORDER_FOCUS};
            outline: none;
        }}
        QPushButton#buildButton {{
            background-color: {Colors.BUTTON_SUCCESS};
            border: 1px solid {Colors.BUTTON_SUCCESS_BORDER};
            font-weight: 600;
            padding: 5px 12px;
        }}
        QPushButton#buildButton:hover {{
            background-color: {Colors.BUTTON_SUCCESS_HOVER};
            border: 1px solid {Colors.BUTTON_SUCCESS_BORDER_HOVER};
        }}
        QPushButton#buildButton:pressed {{
            background-color: {Colors.BUTTON_SUCCESS_PRESSED};
            border: 1px solid {Colors.BUTTON_SUCCESS_BORDER};
        }}
        QPushButton#buildButton:disabled {{
            background-color: {Colors.BG_DISABLED};
            color: {Colors.TEXT_DISABLED};
            border: 1px dashed {Colors.BORDER_DISABLED};
            opacity: 0.6;
        }}
        QPushButton#stopButton {{
            background-color: {Colors.BUTTON_ERROR};
            border: 1px solid {Colors.BUTTON_ERROR_BORDER};
            font-weight: 600;
            padding: 5px 12px;
        }}
        QPushButton#stopButton:hover {{
            background-color: {Colors.BUTTON_ERROR_HOVER};
            border: 1px solid {Colors.BUTTON_ERROR_BORDER_HOVER};
        }}
        QPushButton#stopButton:pressed {{
            background-color: {Colors.BUTTON_ERROR_PRESSED};
            border: 1px solid {Colors.BUTTON_ERROR_BORDER};
        }}
        QLineEdit {{
            background-color: {Colors.BG_SECONDARY};
            color: {Colors.TEXT_PRIMARY};
            border: 1px solid {Colors.BORDER_DEFAULT};
            border-radius: 4px;
            padding: 4px 8px;
            selection-background-color: {Colors.SELECTION_BG};
            selection-color: {Colors.SELECTION_TEXT};
        }}
        QLineEdit:focus {{
            border: 1px solid {Colors.BORDER_FOCUS};
            background-color: {Colors.BG_TERTIARY};
        }}
        QLineEdit:hover {{
            border: 1px solid {Colors.BORDER_HOVER};
        }}
        QComboBox {{
            background-color: {Colors.BG_SECONDARY};
            color: {Colors.TEXT_PRIMARY};
            border: 1px solid {Colors.BORDER_DEFAULT};
            border-radius: 4px;
            padding: 4px 8px;
            min-width: 120px;
        }}
        QComboBox:hover {{
            border: 1px solid {Colors.BORDER_HOVER};
            background-color: {Colors.BG_TERTIARY};
        }}
        QComboBox:focus {{
            border: 1px solid {Colors.BORDER_FOCUS};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 20px;
            background-color: transparent;
        }}
        QComboBox::down-arrow {{
            image: none;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 5px solid {Colors.COMBO_ARROW};
            width: 0;
            height: 0;
            margin-right: 6px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {Colors.BG_TERTIARY};
            color: {Colors.TEXT_PRIMARY};
            border: 1px solid {Colors.BORDER_DEFAULT};
            selection-background-color: {Colors.SELECTION_BG};
            selection-color: {Colors.SELECTION_TEXT};
        }}
        QListWidget {{
            background-color: {Colors.BG_SECONDARY};
            color: {Colors.TEXT_PRIMARY};
            border: 1px solid {Colors.BORDER_DEFAULT};
            border-radius: 4px;
            selection-background-color: {Colors.SELECTION_BG};
            selection-color: {Colors.SELECTION_TEXT};
        }}
        QListWidget::item {{
            padding: 3px;
            border-bottom: 1px solid {Colors.LIST_ITEM_BORDER};
        }}
        QListWidget::item:hover {{
            background-color: {Colors.LIST_ITEM_HOVER};
        }}
        QListWidget::item:selected {{
            background-color: {Colors.SELECTION_BG};
            color: {Colors.SELECTION_TEXT};
        }}
        QCheckBox {{
            color: {Colors.TEXT_PRIMARY};
            spacing: 8px;
        }}
        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            border: 2px solid {Colors.CHECKBOX_BORDER};
            border-radius: 3px;
            background-color: {Colors.BG_SECONDARY};
        }}
        QCheckBox::indicator:hover {{
            border: 2px solid {Colors.CHECKBOX_BORDER_HOVER};
            background-color: {Colors.BG_TERTIARY};
        }}
        QCheckBox::indicator:checked {{
            background-color: {Colors.CHECKBOX_CHECKED};
            border: 2px solid {Colors.CHECKBOX_CHECKED};
            image: none;
        }}
        QLabel {{
            color: {Colors.TEXT_PRIMARY};
        }}
        QProgressBar {{
            background-color: {Colors.PROGRESS_BG};
            border: 1px solid {Colors.BORDER_DEFAULT};
            border-radius: 4px;
            text-align: center;
            color: {Colors.TEXT_PRIMARY};
            height: 16px;
        }}
        QProgressBar::chunk {{
            background-color: {Colors.PROGRESS_CHUNK};
            border-radius: 3px;
        }}
        QTextEdit {{
            background-color: {Colors.BG_DARKEST};
            color: {Colors.TEXT_SECONDARY};
            border: 1px solid {Colors.BORDER_DEFAULT};
            border-radius: 4px;
            selection-background-color: {Colors.SELECTION_BG};
            selection-color: {Colors.SELECTION_TEXT};
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
        }}
        QScrollBar:vertical {{
            background-color: {Colors.SCROLLBAR_BG};
            width: 12px;
            border: none;
        }}
        QScrollBar::handle:vertical {{
            background-color: {Colors.SCROLLBAR_HANDLE};
            border-radius: 6px;
            border: 2px solid {Colors.SCROLLBAR_BG};
            min-height: 16px;
        }}
        QScrollBar::handle:vertical:hover {{
            background-color: {Colors.SCROLLBAR_HANDLE_HOVER};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        QScrollBar:horizontal {{
            background-color: {Colors.SCROLLBAR_BG};
            height: 12px;
            border: none;
        }}
        QScrollBar::handle:horizontal {{
            background-color: {Colors.SCROLLBAR_HANDLE};
            border-radius: 6px;
            border: 2px solid {Colors.SCROLLBAR_BG};
            min-width: 16px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background-color: {Colors.SCROLLBAR_HANDLE_HOVER};
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0px;
        }}
        QComboBox:disabled {{
            background-color: {Colors.BG_DISABLED};
            color: {Colors.TEXT_DISABLED};
            border: 1px dashed {Colors.BORDER_DISABLED};
            opacity: 0.6;
        }}
        QPushButton:disabled {{
            background-color: {Colors.BG_DISABLED};
            color: {Colors.TEXT_DISABLED};
            border: 1px dashed {Colors.BORDER_DISABLED};
            opacity: 0.6;
        }}
        QLineEdit:disabled {{
            background-color: {Colors.BG_DISABLED};
            color: {Colors.TEXT_DISABLED};
            border: 1px dashed {Colors.BORDER_DISABLED};
            opacity: 0.6;
        }}
        QListWidget:disabled {{
            background-color: {Colors.BG_DISABLED};
            color: {Colors.TEXT_DISABLED};
            border: 1px dashed {Colors.BORDER_DISABLED};
            opacity: 0.6;
        }}
        QCheckBox:disabled {{
            color: {Colors.TEXT_DISABLED};
            opacity: 0.6;
        }}
        QLabel:disabled {{
            color: {Colors.TEXT_DISABLED};
            opacity: 0.6;
        }}
    """)

    window = ISOBuilderGUI()
    window.show()
    sys.exit(app.exec() if HAS_PYQT6 else app.exec_())


if __name__ == '__main__':
    main()
