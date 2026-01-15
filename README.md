# Arch Linux ISO Builder

GUI application for creating a live and installable Arch Linux ISO from your current installation. Perfect for creating custom Arch-based distributions, backup ISOs, or portable systems.

## Features

- **Complete ISO Creation**: Build a bootable Arch Linux ISO from your current system
- **Package Management**: Include all installed packages with support for AUR packages via local repository
- **User Account Configuration**: Configure a non-root user account with optional sudo access
- **CachyOS Support**: Automatic detection and support for CachyOS kernels
- **Modern Nvidia Drivers**: Automatic detection and configuration of modern Nvidia drivers (proprietary or open-source)
- **Wayland Support**: Full Wayland configuration for modern desktop environments
- **Driver Support**: Comprehensive video, audio, and network/wifi driver support in live session
- **User Templates**: Copy system user home directories as templates for the configured user
- **Directory Exclusions**: Exclude temp/cache files to reduce ISO size
- **Package Exclusions**: Selectively exclude packages from the ISO
- **USB Writing**: Automatically write ISO to USB drive after build
- **Modern GUI**: Dark-themed interface built with PyQt6

## Requirements

- Arch Linux (or Arch-based distribution like CachyOS)
- Python 3.8+
- PyQt6
- Root/sudo access (required for building ISO and writing to USB)
- `archiso` package (automatically installed if missing)

## Installation

```bash
# Install PyQt6
sudo pacman -S python-pyqt6

# Or use pip (not recommended, may conflict with system packages)
pip install PyQt6
```

## Usage

```bash
# Navigate to the project directory
cd ~/Dev/make-arch-iso

# Run with sudo (required for ISO building and USB writing)
sudo python3 main.py
```

### First Run

1. **Configure ISO Settings**:
   - Set ISO name (default: `custom-arch-live`)
   - Choose work and output directories
   - Configure user account (username, password, sudo access)
   - Set root password (still needed for system operations)

2. **Optional: User Template**:
   - Select a system user whose home directory will be copied as a template
   - Useful for preserving your configuration, dotfiles, and applications

3. **Optional: Exclusions**:
   - Exclude specific packages you don't need on the ISO
   - Exclude directory patterns to reduce ISO size (cache, downloads, etc.)

4. **Build ISO**:
   - Click "Build ISO" and wait for the build to complete
   - Progress and logs are displayed in real-time

5. **Optional: Write to USB**:
   - After successful build, optionally write the ISO directly to a USB drive

## Configuration

Settings are automatically saved to `~/.config/iso_builder_gui.json` and persist between sessions:

- `work_dir`: Working directory for ISO build
- `output_dir`: Output directory for ISO file
- `iso_name`: Name of the generated ISO
- `username`: Username for the configured user account
- `user_password`: Password for the configured user account
- `user_sudo`: Whether to grant sudo access to the user
- `root_password`: Root password (required for system operations)
- `template_user`: System user whose home will be used as template
- `excluded_packages`: List of packages to exclude
- `exclude_dirs`: List of directory patterns to exclude
- `write_to_usb`: Whether to write ISO to USB after build
- `compression_type`: Compression algorithm (`zstd`, `gzip`, or `xz`)
- `compression_level`: Compression level (optional, uses defaults if not set)

## How It Works

### Build Process

1. **Cleanup**: Removes previous build artifacts
2. **Profile Setup**: Copies archiso releng profile
3. **Package Detection**: Scans your system for installed packages
4. **AUR Handling**: Copies AUR packages to a local repository
5. **User Template**: Copies selected user's home directory (if specified)
6. **Driver Configuration**: Detects and configures video, audio, and network drivers
7. **Kernel Detection**: Automatically detects CachyOS kernels
8. **Script Generation**: Creates customization and installation scripts
9. **ISO Build**: Runs `mkarchiso` to build the final ISO

### Live Session Features

The live ISO includes:

- **Video Drivers**: Intel (i915), AMD (amdgpu/radeon), Nvidia (nvidia/nvidia-open)
- **Audio Support**: PipeWire, ALSA, and SOF firmware for modern audio controllers
- **Network Support**: NetworkManager, iwd, and wpa_supplicant for WiFi and Ethernet
- **Firmware**: Comprehensive linux-firmware package for hardware support
- **GNOME Desktop**: Full GNOME desktop environment with Wayland support
- **Automatic Login**: Configured user (or root) automatically logs in to desktop

### Installation Process

The installer script (`install.sh`) provides:

- UEFI/GPT partitioning with EFI and root partitions
- Package installation from the ISO's package list
- Video driver selection (Intel, AMD, NVIDIA, or All)
- Automatic CachyOS kernel detection and configuration
- User account creation with sudo access
- Wayland configuration for GDM
- systemd-boot bootloader configuration

