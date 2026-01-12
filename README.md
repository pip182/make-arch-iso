# Arch Linux ISO Builder

GUI application for creating a live and installable Arch Linux ISO from your current installation.

## Features

- Create a bootable Arch Linux ISO from your current system
- Customize the ISO with your packages, configurations, and user data
- Select video drivers during installation (Intel, AMD, NVIDIA)
- Write ISO directly to USB drive
- Modern dark-themed GUI built with PyQt6/PyQt5

## Requirements

- Arch Linux (or Arch-based distribution)
- Python 3.8+
- PyQt6 or PyQt5
- Root/sudo access (required for building ISO and writing to USB)

## Installation

```bash
# Install PyQt6 (recommended)
sudo pacman -S python-pyqt6

# Or install PyQt5
sudo pacman -S python-pyqt5

# Or use pip
pip install PyQt6
```

## Usage

```bash
# Clone or navigate to the project directory
cd ~/Dev/make-arch-iso

# Run with sudo (required)
sudo python3 main.py
```

## Project Structure

```
make-arch-iso/
├── main.py                 # Entry point
├── make_arch_iso/          # Main package
│   ├── __init__.py
│   ├── constants.py        # Constants (Colors, LayoutSpacing, Paths, Messages)
│   ├── qt_compat.py        # PyQt6/PyQt5 compatibility layer
│   ├── utils.py            # Utility functions
│   ├── builder.py          # ISOBuilderThread class
│   ├── usb_writer.py       # USBWriterThread class
│   └── gui/                # GUI components
│       ├── __init__.py
│       ├── main_window.py  # Main GUI window
│       ├── dialogs.py      # Dialog windows
│       └── threads.py      # GUI thread classes
└── README.md
```

## Configuration

The application saves settings to `~/.config/iso_builder_gui.json`.

## License

See original file for license information.
