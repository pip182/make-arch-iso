# Arch Linux ISO Builder - Agent Documentation

## Overview

The Arch Linux ISO Builder is a PyQt6/PyQt5 GUI application that creates a bootable, installable Arch Linux ISO from your current system installation. It packages your installed packages, user configurations, and system settings into a custom live ISO that can be used for system deployment or backup.

## Architecture

### Package Structure

```
make_arch_iso/
├── main.py                 # Entry point - initializes Qt app and shows GUI
├── make_arch_iso/          # Main package
│   ├── constants.py        # Constants (Colors, LayoutSpacing, Paths, Messages)
│   ├── qt_compat.py        # PyQt6/PyQt5 compatibility layer
│   ├── utils.py            # Utility functions (run_command, safe_remove, etc.)
│   ├── builder.py          # ISOBuilderThread - core ISO building logic
│   ├── usb_writer.py       # USBWriterThread - writes ISO to USB device
│   └── gui/                # GUI components
│       ├── main_window.py  # ISOBuilderGUI - main application window
│       ├── dialogs.py      # ExclusionsDialog, PackageSelectionDialog
│       └── threads.py      # PackageLoaderThread - loads packages in background
```

### Core Components

#### 1. **Constants Module** (`constants.py`)
- `Colors`: UI color scheme (dark theme)
- `LayoutSpacing`: Layout spacing and margin constants
- `Paths`: Default paths (work dir, output dir, config file)
- `Messages`: User-facing message strings

#### 2. **Qt Compatibility** (`qt_compat.py`)
- Detects and imports PyQt6 or PyQt5
- Exports common Qt classes and signals
- Sets `HAS_PYQT6` and `HAS_PYQT5` flags

#### 3. **Utilities** (`utils.py`)
- `run_command()`: Execute shell commands with consistent error handling
- `safe_remove()`: Safely remove files/directories
- `safe_makedirs()`: Create directories with proper permissions
- `get_qt_dialog_code()`: Get QDialog return codes for PyQt version

#### 4. **ISO Builder** (`builder.py`)
- `ISOBuilderThread`: QThread subclass that performs ISO building
  - `DEFAULT_EXCLUDE_DIRS`: Default patterns to exclude from ISO
  - `HOME_COPY_INCLUDES`: Patterns to include when copying user template
  - `HOME_COPY_EXCLUDES`: Patterns to exclude when copying user template
  - `run()`: Main build process
  - `_build_package_list()`: Generate package list from current system
  - `_write_customize_airootfs()`: Write customization script for live ISO
  - Builds ISO using `mkarchiso` command

#### 5. **USB Writer** (`usb_writer.py`)
- `USBWriterThread`: QThread subclass that writes ISO to USB
  - Uses `dd` command to write ISO to block device
  - Requires root/sudo privileges

#### 6. **GUI Components**

**Main Window** (`gui/main_window.py`):
- `ISOBuilderGUI`: Main application window (QMainWindow)
  - Configuration inputs (ISO name, directories, root password)
  - User template selection (dropdown of system users)
  - Directory and package exclusion dialogs
  - USB device selection
  - Build progress display and log output
  - Settings persistence (JSON config file)

**Dialogs** (`gui/dialogs.py`):
- `ExclusionsDialog`: Manage directory exclusion patterns
- `PackageSelectionDialog`: Select packages to exclude from ISO

**Threads** (`gui/threads.py`):
- `PackageLoaderThread`: Loads installed packages and identifies AUR packages

## Key Features

1. **ISO Creation**: Creates bootable Arch Linux ISO from current system
2. **Package Management**: Includes all installed packages (supports AUR packages)
3. **User Templates**: Copy user home directory as template for root user on ISO
4. **Directory Exclusions**: Exclude temp/cache files to reduce ISO size
5. **Package Exclusions**: Selectively exclude packages from ISO
6. **Video Driver Selection**: Select video drivers during installation (Intel, AMD, NVIDIA)
7. **USB Writing**: Automatically write ISO to USB device after build
8. **Settings Persistence**: Saves configuration to `~/.config/iso_builder_gui.json`

## Build Process

1. User configures settings in GUI
2. `ISOBuilderThread` runs in background:
   - Copies archiso releng profile
   - Builds package list from current system
   - Creates local repository for AUR packages
   - Copies user template home directory (if selected)
   - Writes customization scripts:
     - `customize_airootfs.sh`: Sets up live system
     - `install.sh`: Installation script with driver selection
   - Configures mkinitcpio for video drivers
   - Runs `mkarchiso` to build ISO
3. Optional: `USBWriterThread` writes ISO to USB device

## Dependencies

- Python 3.8+
- PyQt6 (recommended) or PyQt5
- Arch Linux system
- `archiso` package (for mkarchiso)
- Root/sudo privileges (required for building and USB writing)

## Configuration

Settings are saved to `~/.config/iso_builder_gui.json`:
- `work_dir`: Working directory for ISO build
- `output_dir`: Output directory for ISO file
- `write_to_usb`: Whether to write to USB after build
- `excluded_packages`: List of packages to exclude
- `root_password`: Root password for ISO
- `template_user`: User whose home directory to use as template

## Usage Patterns

### Running the Application
```bash
cd ~/Dev/make-arch-iso
sudo python3 main.py
```

### Key Classes for Extension

- **ISOBuilderThread**: Extend for custom build steps
- **ISOBuilderGUI**: Extend for custom UI components
- **ExclusionsDialog**: Extend for custom exclusion patterns

### Common Tasks

- Adding new exclusion patterns: Modify `ISOBuilderThread.DEFAULT_EXCLUDE_DIRS`
- Changing video drivers: Modify `gui_must` list in `builder.py`
- Customizing installer script: Modify `_write_customize_airootfs()` in `builder.py`

## Thread Safety

- All long-running operations use QThread subclasses
- Signals are used for communication between threads and GUI
- Qt's signal/slot mechanism ensures thread-safe UI updates

## Error Handling

- Commands use `check=False` with manual error checking
- Threads emit error signals to GUI
- User-friendly error messages displayed in status bar and message boxes

## Development Notes

- Uses PyQt6 by default, falls back to PyQt5
- Dark theme applied via QPalette
- All file operations use UTF-8 encoding
- Requires root privileges for ISO building and USB writing
- Uses `mkarchiso` from `archiso` package for ISO creation
