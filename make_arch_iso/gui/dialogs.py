"""GUI Dialog classes"""
from ..qt_compat import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QListWidget, QListWidgetItem, QComboBox, QMessageBox,
    QLineEdit, QColor, Qt
)
from ..constants import Colors
from .threads import PackageLoaderThread


class ExclusionsDialog(QDialog):
    """Dialog for managing directory exclusions"""

    def __init__(self, parent, exclude_items):
        super().__init__(parent)
        self.parent_window = parent
        self.setWindowTitle('Directory Exclusions')
        self.setMinimumSize(600, 500)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)

        # Info label
        info_label = QLabel(
            'Select directories/patterns to exclude from the ISO '
            '(reduces size):'
        )
        layout.addWidget(info_label)

        # Exclusions list
        self.exclude_list = QListWidget()
        self.exclude_list.setMinimumHeight(300)

        # Add items (exclude_items can be dict or list)
        if isinstance(exclude_items, dict):
            for excl_dir, checked in exclude_items.items():
                item = QListWidgetItem(excl_dir)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                state = (Qt.CheckState.Checked if checked
                         else Qt.CheckState.Unchecked)
                item.setCheckState(state)
                self.exclude_list.addItem(item)
        else:
            for excl_dir in exclude_items:
                item = QListWidgetItem(excl_dir)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked)
                self.exclude_list.addItem(item)

        layout.addWidget(self.exclude_list)

        # Buttons for managing exclusions
        btn_layout = QHBoxLayout()

        add_btn = QPushButton('Add Custom...')
        add_btn.clicked.connect(self.add_custom_exclusion)
        btn_layout.addWidget(add_btn)

        remove_btn = QPushButton('Remove Selected')
        remove_btn.clicked.connect(self.remove_exclusion)
        btn_layout.addWidget(remove_btn)

        select_all_btn = QPushButton('Select All')
        select_all_btn.clicked.connect(self.select_all_exclusions)
        btn_layout.addWidget(select_all_btn)

        deselect_all_btn = QPushButton('Deselect All')
        deselect_all_btn.clicked.connect(self.deselect_all_exclusions)
        btn_layout.addWidget(deselect_all_btn)

        layout.addLayout(btn_layout)

        # Dialog buttons
        dialog_btn_layout = QHBoxLayout()
        dialog_btn_layout.addStretch()

        ok_btn = QPushButton('OK')
        ok_btn.clicked.connect(self.accept)
        dialog_btn_layout.addWidget(ok_btn)

        cancel_btn = QPushButton('Cancel')
        cancel_btn.clicked.connect(self.reject)
        dialog_btn_layout.addWidget(cancel_btn)

        layout.addLayout(dialog_btn_layout)

    def add_custom_exclusion(self):
        """Add a custom directory exclusion pattern"""
        try:
            from PyQt6.QtWidgets import QInputDialog
        except ImportError:
            from PyQt5.QtWidgets import QInputDialog

        text, ok = QInputDialog.getText(
            self,
            'Add Custom Exclusion',
            'Enter directory pattern to exclude '
            '(e.g., ".cache", "Downloads/*"):'
        )
        if ok and text.strip():
            # Check if it already exists
            for i in range(self.exclude_list.count()):
                if self.exclude_list.item(i).text() == text.strip():
                    QMessageBox.warning(
                        self, 'Duplicate',
                        'This exclusion pattern already exists.'
                    )
                    return

            item = QListWidgetItem(text.strip())
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            self.exclude_list.addItem(item)

    def remove_exclusion(self):
        """Remove selected exclusion"""
        current_row = self.exclude_list.currentRow()
        if current_row >= 0:
            self.exclude_list.takeItem(current_row)

    def select_all_exclusions(self):
        """Check all exclusion items"""
        for i in range(self.exclude_list.count()):
            self.exclude_list.item(i).setCheckState(Qt.CheckState.Checked)

    def deselect_all_exclusions(self):
        """Uncheck all exclusion items"""
        for i in range(self.exclude_list.count()):
            self.exclude_list.item(i).setCheckState(Qt.CheckState.Unchecked)

    def get_selected_exclusions(self):
        """Get list of checked exclusion patterns"""
        exclusions = []
        for i in range(self.exclude_list.count()):
            item = self.exclude_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                exclusions.append(item.text())
        return exclusions

    def get_all_exclusions(self):
        """Get all exclusion patterns as dict {pattern: checked}"""
        exclusions = {}
        for i in range(self.exclude_list.count()):
            item = self.exclude_list.item(i)
            checked = (
                item.checkState() == Qt.CheckState.Checked
            )
            exclusions[item.text()] = checked
        return exclusions


