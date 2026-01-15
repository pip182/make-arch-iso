"""GUI Dialog classes"""
import os
import json
from datetime import datetime
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QListWidget, QListWidgetItem, QMessageBox,
    QLineEdit, QComboBox, QCheckBox, QInputDialog
)
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt
from ..constants import Colors, LayoutSpacing
from ..utils import run_command
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

    def __init__(self, parent, excluded_packages=None, settings=None):
        super().__init__(parent)
        self.parent_window = parent
        self.settings = settings or {}
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
        # Track which packages are already in the list
        self.loaded_package_names = set()

        # Create status label early (needed for update_status calls)
        self.status_label = QLabel('')
        layout.addWidget(self.status_label)

        # Show excluded packages immediately (before loading completes)
        if self.excluded_packages:
            excluded_count = len(self.excluded_packages)
            self.loading_label.setText(
                f"Loading packages... ({excluded_count} excluded shown)"
            )
            # Add excluded packages to list immediately
            for pkg_name in self.excluded_packages:
                item = QListWidgetItem(pkg_name)
                item.setFlags(
                    item.flags() | Qt.ItemFlag.ItemIsUserCheckable
                )
                item.setCheckState(Qt.CheckState.Checked)
                # Mark as potentially AUR (will be updated when loading)
                item.setForeground(QColor(Colors.INFO))
                item.setToolTip('Excluded package (AUR status loading...)')
                self.package_list.addItem(item)
                self.loaded_package_names.add(pkg_name)
            # Enable search and buttons early for excluded packages
            self.search_input.setEnabled(True)
            self.update_status()

        self.loader_thread = None

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

        self.update_btn = QPushButton('Update Package List')
        self.update_btn.clicked.connect(self.update_package_list)
        btn_layout.addWidget(self.update_btn)

        layout.addLayout(btn_layout)

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

        # Load from cache or start loading after all UI elements are created
        self._load_from_cache_or_start()

    def _load_from_cache_or_start(self):
        """Load package list from cache or start loading if old/missing"""
        # Check if we have cached package list
        cached_list = self.settings.get('package_list', [])
        cached_date_str = self.settings.get('package_list_date', '')

        if cached_list and cached_date_str:
            try:
                cached_date = datetime.fromisoformat(cached_date_str)
                days_old = (datetime.now() - cached_date).days

                if days_old < 3:
                    # Cache is fresh, use it
                    self._load_from_cache(cached_list)
                    return
                else:
                    # Cache is old, prompt user
                    reply = QMessageBox.question(
                        self,
                        'Package List Update',
                        f'The cached package list is {days_old} days old.\n\n'
                        'Would you like to update it now?\n\n'
                        'Yes to update, No to use cached list, Cancel to exit',
                        QMessageBox.StandardButton.Yes |
                        QMessageBox.StandardButton.No |
                        QMessageBox.StandardButton.Cancel,
                        QMessageBox.StandardButton.Yes
                    )

                    if reply == QMessageBox.StandardButton.Cancel:
                        self.reject()
                        return
                    elif reply == QMessageBox.StandardButton.No:
                        self._load_from_cache(cached_list)
                        return
                    # If Yes, fall through to start loading
            except (ValueError, TypeError):
                # Invalid date format, start fresh
                pass

        # No cache or user wants to update - start loading
        self.start_loading_packages()

    def _load_from_cache(self, cached_list):
        """Load package list from cache"""
        # Reconstruct all_packages and aur_packages from cache
        self.all_packages = cached_list
        self.aur_packages = {
            pkg['name'] for pkg in cached_list if pkg.get('is_aur', False)
        }

        # Hide loading label
        self.loading_label.hide()

        # Enable UI elements including update button
        self.search_input.setEnabled(True)
        self.select_all_btn.setEnabled(True)
        self.deselect_all_btn.setEnabled(True)
        self.select_aur_btn.setEnabled(True)
        self.deselect_aur_btn.setEnabled(True)
        self.update_btn.setEnabled(True)
        self.ok_btn.setEnabled(True)

        # Populate list
        self.populate_list()

        # Ensure excluded packages are checked
        excluded_set = set(self.excluded_packages)
        for i in range(self.package_list.count()):
            item = self.package_list.item(i)
            pkg_name = item.text()
            if pkg_name in excluded_set:
                item.setCheckState(Qt.CheckState.Checked)
                if pkg_name in self.aur_packages:
                    item.setForeground(QColor(Colors.INFO))
                    item.setToolTip('AUR package (excluded)')
                else:
                    item.setForeground(QColor())
                    item.setToolTip('Excluded package')

        self.update_status()

    def update_package_list(self):
        """Manually trigger package list update"""
        # Stop current loading if in progress
        if self.loader_thread and self.loader_thread.isRunning():
            self.loader_thread.terminate()
            self.loader_thread.wait()

        # Clear current list
        self.package_list.clear()
        self.all_packages = []
        self.aur_packages = set()
        self.loaded_package_names.clear()

        # Show loading label
        self.loading_label.show()
        self.loading_label.setText('Updating package list...')
        self.loading_label.setStyleSheet(
            f'QLabel {{ color: {Colors.INFO}; font-weight: 600; }}'
        )

        # Disable UI elements including update button
        self.search_input.setEnabled(False)
        self.select_all_btn.setEnabled(False)
        self.deselect_all_btn.setEnabled(False)
        self.select_aur_btn.setEnabled(False)
        self.deselect_aur_btn.setEnabled(False)
        self.update_btn.setEnabled(False)
        self.ok_btn.setEnabled(False)

        # Start loading
        self.start_loading_packages()

    def start_loading_packages(self):
        """Start loading packages in a background thread"""
        # Disable update button while loading
        self.update_btn.setEnabled(False)

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

        # Save to cache
        self._save_to_cache(all_packages)

        # Hide loading label
        self.loading_label.hide()

        # Enable UI elements including update button
        self.search_input.setEnabled(True)
        self.select_all_btn.setEnabled(True)
        self.deselect_all_btn.setEnabled(True)
        self.select_aur_btn.setEnabled(True)
        self.deselect_aur_btn.setEnabled(True)
        self.update_btn.setEnabled(True)
        self.ok_btn.setEnabled(True)

        # Populate list (excluded packages are already shown and checked)
        self.populate_list()

        # Ensure excluded packages are checked and update AUR status
        excluded_set = set(self.excluded_packages)
        for i in range(self.package_list.count()):
            item = self.package_list.item(i)
            pkg_name = item.text()
            if pkg_name in excluded_set:
                item.setCheckState(Qt.CheckState.Checked)
                # Update AUR highlighting now that we know
                if pkg_name in self.aur_packages:
                    item.setForeground(QColor(Colors.INFO))
                    item.setToolTip('AUR package (excluded)')
                else:
                    # Reset foreground to default (not AUR)
                    item.setForeground(QColor())  # Default color
                    item.setToolTip('Excluded package')

        self.update_status()

    def _save_to_cache(self, all_packages):
        """Save package list to cache in settings"""
        if self.parent_window:
            self.parent_window.settings['package_list'] = all_packages
            self.parent_window.settings['package_list_date'] = (
                datetime.now().isoformat()
            )
            self.parent_window.save_settings()

    def closeEvent(self, event):
        """Clean up thread when dialog is closed"""
        if self.loader_thread and self.loader_thread.isRunning():
            self.loader_thread.terminate()
            self.loader_thread.wait()
        event.accept()

    def populate_list(self, filter_text=''):
        """Populate the package list with packages"""
        filter_lower = filter_text.lower() if filter_text else ''

        # Clear and rebuild list
        self.package_list.clear()
        self.loaded_package_names.clear()

        # Re-add excluded packages first (they should always be visible)
        excluded_packages_set = set(self.excluded_packages)
        for pkg_name in sorted(excluded_packages_set):
            # Check if it matches filter
            if filter_text and filter_lower not in pkg_name.lower():
                continue

            item = QListWidgetItem(pkg_name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)

            # Check if it's AUR (if we have that info from loaded packages)
            if pkg_name in self.aur_packages:
                item.setForeground(QColor(Colors.INFO))
                item.setToolTip('AUR package (excluded)')
            elif self.all_packages:
                # If packages are loaded but this isn't in aur_packages,
                # it's not AUR
                item.setToolTip('Excluded package')
            else:
                # Packages not loaded yet - will update later
                item.setForeground(QColor(Colors.INFO))
                item.setToolTip('Excluded package (AUR status loading...)')

            self.package_list.addItem(item)
            self.loaded_package_names.add(pkg_name)

        # Add all other packages (only if packages have been loaded)
        if self.all_packages:
            for pkg_info in self.all_packages:
                pkg_name = pkg_info['name']

                # Skip if already added (excluded package)
                if pkg_name in excluded_packages_set:
                    continue

                # Check filter
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
                self.loaded_package_names.add(pkg_name)

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