## Build Optimization

### Compression Settings

The build time is significantly affected by the compression algorithm used for the squashfs filesystem. The builder includes optimization settings:

**Compression Options**:
- **Zstd (Recommended)**: Fast compression/decompression with good compression ratio (~3-4x faster than XZ, similar ratio at level 6)
- **Gzip**: Faster than XZ, moderate compression (~2x faster than XZ, slightly larger output)
- **XZ**: Best compression ratio but slowest (~5-10x slower compression, ~30% smaller output)

**Default**: Zstd with level 6 (recommended for most users - provides fast builds with good compression)

**Compression Levels**:
- **Zstd**: 1-22 (default: 6) - Lower = faster, Higher = smaller
- **Gzip**: 1-9 (default: 6) - Lower = faster, Higher = smaller
- **XZ**: 1-9 (default: 6) - Lower = faster, Higher = smaller

**Expected Build Times** (approximate for 16GB ISO):
- **Zstd level 6**: 20-40 minutes (recommended)
- **Gzip**: 30-50 minutes
- **XZ level 6**: 3+ hours (default archiso behavior)

### Reducing Build Time

To significantly reduce build time:

1. **Use Zstd Compression**:
   - Select "zstd (Fast, Recommended)" in Build Optimization settings
   - Keep default level 6 for good balance
   - Level 4-5 for even faster builds (slightly larger ISO)

2. **Reduce Work Directory Size**:
   - The work directory can grow to 50GB+ during builds
   - Ensure large directories are excluded (Downloads, Videos, Music)
   - Consider excluding browser caches and development files

3. **Optimize User Template**:
   - Only include essential configuration files
   - Default exclusions already remove cache, downloads, media files
   - Consider copying only `.config` directory if template is large

4. **Reduce Package Count**:
   - Exclude unnecessary packages from the ISO
   - Development tools, documentation, and large applications add build time
   - More packages = longer compression time

5. **SSD Storage**:
   - Use an SSD for the work directory for faster file operations
   - The work directory requires significant I/O during build

### Reducing ISO Size

The ISO can become large with many packages. To reduce size:

1. **Exclude Large Packages**: Use the package exclusion dialog to remove:
   - Development tools you don't need (`gcc`, `make`, build tools)
   - Documentation packages (`*-docs`)
   - Large applications you won't use

2. **Exclude Directories**: The default exclusions already remove:
   - Cache directories (`.cache`, browser caches)
   - Downloads, Videos, Music
   - Build artifacts (`node_modules`, `__pycache__`)
   - IDE data (`.vscode`, `.idea`)

3. **Selective User Template**: Instead of copying entire home directory:
   - Use the exclusion patterns to only copy `.config` and essential files
   - Manually copy specific directories if needed

### Video Driver Selection

The installer prompts for video driver selection:

- **Intel (i915)**: For Intel integrated graphics
- **AMD (amdgpu/radeon)**: For AMD GPUs (modern and legacy)
- **NVIDIA (nvidia)**: For NVIDIA GPUs (proprietary driver, best compatibility)
- **All**: Recommended for systems with multiple GPUs or unknown hardware

**Tip**: If you're unsure, select "All" - the installer will install all drivers and you can remove unused ones later.

### Nvidia Driver Detection

The builder automatically detects your installed Nvidia driver:

- **Proprietary `nvidia`**: Default, best compatibility
- **Open-source `nvidia-open`**: If you prefer open-source drivers

Both are properly configured with:
- X11 configuration files
- Wayland environment variables
- Proper kernel module loading

### CachyOS Kernel Support

If you're building from a CachyOS system:

- The builder automatically detects your CachyOS kernel variant
- Supported kernels: `linux-cachyos`, `linux-cachyos-bore`, `linux-cachyos-lts`, `linux-cachyos-hardened`, etc.
- The ISO will use the same kernel with all CachyOS optimizations

### User Account Setup

**Best Practices**:

- Use a non-root user account for daily use (more secure)
- Enable sudo access for administrative tasks
- Set strong passwords for both user and root accounts
- Use a user template if you want your configurations in the ISO

**Groups Included**: The configured user is automatically added to:
- `wheel` (for sudo access)
- `users`, `audio`, `video`, `optical`, `storage`
- `games`, `power`, `scanner`, `network`

### Troubleshooting Common Issues

#### Black Screen / No Display Manager

**Cause**: Missing or incorrect video driver

**Solution**:
1. Boot the ISO and press `Ctrl+Alt+F2` to switch to TTY
2. Login as root
3. Install the correct driver:
   ```bash
   # For Intel
   pacman -S xf86-video-intel

   # For AMD
   pacman -S xf86-video-amdgpu

   # For NVIDIA
   pacman -S nvidia nvidia-utils
   ```
