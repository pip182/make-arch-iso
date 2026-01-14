# Arch Linux ISO Builder

GUI application for creating a live and installable Arch Linux ISO from your current installation.

## Features

- Create a bootable Arch Linux ISO from your current system
- Customize the ISO with your packages, configurations, and user data
- Select video drivers during installation (Intel, AMD, NVIDIA)
- Installer script with a root desktop shortcut for quick setup
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

## Common Live ISO Issues (and Fixes)

When building and running a live ISO, the most frequent issues typically
involve firmware, drivers, or service enablement. This project helps mitigate
them by installing essential packages and loading common modules during the
installer flow.

### Graphics
- **Black screen / no display manager**: ensure the correct Intel/AMD/NVIDIA
  driver selection during install. If you pick the wrong driver, reboot and
  reinstall or add the appropriate GPU packages in the installed system.
- **NVIDIA modesetting issues**: make sure `nvidia`/`nvidia-utils` packages are
  installed and that the `nvidia` module loads on boot.

### WiFi / Ethernet
- **No wireless networks detected**: confirm that firmware is installed and
  that `NetworkManager` is enabled. Some WiFi chipsets need `iwlwifi` or
  `ath10k` firmware which is included in `linux-firmware`.
- **Ethernet not detected**: verify that common Ethernet modules (like
  `r8169`, `e1000e`, or `igb`) load; these are handled by the installer.

### Audio
- **No audio devices / crackling**: ensure `pipewire` and `wireplumber` are
  installed and running. Also ensure `sof-firmware` is installed for newer
  Intel audio controllers.

### Boot Issues
- **UEFI-only install script**: the provided installer targets UEFI systems.
  For legacy BIOS, adjust the bootloader section in `install.sh` accordingly.

## License

See original file for license information.