class PackageSelectionDialog(QDialog):
    """Dialog for managing package exclusions"""

    def __init__(self, parent, excluded_packages=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setWindowTitle('Package Selection')
        self.setMinimumSize(700, 500)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)

        # Info label
        info_label = QLabel(
            'Select packages to exclude from the ISO. '
            'AUR packages are highlighted.'
        )
        layout.addWidget(info_label)

        # Loading status label
        self.loading_label = QLabel('Loading packages...')
        self.loading_label.setStyleSheet(
            f'QLabel {{ color: {Colors.INFO}; font-weight: 600; }}'
        )
        layout.addWidget(self.loading_label)

        # Search/filter box
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel('Search:'))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            'Filter packages by name...'
        )
        self.search_input.textChanged.connect(self.filter_packages)
        self.search_input.setEnabled(False)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)

        self.package_list = QListWidget()
        self.package_list.setMinimumHeight(400)
        layout.addWidget(self.package_list)

        self.all_packages = []
        self.aur_packages = set()
        self.excluded_packages = excluded_packages or []

        self.loader_thread = None
        self.start_loading_packages()

        btn_layout = QHBoxLayout()

        self.select_all_btn = QPushButton('Select All')
        self.select_all_btn.clicked.connect(self.select_all_packages)
        self.select_all_btn.setEnabled(False)
        btn_layout.addWidget(self.select_all_btn)

        self.deselect_all_btn = QPushButton('Deselect All')
        self.deselect_all_btn.clicked.connect(self.deselect_all_packages)
        self.deselect_all_btn.setEnabled(False)
        btn_layout.addWidget(self.deselect_all_btn)

        self.select_aur_btn = QPushButton('Select All AUR')
        self.select_aur_btn.clicked.connect(self.select_all_aur)
        self.select_aur_btn.setEnabled(False)
        btn_layout.addWidget(self.select_aur_btn)

        self.deselect_aur_btn = QPushButton('Deselect All AUR')
        self.deselect_aur_btn.clicked.connect(self.deselect_all_aur)
        self.deselect_aur_btn.setEnabled(False)
        btn_layout.addWidget(self.deselect_aur_btn)

        layout.addLayout(btn_layout)

        self.status_label = QLabel('')
        layout.addWidget(self.status_label)

        dialog_btn_layout = QHBoxLayout()
        dialog_btn_layout.addStretch()

        self.ok_btn = QPushButton('OK')
        self.ok_btn.clicked.connect(self.accept)
        self.ok_btn.setEnabled(False)
        dialog_btn_layout.addWidget(self.ok_btn)

        cancel_btn = QPushButton('Cancel')
        cancel_btn.clicked.connect(self.reject)
        dialog_btn_layout.addWidget(cancel_btn)

        layout.addLayout(dialog_btn_layout)

    def start_loading_packages(self):
        """Start loading packages in a background thread"""
        self.loader_thread = PackageLoaderThread()
        self.loader_thread.progress_signal.connect(self.on_loading_progress)
        self.loader_thread.finished_signal.connect(self.on_loading_finished)
        self.loader_thread.start()

    def on_loading_progress(self, message):
        """Update loading progress message"""
        self.loading_label.setText(message)

    def on_loading_finished(self, all_packages, aur_packages):
        """Handle package loading completion"""
        self.all_packages = all_packages
        self.aur_packages = aur_packages

        if not all_packages:
            self.loading_label.setText(
                "Error: Failed to load packages"
            )
            self.loading_label.setStyleSheet(
                f'QLabel {{ color: {Colors.ERROR}; font-weight: 600; }}'
            )
            return

        # Hide loading label
        self.loading_label.hide()

        # Enable UI elements
        self.search_input.setEnabled(True)
        self.select_all_btn.setEnabled(True)
        self.deselect_all_btn.setEnabled(True)
        self.select_aur_btn.setEnabled(True)
        self.deselect_aur_btn.setEnabled(True)
        self.ok_btn.setEnabled(True)

        # Populate list
        self.populate_list()

        # Set initial exclusions
        if self.excluded_packages:
            for pkg in self.excluded_packages:
                for i in range(self.package_list.count()):
                    item = self.package_list.item(i)
                    if item.text() == pkg:
                        item.setCheckState(Qt.CheckState.Checked)
                        break

        self.update_status()

    def closeEvent(self, event):
        """Clean up thread when dialog is closed"""
        if self.loader_thread and self.loader_thread.isRunning():
            self.loader_thread.terminate()
            self.loader_thread.wait()
        event.accept()

    def populate_list(self, filter_text=''):
        """Populate the package list with packages"""
        self.package_list.clear()
        filter_lower = filter_text.lower()

        for pkg_info in self.all_packages:
            pkg_name = pkg_info['name']
            if filter_text and filter_lower not in pkg_name.lower():
                continue

            item = QListWidgetItem(pkg_name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)

            # Highlight AUR packages
            if pkg_info['is_aur']:
                item.setForeground(QColor(Colors.INFO))
                item.setToolTip('AUR package')

            self.package_list.addItem(item)

    def filter_packages(self, text):
        """Filter packages based on search text"""
        self.populate_list(text)
        self.update_status()

    def select_all_packages(self):
        """Check all packages"""
        for i in range(self.package_list.count()):
            self.package_list.item(i).setCheckState(
                Qt.CheckState.Checked
            )
        self.update_status()

    def deselect_all_packages(self):
        """Uncheck all packages"""
        for i in range(self.package_list.count()):
            self.package_list.item(i).setCheckState(
                Qt.CheckState.Unchecked
            )
        self.update_status()

    def select_all_aur(self):
        """Check all AUR packages"""
        for i in range(self.package_list.count()):
            item = self.package_list.item(i)
            if item.text() in self.aur_packages:
                item.setCheckState(Qt.CheckState.Checked)
        self.update_status()

    def deselect_all_aur(self):
        """Uncheck all AUR packages"""
        for i in range(self.package_list.count()):
            item = self.package_list.item(i)
            if item.text() in self.aur_packages:
                item.setCheckState(Qt.CheckState.Unchecked)
        self.update_status()

    def update_status(self):
        """Update status label with package counts"""
        total = self.package_list.count()
        excluded = sum(
            1 for i in range(self.package_list.count())
            if self.package_list.item(i).checkState() ==
            Qt.CheckState.Checked
        )
        aur_excluded = sum(
            1 for i in range(self.package_list.count())
            if (self.package_list.item(i).checkState() ==
                Qt.CheckState.Checked and
                self.package_list.item(i).text() in self.aur_packages)
        )
        self.status_label.setText(
            f'Total packages: {total} | '
            f'Excluded: {excluded} ({aur_excluded} AUR)'
        )

    def get_excluded_packages(self):
        """Get list of checked (excluded) packages"""
        excluded = []
        for i in range(self.package_list.count()):
            item = self.package_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                excluded.append(item.text())
        return excluded