class BuildOptimizationDialog(QDialog):
    """Dialog for build optimization settings"""

    def __init__(self, parent, settings):
        super().__init__(parent)
        self.parent_window = parent
        self.settings = settings
        self.setWindowTitle('Build Optimization Settings')
        self.setMinimumSize(550, 400)

        layout = QVBoxLayout(self)
        layout.setSpacing(LayoutSpacing.GROUP_SPACING)
        layout.setContentsMargins(*LayoutSpacing.GROUP_MARGINS)

        # Info label
        info_label = QLabel(
            'Compression settings significantly affect build time. Zstd is '
            'recommended for faster builds with good compression. XZ provides '
            'best compression but is slower.'
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Compression type
        compression_layout = QHBoxLayout()
        compression_layout.setSpacing(LayoutSpacing.FIELD_SPACING)
        compression_label = QLabel('Compression Type:')
        compression_label.setMinimumWidth(140)
        compression_layout.addWidget(compression_label)
        self.compression_combo = QComboBox()
        self.compression_combo.addItems([
            'zstd (Fast, Recommended)',
            'gzip (Fast)',
            'xz (Slow, Best Compression)'
        ])
        compression_type_setting = self.settings.get('compression_type', 'zstd')
        if compression_type_setting == 'zstd':
            self.compression_combo.setCurrentIndex(0)
        elif compression_type_setting == 'gzip':
            self.compression_combo.setCurrentIndex(1)
        elif compression_type_setting == 'xz':
            self.compression_combo.setCurrentIndex(2)
        self.compression_combo.currentIndexChanged.connect(self.save_settings)
        compression_layout.addWidget(self.compression_combo)
        compression_layout.addStretch()
        layout.addLayout(compression_layout)

        # Compression level (optional)
        level_info_label = QLabel(
            'Compression Level (optional): Lower = faster build, Higher = smaller ISO. '
            'Leave blank for defaults (zstd: 6, gzip: 6, xz: 6)'
        )
        level_info_label.setWordWrap(True)
        layout.addWidget(level_info_label)

        level_layout = QHBoxLayout()
        level_layout.setSpacing(LayoutSpacing.FIELD_SPACING)
        level_label = QLabel('Level (1-22 for zstd, 1-9 for gzip/xz):')
        level_label.setMinimumWidth(140)
        level_layout.addWidget(level_label)
        self.compression_level_input = QLineEdit()
        self.compression_level_input.setMinimumWidth(100)
        self.compression_level_input.setMinimumHeight(LayoutSpacing.MIN_INPUT_HEIGHT)
        compression_level = self.settings.get('compression_level', None)
        if compression_level:
            self.compression_level_input.setText(str(compression_level))
        self.compression_level_input.textChanged.connect(self.save_settings)
        level_layout.addWidget(self.compression_level_input)
        level_layout.addStretch()
        layout.addLayout(level_layout)

        layout.addStretch()

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

    def save_settings(self):
        """Save compression settings"""
        try:
            compression_index = self.compression_combo.currentIndex()
            if compression_index == 0:
                self.settings['compression_type'] = 'zstd'
            elif compression_index == 1:
                self.settings['compression_type'] = 'gzip'
            elif compression_index == 2:
                self.settings['compression_type'] = 'xz'

            compression_level_text = self.compression_level_input.text().strip()
            if compression_level_text:
                try:
                    level = int(compression_level_text)
                    self.settings['compression_level'] = level
                except ValueError:
                    self.settings['compression_level'] = None
            else:
                self.settings['compression_level'] = None

            # Save to config file
            config_dir = os.path.dirname(self.parent_window.CONFIG_FILE)
            os.makedirs(config_dir, exist_ok=True)
            with open(self.parent_window.CONFIG_FILE, 'w') as f:
                json.dump(self.settings, f, indent=2)
        except Exception:
            pass  # Fail silently if we can't save settings


class UserConfigurationDialog(QDialog):
    """Dialog for user account configuration"""

    def __init__(self, parent, settings):
        super().__init__(parent)
        self.parent_window = parent
        self.settings = settings
        self.setWindowTitle('User Configuration')
        self.setMinimumSize(550, 400)

        layout = QVBoxLayout(self)
        layout.setSpacing(LayoutSpacing.GROUP_SPACING * 2)  # Increased spacing
        layout.setContentsMargins(*LayoutSpacing.GROUP_MARGINS)

        # Info label
        info_label = QLabel(
            'Configure the user account for the live ISO and installed system. '
            'This user will be created with sudo access and will be used for '
            'automatic login. You can optionally use a system user\'s home '
            'directory as a template.'
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Add spacing after info label
        layout.addSpacing(LayoutSpacing.FIELD_SPACING)

        # Create two-column layout
        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(LayoutSpacing.FIELD_SPACING * 2)

        # Left column
        left_column = QVBoxLayout()
        left_column.setSpacing(LayoutSpacing.FIELD_SPACING * 2)  # Increased vertical spacing

        # Username field
        username_layout = QHBoxLayout()
        username_layout.setSpacing(LayoutSpacing.FIELD_SPACING)
        username_label = QLabel('Username:')
        username_label.setMinimumWidth(120)
        username_layout.addWidget(username_label)
        self.username_input = QLineEdit()
        self.username_input.setMinimumWidth(200)
        self.username_input.setMinimumHeight(LayoutSpacing.MIN_INPUT_HEIGHT)
        self.username_input.setText(
            self.settings.get('username', 'archuser')
        )
        self.username_input.textChanged.connect(self.save_settings)
        username_layout.addWidget(self.username_input)
        username_layout.addStretch()
        left_column.addLayout(username_layout)

        # User password field
        user_password_layout = QHBoxLayout()
        user_password_layout.setSpacing(LayoutSpacing.FIELD_SPACING)
        user_password_label = QLabel('User Password:')
        user_password_label.setMinimumWidth(120)
        user_password_layout.addWidget(user_password_label)
        self.user_password_input = QLineEdit()
        self.user_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.user_password_input.setMinimumHeight(
            LayoutSpacing.MIN_INPUT_HEIGHT
        )
        self.user_password_input.setMinimumWidth(200)
        self.user_password_input.setText(
            self.settings.get('user_password', 'arch')
        )
        self.user_password_input.textChanged.connect(self.save_settings)
        user_password_layout.addWidget(self.user_password_input)
        user_password_layout.addStretch()
        left_column.addLayout(user_password_layout)

        # Root password field
        root_password_layout = QHBoxLayout()
        root_password_layout.setSpacing(LayoutSpacing.FIELD_SPACING)
        root_password_label = QLabel('Root Password:')
        root_password_label.setMinimumWidth(120)
        root_password_layout.addWidget(root_password_label)
        self.root_password_input = QLineEdit()
        self.root_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.root_password_input.setMinimumHeight(
            LayoutSpacing.MIN_INPUT_HEIGHT
        )
        self.root_password_input.setMinimumWidth(200)
        self.root_password_input.setText(
            self.settings.get('root_password', 'root')
        )
        self.root_password_input.textChanged.connect(self.save_settings)
        root_password_layout.addWidget(self.root_password_input)
        root_password_layout.addStretch()
        left_column.addLayout(root_password_layout)

        left_column.addStretch()
        columns_layout.addLayout(left_column)

        # Right column
        right_column = QVBoxLayout()
        right_column.setSpacing(LayoutSpacing.FIELD_SPACING)

        # Sudo access checkbox
        self.sudo_checkbox = QCheckBox('Grant sudo access to user')
        self.sudo_checkbox.setChecked(
            self.settings.get('user_sudo', True)
        )
        self.sudo_checkbox.stateChanged.connect(self.save_settings)
        right_column.addWidget(self.sudo_checkbox)

        # User template selection
        user_template_layout = QVBoxLayout()
        user_template_layout.setSpacing(LayoutSpacing.FIELD_SPACING)
        user_template_layout.addWidget(QLabel('User Template (optional):'))

        template_input_layout = QHBoxLayout()
        template_input_layout.setSpacing(LayoutSpacing.FIELD_SPACING)
        # User selection combo
        self.user_source_combo = QComboBox()
        self.user_source_combo.setMinimumWidth(200)
        self.populate_user_list()
        self.user_source_combo.currentIndexChanged.connect(self.save_settings)
        template_input_layout.addWidget(self.user_source_combo)

        # Refresh users button
        refresh_users_btn = QPushButton('Refresh')
        refresh_users_btn.clicked.connect(self.populate_user_list)
        template_input_layout.addWidget(refresh_users_btn)
        template_input_layout.addStretch()

        user_template_layout.addLayout(template_input_layout)
        right_column.addLayout(user_template_layout)

        right_column.addStretch()
        columns_layout.addLayout(right_column)

        # Set equal stretch for both columns
        columns_layout.setStretchFactor(left_column, 1)
        columns_layout.setStretchFactor(right_column, 1)

        layout.addLayout(columns_layout)
        layout.addStretch()

        # Add spacing before dialog buttons
        layout.addSpacing(LayoutSpacing.FIELD_SPACING * 2)

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

    def populate_user_list(self):
        """Populate the user combo box with system users"""
        self.user_source_combo.clear()
        try:
            # Get all users with home directories
            result = run_command(['getent', 'passwd'], check=False)
            if result.returncode == 0:
                users = []
                for line in result.stdout.strip().split('\n'):
                    if not line:
                        continue
                    parts = line.split(':')
                    if len(parts) >= 6:
                        username = parts[0]
                        home_dir = parts[5]
                        # Only show users with valid home directories
                        if home_dir and os.path.exists(home_dir) and \
                                home_dir != '/' and \
                                username not in ['nobody', 'nfsnobody']:
                            users.append(username)

                # Sort and add to combo
                for username in sorted(users):
                    self.user_source_combo.addItem(username, username)

                # Set current selection if saved
                saved_user = self.settings.get('template_user')
                if saved_user:
                    index = self.user_source_combo.findData(saved_user)
                    if index >= 0:
                        self.user_source_combo.setCurrentIndex(index)
            else:
                self.user_source_combo.addItem('No users found', None)
        except Exception as e:
            self.user_source_combo.addItem('Error loading users', None)

    def save_settings(self):
        """Save user configuration settings"""
        try:
            self.settings['username'] = self.username_input.text()
            self.settings['user_password'] = self.user_password_input.text()
            self.settings['root_password'] = self.root_password_input.text()
            self.settings['user_sudo'] = self.sudo_checkbox.isChecked()
            if self.user_source_combo.currentData():
                self.settings['template_user'] = (
                    self.user_source_combo.currentData()
                )
            else:
                self.settings.pop('template_user', None)

            # Save to config file
            config_dir = os.path.dirname(self.parent_window.CONFIG_FILE)
            os.makedirs(config_dir, exist_ok=True)
            with open(self.parent_window.CONFIG_FILE, 'w') as f:
                json.dump(self.settings, f, indent=2)
        except Exception:
            pass  # Fail silently if we can't save settings