4. Restart GDM: `systemctl restart gdm`

#### No WiFi Networks Detected

**Cause**: Missing WiFi firmware or drivers

**Solution**:
- The ISO includes `linux-firmware` which covers most WiFi chipsets
- If your specific chipset needs additional firmware:
  ```bash
  pacman -S linux-firmware-qlogic  # For specific chipsets
  ```
- Check your WiFi chipset: `lspci | grep -i network`
- NetworkManager should start automatically - check: `systemctl status NetworkManager`

#### No Audio / Audio Crackling

**Cause**: Missing audio firmware or PipeWire not running

**Solution**:
1. Ensure `sof-firmware` is installed (included by default)
2. Check PipeWire services:
   ```bash
   systemctl --user status pipewire pipewire-pulse wireplumber
   ```
3. Restart audio services:
   ```bash
   systemctl --user restart pipewire pipewire-pulse wireplumber
   ```

#### Installation Fails or ISO Won't Boot

**Diagnosis Steps**:

1. **Check ISO Integrity**:
   ```bash
   # On the live ISO
   md5sum /path/to/iso
   ```

2. **Verify Boot Mode**:
   - Ensure UEFI boot is enabled in BIOS
   - The installer requires UEFI (BIOS support requires script modification)

3. **Check Logs**:
   - Build logs are saved to `~/.config/iso_builder_logs/`
   - Installation errors appear in the terminal running `install.sh`

4. **Test in VM First**:
   - Before using on real hardware, test the ISO in a VM
   - Helps catch issues without risk

### Advanced Configuration

#### Custom Repository Support

The builder automatically includes your system's `pacman.conf`:

- Custom repositories (like CachyOS repos) are included
- AUR packages are handled via local repository
- Repository keys are copied if available

#### Excluding Specific Packages

To exclude packages:

1. Click "Exclude Packages" button
2. Search for packages to exclude
3. Check boxes for packages you don't want
4. Click "OK" to save

**Note**: Required packages (like `base`, `linux`, `mkinitcpio`) cannot be excluded.

#### Custom mkinitcpio Configuration

Video, audio, and network modules are automatically added to mkinitcpio for early loading:

- Video: `i915`, `amdgpu`, `radeon`, `nvidia`
- Audio: `snd_hda_intel`, `snd_sof_pci`, `snd_sof_intel_hda_common`
- Network: `iwlwifi`, `r8169`, `e1000e`, `igb`, `ath10k_pci`, `ath9k`, `rtw89`

These ensure hardware works in the live session before the full system loads.

### Creating a Minimal ISO

For a minimal ISO focused on installation only:

1. Exclude desktop environments except GNOME (if keeping GUI)
2. Exclude large applications (browsers, office suites, media players)
3. Keep only essential system packages
4. Use minimal user template or none at all

### Network Issues in Live Session

If network doesn't work automatically:

```bash
# Check NetworkManager status
systemctl status NetworkManager

# Start manually if needed
systemctl start NetworkManager

# For WiFi, connect via nmtui
nmtui

# Or use iwctl (if iwd is installed)
iwctl
station wlan0 scan
station wlan0 get-networks
station wlan0 connect <network-name>
```

## Project Structure

```
make-arch-iso/
├── main.py                 # Entry point
├── make_arch_iso/          # Main package
│   ├── __init__.py
│   ├── constants.py        # UI constants, paths, messages
│   ├── utils.py            # Utility functions
│   ├── builder.py          # ISOBuilderThread - core build logic
│   ├── usb_writer.py       # USBWriterThread - USB writing
│   └── gui/                # GUI components
│       ├── __init__.py
│       ├── main_window.py  # Main GUI window
│       ├── dialogs.py      # Exclusion dialogs
│       └── threads.py      # Package loading thread
├── scripts/                # Static script templates
│   ├── customize_airootfs.sh    # Live ISO customization
│   ├── install.sh               # Installation script
│   └── Install Arch.desktop     # Desktop shortcut
└── README.md
```

## Development

### Extending Functionality

**Add New Drivers**: Edit the `gui_must` list in `builder.py` to add driver packages.

**Modify Installation Flow**: Edit `scripts/install.sh` - changes are automatically used.

**Custom Live ISO Behavior**: Edit `scripts/customize_airootfs.sh`.

**Change Default Exclusions**: Modify `DEFAULT_EXCLUDE_DIRS` or `HOME_COPY_EXCLUDES` in `builder.py`.

### Testing

1. Build ISO in VM first to catch issues
2. Test installation in VM before using on real hardware
3. Check build logs in `~/.config/iso_builder_logs/`

## License

See original file for license information.
