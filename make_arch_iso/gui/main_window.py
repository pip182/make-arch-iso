"""Main GUI Window"""
import os
import sys
import json
import subprocess
import getpass
import time
from pathlib import Path
from typing import Tuple

from ..qt_compat import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextEdit, QLineEdit, QFileDialog,
    QProgressBar, QGroupBox, QCheckBox, QMessageBox,
    QComboBox, QFont, QTextCursor, Qt, HAS_PYQT6
)
from ..constants import Colors, LayoutSpacing, Paths, Messages
from ..builder import ISOBuilderThread
from ..usb_writer import USBWriterThread
from ..utils import run_command, get_qt_dialog_code, create_app_icon
from .dialogs import ExclusionsDialog, PackageSelectionDialog


class ISOBuilderGUI(QMainWindow):
    """Main GUI window for ISO builder"""

    CONFIG_FILE = Paths.CONFIG_FILE

    def __init__(self):
        super().__init__()
        self.builder_thread = None
        self.usb_writer_thread = None
        self.last_iso_path = None
        self.load_settings()
        self.init_ui()

    # Helper methods for DRY
    def set_status(self, text: str, color: str = None) -> None:
        """Set status label text and optional color"""
        self.status_label.setText(text)
        if color:
            self.status_label.setStyleSheet(
                f'QLabel {{ color: {color}; font-weight: 600; }}'
            )

    def create_group_layout(
        self, spacing: int = None, margins: Tuple = None
    ) -> QVBoxLayout:
        """Create a standardized group box layout"""
        layout = QVBoxLayout()
        layout.setSpacing(spacing or LayoutSpacing.GROUP_SPACING)
        if margins:
            layout.setContentsMargins(*margins)
        else:
            layout.setContentsMargins(*LayoutSpacing.GROUP_MARGINS)
        return layout

    def create_field_layout(self, spacing: int = None) -> QHBoxLayout:
        """Create a standardized field layout"""
        layout = QHBoxLayout()
        layout.setSpacing(spacing or LayoutSpacing.FIELD_SPACING)
        return layout

    def create_input_field(
        self, default_value: str = "", min_height: int = None
    ) -> QLineEdit:
        """Create a standardized input field"""
        field = QLineEdit(default_value)
        field.setMinimumHeight(min_height or LayoutSpacing.MIN_INPUT_HEIGHT)
        return field

    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle('Arch Linux ISO Builder')
        self.setWindowIcon(create_app_icon())
        self.setMinimumSize(900, 850)
        # Set initial size larger than minimum for better initial
        # appearance
        self.resize(900, 950)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(LayoutSpacing.MAIN_SPACING * 2)
        main_layout.setContentsMargins(
            LayoutSpacing.MAIN_MARGINS,
            LayoutSpacing.MAIN_MARGINS,
            LayoutSpacing.MAIN_MARGINS,
            LayoutSpacing.MAIN_MARGINS
        )

        # Configuration Group
        config_group = QGroupBox('Configuration')
        config_layout = self.create_group_layout()

        # ISO Name
        iso_name_layout = self.create_field_layout()
        iso_name_layout.addWidget(QLabel('ISO Name:'))
        self.iso_name_input = self.create_input_field('custom-arch-live')
        iso_name_layout.addWidget(self.iso_name_input)
        config_layout.addLayout(iso_name_layout)

        # Include custom repo packages
        self.include_custom_repos = QCheckBox(
            'Include custom repository packages (AUR, etc.)'
        )
        self.include_custom_repos.setChecked(True)
        self.include_custom_repos.setContentsMargins(0, 3, 0, 3)
        config_layout.addWidget(self.include_custom_repos)

        # Work Directory
        work_dir_layout = self.create_field_layout()
        work_dir_layout.addWidget(QLabel('Work Directory:'))
        self.work_dir_input = self.create_input_field(
            self.settings.get('work_dir', Paths.DEFAULT_WORK_DIR)
        )
        self.work_dir_input.textChanged.connect(self.save_settings)
        work_dir_layout.addWidget(self.work_dir_input)
        work_dir_btn = QPushButton('Browse...')
        work_dir_btn.clicked.connect(self.browse_work_dir)
        work_dir_layout.addWidget(work_dir_btn)
        config_layout.addLayout(work_dir_layout)

        # Output Directory
        output_dir_layout = self.create_field_layout()
        output_dir_layout.addWidget(QLabel('Output Directory:'))
        self.output_dir_input = self.create_input_field(
            self.settings.get('output_dir', Paths.DEFAULT_OUTPUT_DIR)
        )
        self.output_dir_input.textChanged.connect(self.save_settings)
        output_dir_layout.addWidget(self.output_dir_input)
        output_dir_btn = QPushButton('Browse...')
        output_dir_btn.clicked.connect(self.browse_output_dir)
        output_dir_layout.addWidget(output_dir_btn)
        config_layout.addLayout(output_dir_layout)

        # Directory Exclusions and Package Selection Buttons
        buttons_layout = QHBoxLayout()
        exclude_btn = QPushButton(
            'Configure Directory Exclusions...'
        )
        exclude_btn.clicked.connect(self.show_exclusions_dialog)
        buttons_layout.addWidget(exclude_btn)

        package_btn = QPushButton('Select Packages to Exclude...')
        package_btn.clicked.connect(self.show_package_selection_dialog)
        buttons_layout.addWidget(package_btn)

        buttons_layout.addStretch()
        config_layout.addLayout(buttons_layout)

        config_group.setLayout(config_layout)
        main_layout.addWidget(config_group)

        # User Configuration - Separate Group
        user_group = QGroupBox('User Configuration')
        user_config_layout = self.create_group_layout(spacing=10)

        # Info label
        info_label = QLabel(
            'Select a system user whose home directory will be used as a '
            'template for the root user on the live ISO. The ISO will only '
            'have a root user account.'
        )
        info_label.setWordWrap(True)
        user_config_layout.addWidget(info_label)

        # User template selection
        user_template_layout = QHBoxLayout()
        user_template_layout.addWidget(QLabel('User Template:'))

        # User selection combo
        self.user_source_combo = QComboBox()
        self.user_source_combo.setMinimumWidth(250)
        self.populate_user_list()
        self.user_source_combo.currentIndexChanged.connect(self.save_settings)
        user_template_layout.addWidget(self.user_source_combo)

        # Refresh users button
        refresh_users_btn = QPushButton('Refresh')
        refresh_users_btn.clicked.connect(self.populate_user_list)
        self.refresh_users_btn = refresh_users_btn
        user_template_layout.addWidget(refresh_users_btn)

        user_template_layout.addStretch()
        user_config_layout.addLayout(user_template_layout)

        # Root password field
        root_password_layout = QHBoxLayout()
        root_password_layout.addWidget(QLabel('Root Password:'))
        self.root_password_input = QLineEdit()
        if HAS_PYQT6:
            self.root_password_input.setEchoMode(
                QLineEdit.EchoMode.Password
            )
        else:
            self.root_password_input.setEchoMode(QLineEdit.Password)
        self.root_password_input.setMinimumHeight(
            LayoutSpacing.MIN_INPUT_HEIGHT
        )
        self.root_password_input.setMinimumWidth(250)
        self.root_password_input.setText(
            self.settings.get('root_password', 'root')
        )
        self.root_password_input.textChanged.connect(self.save_settings)
        root_password_layout.addWidget(self.root_password_input)
        root_password_layout.addStretch()
        user_config_layout.addLayout(root_password_layout)

        user_group.setLayout(user_config_layout)
        main_layout.addWidget(user_group)

        # USB Write Group
        usb_group = QGroupBox('Write to USB Drive (Optional)')
        usb_layout = self.create_group_layout()

        self.write_to_usb = QCheckBox(
            'Write ISO to USB drive after build completes'
        )
        self.write_to_usb.setChecked(self.settings.get('write_to_usb', False))
        self.write_to_usb.stateChanged.connect(self.on_usb_write_toggled)
        self.write_to_usb.stateChanged.connect(self.save_settings)
        usb_layout.addWidget(self.write_to_usb)

        # USB Device Selection
        usb_device_layout = QHBoxLayout()
        usb_device_layout.setSpacing(10)
        usb_device_layout.addWidget(QLabel('USB Device:'))
        self.usb_device_combo = QComboBox()
        self.usb_device_combo.setMinimumWidth(300)
        self.usb_device_combo.setMinimumHeight(32)
        usb_device_layout.addWidget(self.usb_device_combo)

        refresh_usb_btn = QPushButton('Refresh')
        refresh_usb_btn.clicked.connect(self.refresh_usb_devices)
        usb_device_layout.addWidget(refresh_usb_btn)

        usb_layout.addLayout(usb_device_layout)

        usb_warning = QLabel(
            '⚠️  WARNING: This will erase all data on the selected USB '
            'device!'
        )
        usb_warning.setStyleSheet(
            f'QLabel {{ color: {Colors.WARNING}; font-weight: 600; }}'
        )
        usb_layout.addWidget(usb_warning)

        usb_group.setLayout(usb_layout)
        main_layout.addWidget(usb_group)

        # Store refresh button reference for later
        self.refresh_usb_btn = refresh_usb_btn

        # Load USB devices
        self.refresh_usb_devices()

        # Update widget states based on checkbox settings
        # This ensures widgets are enabled/disabled correctly on startup
        if self.write_to_usb.isChecked():
            self.on_usb_write_toggled(
                Qt.CheckState.Checked.value if HAS_PYQT6 else 2
            )
        else:
            self.usb_device_combo.setEnabled(False)
            self.refresh_usb_btn.setEnabled(False)

        # Initialize exclusions list (will be managed in dialog)
        # Store as dict: {pattern: checked}
        self.exclude_list_items = {}
        for excl_dir in ISOBuilderThread.DEFAULT_EXCLUDE_DIRS:
            self.exclude_list_items[excl_dir] = True

        # Initialize excluded packages list
        self.excluded_packages = self.settings.get('excluded_packages', [])

        # Progress Group
        progress_group = QGroupBox('Build Progress')
        progress_layout = self.create_group_layout(spacing=6)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setMinimumHeight(LayoutSpacing.MIN_PROGRESS_HEIGHT)
        progress_layout.addWidget(self.progress_bar)

        self.status_label = QLabel(Messages.READY)
        progress_layout.addWidget(self.status_label)

        progress_group.setLayout(progress_layout)
        main_layout.addWidget(progress_group)

        # Output Log
        log_group = QGroupBox('Build Log')
        log_layout = self.create_group_layout(spacing=0)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setFont(QFont('Monospace', 8))
        log_layout.addWidget(self.log_output)

        log_group.setLayout(log_layout)
        main_layout.addWidget(log_group)

        # Buttons
        button_layout = QHBoxLayout()

        self.clear_btn = QPushButton('Clear Log')
        self.clear_btn.clicked.connect(self.log_output.clear)
        button_layout.addWidget(self.clear_btn)

        self.stop_btn = QPushButton('Stop Build')
        self.stop_btn.setObjectName('stopButton')
        self.stop_btn.clicked.connect(self.stop_build)
        self.stop_btn.setEnabled(False)
        button_layout.addWidget(self.stop_btn)

        self.build_btn = QPushButton('Build ISO')
        self.build_btn.setObjectName('buildButton')
        self.build_btn.clicked.connect(self.start_build)
        # Button enabled state will be set based on root check below
        button_layout.addWidget(self.build_btn)

        main_layout.addLayout(button_layout)

        # Check if running as root
        is_root = os.geteuid() == 0
        if not is_root:
            warning = QLabel(
                '⚠️  Warning: This application must be run with sudo '
                'privileges'
            )
            warning.setStyleSheet(
                f'QLabel {{ color: {Colors.WARNING}; font-weight: 600; }}'
            )
            warning.setAlignment(Qt.AlignmentFlag.AlignCenter)
            main_layout.insertWidget(1, warning)
            self.build_btn.setEnabled(False)
            # Log the issue
            import getpass
            current_user = getpass.getuser()
            self.log_output.append(
                f"[INFO] Running as user: {current_user} "
                f"(UID: {os.geteuid()})\n"
            )
            self.log_output.append(
                "[INFO] Please run with: sudo ./make_arch_iso_gui.py\n"
            )
        else:
            # Explicitly enable button when running as root
            self.build_btn.setEnabled(True)
            self.log_output.append(
                "[INFO] Running as root - Build ISO button enabled\n"
            )

    def load_settings(self):
        """Load persisted settings from config file"""
        self.settings = {}
        if os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, 'r') as f:
                    self.settings = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.settings = {}

    def save_settings(self):
        """Save current settings to config file"""
        try:
            config_dir = os.path.dirname(self.CONFIG_FILE)
            os.makedirs(config_dir, exist_ok=True)

            self.settings['work_dir'] = self.work_dir_input.text()
            self.settings['output_dir'] = self.output_dir_input.text()
            self.settings['write_to_usb'] = self.write_to_usb.isChecked()
            self.settings['excluded_packages'] = getattr(
                self, 'excluded_packages', []
            )
            self.settings['root_password'] = self.root_password_input.text()
            if self.user_source_combo.currentData():
                self.settings['template_user'] = (
                    self.user_source_combo.currentData()
                )

            with open(self.CONFIG_FILE, 'w') as f:
                json.dump(self.settings, f, indent=2)
        except IOError:
            pass  # Fail silently if we can't save settings

    def browse_work_dir(self):
        """Browse for work directory"""
        dir_path = QFileDialog.getExistingDirectory(
            self, 'Select Work Directory'
        )
        if dir_path:
            self.work_dir_input.setText(dir_path)

    def browse_output_dir(self):
        """Browse for output directory"""
        dir_path = QFileDialog.getExistingDirectory(
            self, 'Select Output Directory'
        )
        if dir_path:
            self.output_dir_input.setText(dir_path)

    def get_usb_devices(self):
        """Detect available USB block devices"""
        devices = []
        try:
            # Use lsblk to find USB devices
            result = run_command(
                ['lsblk', '-d', '-n', '-o', 'NAME,TYPE,SIZE,MODEL'],
                check=True
            )

            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                parts = line.split()
                if len(parts) >= 2:
                    name = parts[0]
                    dev_type = parts[1] if len(parts) > 1 else ''
                    # Check if it's a disk (not a partition)
                    if dev_type == 'disk':
                        # Check if it's removable (USB)
                        device_path = f"/dev/{name}"
                        try:
                            # Check if device is removable
                            removable_path = f"/sys/block/{name}/removable"
                            if os.path.exists(removable_path):
                                with open(removable_path, 'r') as f:
                                    if f.read().strip() == '1':
                                        # Get size and model if available
                                        size = (
                                            parts[2]
                                            if len(parts) > 2
                                            else 'Unknown'
                                        )
                                        model = (' '.join(parts[3:])
                                                 if len(parts) > 3
                                                 else 'USB Device')
                                        devices.append({
                                            'path': device_path,
                                            'name': name,
                                            'size': size,
                                            'model': model
                                        })
                        except (IOError, OSError):
                            pass
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Fallback: check /dev/sd* and /dev/nvme* devices
            for device_path in Path('/dev').glob('sd[a-z]'):
                if device_path.is_block_device():
                    devices.append({
                        'path': str(device_path),
                        'name': device_path.name,
                        'size': 'Unknown',
                        'model': 'USB Device'
                    })
            for device_path in Path('/dev').glob('nvme[0-9]n[0-9]'):
                if device_path.is_block_device():
                    devices.append({
                        'path': str(device_path),
                        'name': device_path.name,
                        'size': 'Unknown',
                        'model': 'USB Device'
                    })

        return devices

    def refresh_usb_devices(self):
        """Refresh the list of USB devices"""
        self.usb_device_combo.clear()
        devices = self.get_usb_devices()

        if not devices:
            self.usb_device_combo.addItem('No USB devices found', None)
            return

        for device in devices:
            display_text = (
                f"{device['path']} - {device['model']} ({device['size']})"
            )
            self.usb_device_combo.addItem(display_text, device['path'])

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
                        uid = int(parts[2])
                        home_dir = parts[5]
                        # Only include regular users (UID >= 1000)
                        # with home dirs
                        if (uid >= 1000 and home_dir and
                                os.path.exists(home_dir) and
                                os.path.isdir(home_dir)):
                            users.append(username)

                users.sort()
                for user in users:
                    self.user_source_combo.addItem(user, user)

                # Restore previously selected user if exists
                saved_user = self.settings.get('template_user', '')
                if saved_user:
                    index = self.user_source_combo.findData(saved_user)
                    if index >= 0:
                        self.user_source_combo.setCurrentIndex(index)
            else:
                self.user_source_combo.addItem('No users found', None)
        except Exception as e:
            self.user_source_combo.addItem('Error loading users', None)
            self.log_output.append(
                f"[WARN] Failed to load users: {str(e)}\n"
            )

    def on_usb_write_toggled(self, state):
        """Enable/disable USB device selection based on checkbox"""
        enabled = (
            state == Qt.CheckState.Checked.value if HAS_PYQT6 else state == 2
        )
        self.usb_device_combo.setEnabled(enabled)
        if hasattr(self, 'refresh_usb_btn'):
            self.refresh_usb_btn.setEnabled(enabled)
        else:
            for widget in self.findChildren(QPushButton):
                if widget.text() == 'Refresh':
                    widget.setEnabled(enabled)
                    break
        if enabled and self.usb_device_combo.count() == 0:
            self.refresh_usb_devices()
        elif enabled:
            self.refresh_usb_devices()

    def show_exclusions_dialog(self):
        """Show the directory exclusions dialog"""
        dialog = ExclusionsDialog(self, self.exclude_list_items)
        accepted, _ = get_qt_dialog_code()
        result = dialog.exec()

        if result == accepted:
            self.exclude_list_items = dialog.get_all_exclusions()

    def show_package_selection_dialog(self):
        """Show the package selection dialog"""
        dialog = PackageSelectionDialog(self, self.excluded_packages)
        accepted, _ = get_qt_dialog_code()
        result = dialog.exec()

        if result == accepted:
            self.excluded_packages = dialog.get_excluded_packages()
            self.settings['excluded_packages'] = self.excluded_packages
            self.save_settings()

    def get_selected_exclusions(self):
        """Get list of checked exclusion patterns"""
        return [
            pattern for pattern, checked in self.exclude_list_items.items()
            if checked
        ]

    def check_root(self) -> bool:
        """Check if running as root, show error if not"""
        if os.geteuid() != 0:
            QMessageBox.critical(self, 'Error', Messages.ROOT_REQUIRED)
            return False
        return True

    def find_existing_iso(self, output_dir, iso_name):
        """Find existing ISO files matching the name pattern"""
        if not os.path.exists(output_dir):
            return None

        iso_files = list(Path(output_dir).glob(f'{iso_name}*.iso'))
        if not iso_files:
            return None

        # Sort by modification time, most recent first
        iso_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        most_recent = iso_files[0]

        # Check if ISO is recent (within last 24 hours)
        import time
        current_time = time.time()
        iso_age = current_time - most_recent.stat().st_mtime
        hours_old = iso_age / 3600

        # Consider ISO "recent" if less than 24 hours old
        if hours_old < 24:
            return most_recent
        return None

    def start_build(self):
        """Start the ISO build process"""
        if not self.check_root():
            return

        date_str = subprocess.check_output(
            ['date', '+%Y%m'], text=True
        ).strip()

        user_config = {
            'root_password': self.root_password_input.text(),
            'template_user': self.user_source_combo.currentData()
        }

        output_dir = self.output_dir_input.text()
        iso_name = self.iso_name_input.text()

        # Check for existing ISO
        existing_iso = self.find_existing_iso(output_dir, iso_name)
        if existing_iso:
            # Prompt user
            iso_size = existing_iso.stat().st_size / (1024**3)
            import time
            iso_age_hours = (
                (time.time() - existing_iso.stat().st_mtime) / 3600
            )
            reply = QMessageBox.question(
                self,
                'Existing ISO Found',
                f'Found an existing ISO file:\n\n'
                f'File: {existing_iso.name}\n'
                f'Size: {iso_size:.2f} GB\n'
                f'Age: {iso_age_hours:.1f} hours old\n\n'
                f'Do you want to use this existing ISO or rebuild?',
                QMessageBox.StandardButton.Yes |
                QMessageBox.StandardButton.No |
                QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Yes
            )

            if reply == QMessageBox.StandardButton.Cancel:
                return

            if reply == QMessageBox.StandardButton.Yes:
                # Use existing ISO - skip build and go straight to USB write
                # or completion
                self.log_output.clear()
                self.append_log(
                    f"[INFO] Using existing ISO: {existing_iso}\n"
                )
                self.append_log(
                    "[INFO] Skipping build process.\n"
                )
                self.progress_bar.setValue(100)
                self.build_btn.setEnabled(False)
                self.stop_btn.setEnabled(False)

                # Simulate build completion with existing ISO
                # This will handle USB write if enabled
                self.last_iso_path = str(existing_iso)
                self.build_finished(True, str(existing_iso))
                return

        # Proceed with normal build
        config = {
            'work_dir': self.work_dir_input.text(),
            'output_dir': output_dir,
            'iso_name': iso_name,
            'iso_label': f"ARCH_CUSTOM_{date_str}",
            'exclude_dirs': self.get_selected_exclusions(),
            'excluded_packages': self.excluded_packages,
            'include_custom_repos': self.include_custom_repos.isChecked(),
            'user_config': user_config
        }

        # Update UI
        self.build_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.set_status(Messages.BUILDING)
        self.log_output.clear()

        # Start builder thread
        self.builder_thread = ISOBuilderThread(config)
        self.builder_thread.output_signal.connect(self.append_log)
        self.builder_thread.progress_signal.connect(self.update_progress)
        self.builder_thread.finished_signal.connect(self.build_finished)
        self.builder_thread.start()

    def stop_build(self):
        """Stop the build process"""
        if self.builder_thread:
            self.builder_thread.stop()
            self.append_log("\n[INFO] Build stopped by user\n")
            self.build_finished(False, "Stopped by user")

    def append_log(self, text):
        """Append text to the log output"""
        self.log_output.moveCursor(QTextCursor.MoveOperation.End)
        self.log_output.insertPlainText(text)
        self.log_output.moveCursor(QTextCursor.MoveOperation.End)

    def update_progress(self, value):
        """Update the progress bar"""
        self.progress_bar.setValue(value)

    def build_finished(self, success, message):
        """Handle build completion"""
        self.build_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

        if success:
            self.last_iso_path = message
            self.set_status(Messages.BUILD_SUCCESS, Colors.SUCCESS)

            # Check if USB write is enabled - automatically proceed
            # without confirmation
            if self.write_to_usb.isChecked():
                # Get selected USB device
                device_path = self.usb_device_combo.currentData()

                if not device_path:
                    # Only show error if USB device is invalid
                    QMessageBox.warning(
                        self,
                        'Invalid USB Device',
                        'ISO created successfully, but the selected USB '
                        'device is invalid.\n\n'
                        f'ISO Location: {message}\n\n'
                        'Please select a valid USB device and try again.'
                    )
                    return

                # Automatically start USB write without confirmation
                self.start_usb_write(message, device_path)
            else:
                # Only show completion message if USB write is not enabled
                QMessageBox.information(
                    self,
                    'Build Complete',
                    f'ISO created successfully!\n\nLocation: {message}\n\n'
                    'You can now write it to a USB drive or test it in a VM.'
                )
        else:
            self.set_status(Messages.BUILD_FAILED, Colors.ERROR)
            QMessageBox.critical(
                self, 'Build Failed', f'Build failed: {message}'
            )

    def start_usb_write(self, iso_path, device_path):
        """Start writing ISO to USB device"""
        self.set_status(Messages.USB_WRITING, Colors.INFO)
        self.build_btn.setEnabled(False)
        self.progress_bar.setValue(0)

        # Start USB writer thread
        self.usb_writer_thread = USBWriterThread(iso_path, device_path)
        self.usb_writer_thread.output_signal.connect(self.append_log)
        self.usb_writer_thread.progress_signal.connect(self.update_progress)
        self.usb_writer_thread.finished_signal.connect(self.usb_write_finished)
        self.usb_writer_thread.start()

    def usb_write_finished(self, success, message):
        """Handle USB write completion"""
        self.build_btn.setEnabled(True)

        if success:
            self.set_status(Messages.USB_WRITE_SUCCESS, Colors.SUCCESS)
            # Show final completion message with ISO location and USB
            # write success
            iso_location = self.last_iso_path or "Unknown"
            QMessageBox.information(
                self,
                'Process Complete',
                f'ISO created and written to USB drive successfully!\n\n'
                f'ISO Location: {iso_location}\n'
                f'USB Device: {message}\n\n'
                'You can now boot from this USB drive.'
            )
        else:
            self.set_status(Messages.USB_WRITE_FAILED, Colors.ERROR)
            # Show error with ISO location in case user wants to manually
            # write it
            iso_location = self.last_iso_path or "Unknown"
            QMessageBox.critical(
                self,
                'USB Write Failed',
                f'Failed to write ISO to USB device.\n\n'
                f'Error: {message}\n\n'
                f'ISO Location: {iso_location}\n\n'
                'You can manually write the ISO to a USB drive using dd '
                'or another tool.'
            )
