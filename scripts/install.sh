#!/bin/bash
set -euo pipefail

# Custom Arch installer (UEFI, GPT, EFI+root)
# WARNING: this wipes the selected disk.

ROOT_PASSWORD="{ROOT_PASSWORD}"
USERNAME="{USERNAME}"
USER_PASSWORD="{USER_PASSWORD}"
USER_SUDO="{USER_SUDO}"
HOSTNAME="arch-custom"
TIMEZONE="America/Denver"
LOCALE="en_US.UTF-8"

PKGLIST="/root/pkglist.txt"

echo "========================================"
echo "  Custom Arch Installer (UEFI, GPT)"
echo "========================================"
echo
lsblk -dpno NAME,SIZE,MODEL | sed 's/^/  /'
echo
read -r -p "Install to which disk (e.g. /dev/nvme0n1 or /dev/sda)? " DISK
if [[ ! -b "$DISK" ]]; then
  echo "ERROR: $DISK is not a block device"
  exit 1
fi

echo
echo "ABOUT TO WIPE: $DISK"
read -r -p "Type WIPE to confirm: " CONF
if [[ "$CONF" != "WIPE" ]]; then
  echo "Cancelled."
  exit 0
fi

# Basic sanity: require UEFI for systemd-boot path
if [[ ! -d /sys/firmware/efi/efivars ]]; then
  echo "ERROR: This script expects UEFI boot (no /sys/firmware/efi)."
  echo "If you need BIOS/GRUB support, modify bootloader section."
  exit 1
fi

echo "[1/8] Partitioning..."
sgdisk --zap-all "$DISK"
sgdisk -n 1:0:+512M -t 1:ef00 -c 1:"EFI" "$DISK"
sgdisk -n 2:0:0      -t 2:8300 -c 2:"ROOT" "$DISK"
partprobe "$DISK"
sleep 2

# Handle nvme/mmc partition naming
EFI_PART="$DISK1"
ROOT_PART="$DISK2"
if [[ "$DISK" =~ nvme|mmcblk ]]; then
  EFI_PART="$DISKp1"
  ROOT_PART="$DISKp2"
fi

echo "[2/8] Formatting..."
mkfs.fat -F32 "$EFI_PART"
mkfs.ext4 -F "$ROOT_PART"

echo "[3/8] Mounting..."
mount "$ROOT_PART" /mnt
mkdir -p /mnt/boot
mount "$EFI_PART" /mnt/boot

echo "[4/8] Installing base system..."
if [[ ! -f "$PKGLIST" ]]; then
  echo "WARN: $PKGLIST not found; installing minimal base only."
  # Detect CachyOS kernel in live environment
  if pacman -Qq linux-cachyos linux-cachyos-bore linux-cachyos-lts linux-cachyos-hardened &>/dev/null 2>&1; then
    # Determine which CachyOS kernel is installed
    if pacman -Qq linux-cachyos &>/dev/null; then
      DEFAULT_KERNEL="linux-cachyos"
    elif pacman -Qq linux-cachyos-bore &>/dev/null; then
      DEFAULT_KERNEL="linux-cachyos-bore"
    elif pacman -Qq linux-cachyos-lts &>/dev/null; then
      DEFAULT_KERNEL="linux-cachyos-lts"
    elif pacman -Qq linux-cachyos-hardened &>/dev/null; then
      DEFAULT_KERNEL="linux-cachyos-hardened"
    else
      DEFAULT_KERNEL="linux"
    fi
    echo "Detected CachyOS kernel, using: $DEFAULT_KERNEL"
    pacstrap -K /mnt base "$DEFAULT_KERNEL" linux-firmware networkmanager
  else
    pacstrap -K /mnt base linux linux-firmware networkmanager
  fi
else
  # Use current live pacman.conf (includes local-repo if you built it)
  pacstrap -K -C /etc/pacman.conf /mnt $(grep -v '^#' "$PKGLIST" | xargs)
fi

echo "[5/8] fstab..."
genfstab -U /mnt >> /mnt/etc/fstab

echo
echo "========================================"
echo "  Video Driver Selection"
echo "========================================"
echo "Select your primary graphics driver:"
echo "  1) Intel (i915)"
echo "  2) AMD (amdgpu/radeon)"
echo "  3) NVIDIA (nvidia)"
echo "  4) All (recommended for multi-GPU systems)"
echo
read -r -p "Enter choice [1-4] (default: 4): " DRIVER_CHOICE
DRIVER_CHOICE=$DRIVER_CHOICE:-4

case "$DRIVER_CHOICE" in
  1)
    MKINITCPIO_MODULES="i915"
    REMOVE_DRIVERS="xf86-video-amdgpu xf86-video-ati nvidia nvidia-open nvidia-utils nvidia-settings lib32-nvidia-utils"
    NVIDIA_PACKAGES=""
    ;;
  2)
    MKINITCPIO_MODULES="amdgpu radeon"
    REMOVE_DRIVERS="nvidia nvidia-open nvidia-utils nvidia-settings lib32-nvidia-utils"
    NVIDIA_PACKAGES=""
    ;;
  3)
    MKINITCPIO_MODULES="nvidia"
    REMOVE_DRIVERS="xf86-video-amdgpu xf86-video-ati"
    # Default to proprietary nvidia (better compatibility)
    # Will be detected from package list during installation
    NVIDIA_PACKAGES="auto"
    ;;
  4|*)
    MKINITCPIO_MODULES="i915 amdgpu radeon nvidia"
    REMOVE_DRIVERS=""
    # For multi-GPU systems, detect from package list
    NVIDIA_PACKAGES="auto"
    ;;
esac

# Common modules for audio + networking
COMMON_MODULES="snd_hda_intel snd_sof_pci snd_sof_intel_hda_common iwlwifi r8169 e1000e igb"
ALL_MODULES="$MKINITCPIO_MODULES $COMMON_MODULES"

echo "[6/8] System config (chroot)..."
arch-chroot /mnt /bin/bash -euo pipefail <<CHROOT
echo "root:$ROOT_PASSWORD" | chpasswd

# Create user account if configured
if [[ -n "$USERNAME" ]] && [[ "$USERNAME" != "None" ]] && [[ -n "$USER_PASSWORD" ]]; then
  echo "Creating user account: $USERNAME"
  # Create user with home directory and common groups
  useradd -m -G wheel,users,audio,video,optical,storage,games,power,scanner,network -s /bin/bash "$USERNAME" || true

  # Set user password
  echo "$USERNAME:$USER_PASSWORD" | chpasswd

  # Configure sudo access if enabled
  if [[ "$USER_SUDO" == "true" ]]; then
    echo "Configuring sudo access for $USERNAME"
    # Ensure sudo is installed
    pacman -S --noconfirm --needed sudo || true
    # Configure sudoers for wheel group (standard Arch way)
    sed -i 's/^# %wheel ALL=(ALL:ALL) ALL/%wheel ALL=(ALL:ALL) ALL/' /etc/sudoers || true
  fi
fi

ln -sf "/usr/share/zoneinfo/$TIMEZONE" /etc/localtime
hwclock --systohc

sed -i "s/^#$LOCALE/$LOCALE/" /etc/locale.gen || true
locale-gen
echo "LANG=$LOCALE" > /etc/locale.conf

echo "$HOSTNAME" > /etc/hostname
cat > /etc/hosts <<EOF
127.0.0.1   localhost
::1         localhost
127.0.1.1   $HOSTNAME.localdomain $HOSTNAME
EOF

# Configure video drivers based on selection
MKINITCPIO_MODULES="$MKINITCPIO_MODULES"
REMOVE_DRIVERS="$REMOVE_DRIVERS"
COMMON_MODULES="$COMMON_MODULES"
ALL_MODULES="$ALL_MODULES"
NVIDIA_PACKAGES="$NVIDIA_PACKAGES"

# Ensure core firmware, audio, and networking packages are present
pacman -Syu --noconfirm --needed \\
  linux-firmware sof-firmware \\
  networkmanager iwd wpa_supplicant \\
  pipewire pipewire-alsa pipewire-pulse wireplumber alsa-utils || true

if grep -q "GenuineIntel" /proc/cpuinfo; then
  pacman -S --noconfirm --needed intel-ucode || true
elif grep -q "AuthenticAMD" /proc/cpuinfo; then
  pacman -S --noconfirm --needed amd-ucode || true
fi

# Install NVIDIA drivers if selected
if [[ "$MKINITCPIO_MODULES" == *nvidia* ]]; then
  # Auto-detect which NVIDIA driver to install based on what was just installed
  if [[ "$NVIDIA_PACKAGES" == "auto" ]]; then
    if pacman -Qq nvidia-open &>/dev/null; then
      NVIDIA_PACKAGES="nvidia-open nvidia-open-utils"
      echo "Detected nvidia-open in installed packages"
    elif pacman -Qq nvidia &>/dev/null || pacman -Si nvidia &>/dev/null 2>&1; then
      NVIDIA_PACKAGES="nvidia nvidia-utils nvidia-settings lib32-nvidia-utils"
      echo "Detected nvidia (proprietary) driver available"
    else
      # Default to proprietary nvidia if nothing found (best compatibility)
      NVIDIA_PACKAGES="nvidia nvidia-utils nvidia-settings lib32-nvidia-utils"
      echo "No NVIDIA driver detected, installing proprietary nvidia by default"
    fi
  fi

  if [[ -n "$NVIDIA_PACKAGES" ]] && [[ "$NVIDIA_PACKAGES" != "auto" ]]; then
    echo "Installing NVIDIA driver packages: $NVIDIA_PACKAGES"
    pacman -S --noconfirm --needed $NVIDIA_PACKAGES || true

    # Create X11 configuration for NVIDIA (if using proprietary driver)
    # Modern X11 typically uses auto-detection, but some setups benefit from explicit config
    if [[ "$NVIDIA_PACKAGES" == *"nvidia "* ]] && [[ "$NVIDIA_PACKAGES" != *"nvidia-open"* ]]; then
      mkdir -p /etc/X11/xorg.conf.d
      cat > /etc/X11/xorg.conf.d/20-nvidia.conf <<'XEOF'
Section "Device"
    Identifier "NVIDIA Card"
    Driver "nvidia"
    VendorName "NVIDIA Corporation"
    # Modern options for better compatibility
    Option "UseDisplayDevice" "none"
    Option "AllowEmptyInitialConfiguration" "true"
    Option "TripleBuffer" "true"
EndSection
XEOF
      echo "Created X11 configuration for NVIDIA proprietary driver"
    fi

    # For Wayland support with NVIDIA (proprietary driver)
    if [[ "$NVIDIA_PACKAGES" == *"nvidia "* ]] && [[ "$NVIDIA_PACKAGES" != *"nvidia-open"* ]]; then
    # Set environment variables for Wayland NVIDIA support
    mkdir -p /etc/environment.d
    cat > /etc/environment.d/10-nvidia-wayland.conf <<'WEOF'
# NVIDIA Wayland support
WLR_NO_HARDWARE_CURSORS=1
__GLX_VENDOR_LIBRARY_NAME=nvidia
WEOF
      echo "Configured environment for NVIDIA Wayland support"
    fi
  fi
fi

if [[ -n "$MKINITCPIO_MODULES" ]]; then
  echo "Configuring mkinitcpio with modules: $MKINITCPIO_MODULES"
  sed -i "s/^MODULES=.*/MODULES=($MKINITCPIO_MODULES)/" /etc/mkinitcpio.conf || true
  # Generate initramfs for installed kernel
  # mkinitcpio -P will generate for all installed kernels
  mkinitcpio -P || true
  # If CachyOS kernel is detected, ensure initramfs is generated for it
  if [[ "$INSTALLED_KERNEL" != "linux" ]]; then
    echo "Generating initramfs for CachyOS kernel: $INSTALLED_KERNEL"
    mkinitcpio -p "$INSTALLED_KERNEL" || true
  fi
fi

if [[ -n "$ALL_MODULES" ]]; then
  echo "Ensuring common modules load on boot: $ALL_MODULES"
  cat > /etc/modules-load.d/custom-arch-iso.conf <<EOF
$ALL_MODULES
EOF
fi

# Remove unneeded driver packages if specified
if [[ -n "$REMOVE_DRIVERS" ]]; then
  echo "Removing unneeded driver packages: $REMOVE_DRIVERS"
  pacman -Rns --noconfirm $REMOVE_DRIVERS 2>/dev/null || true
fi

# Remove deprecated video drivers if present
# xf86-video-intel is deprecated (Intel now uses modesetting driver)
# xf86-video-ati is deprecated (replaced by xf86-video-amdgpu for modern hardware)
pacman -Rns --noconfirm xf86-video-intel xf86-video-ati 2>/dev/null || true

# Ensure nvidia modules are loaded on boot if NVIDIA is selected and installed
if [[ "$MKINITCPIO_MODULES" == *nvidia* ]]; then
  if [[ "$NVIDIA_PACKAGES" != "auto" ]] && [[ -n "$NVIDIA_PACKAGES" ]]; then
    mkdir -p /etc/modules-load.d
    echo "nvidia" > /etc/modules-load.d/nvidia.conf
    echo "nvidia_uvm" >> /etc/modules-load.d/nvidia.conf
    echo "nvidia_drm" >> /etc/modules-load.d/nvidia.conf
    echo "nvidia_modeset" >> /etc/modules-load.d/nvidia.conf
  elif pacman -Qq nvidia nvidia-open &>/dev/null 2>&1; then
    # NVIDIA driver is installed, ensure modules load
    mkdir -p /etc/modules-load.d
    echo "nvidia" > /etc/modules-load.d/nvidia.conf
    echo "nvidia_uvm" >> /etc/modules-load.d/nvidia.conf
    echo "nvidia_drm" >> /etc/modules-load.d/nvidia.conf
    echo "nvidia_modeset" >> /etc/modules-load.d/nvidia.conf
  fi
fi

# Detect CachyOS kernel if installed
INSTALLED_KERNEL="linux"
INSTALLED_KERNEL_VMLINUZ="/vmlinuz-linux"
INSTALLED_KERNEL_INITRD="/initramfs-linux.img"

# Check for CachyOS kernels in order of preference
for kernel in linux-cachyos linux-cachyos-bore linux-cachyos-bmq linux-cachyos-deckify \
              linux-cachyos-eevdf linux-cachyos-lts linux-cachyos-hardened \
              linux-cachyos-rc linux-cachyos-server linux-cachyos-rt-bore; do
  if pacman -Qq "$kernel" &>/dev/null; then
    INSTALLED_KERNEL="$kernel"
    # Kernel image paths follow standard naming convention
    INSTALLED_KERNEL_VMLINUZ="/vmlinuz-$kernel"
    INSTALLED_KERNEL_INITRD="/initramfs-$kernel.img"
    echo "Detected CachyOS kernel: $kernel"
    break
  fi
done

# If no CachyOS kernel found, check for standard kernel
if [[ "$INSTALLED_KERNEL" == "linux" ]]; then
  if pacman -Qq linux &>/dev/null; then
    echo "Using standard Arch Linux kernel"
  else
    echo "WARNING: No kernel detected, will install linux as default"
  fi
fi

# Remove other kernel packages if a specific kernel is detected
if [[ "$INSTALLED_KERNEL" != "linux" ]]; then
  # Remove standard Arch kernels
  pacman -Rns --noconfirm \\
    linux linux-lts linux-zen linux-hardened linux-rt \\
    linux-headers linux-lts-headers linux-zen-headers linux-hardened-headers linux-rt-headers \\
    2>/dev/null || true
  # Ensure detected CachyOS kernel is installed
  pacman -S --noconfirm --needed "$INSTALLED_KERNEL" || true
else
  # Standard kernel - remove alternatives
  pacman -S --noconfirm --needed linux || true
  pacman -Rns --noconfirm \\
    linux-lts linux-zen linux-hardened linux-rt \\
    linux-lts-headers linux-zen-headers linux-hardened-headers linux-rt-headers \\
    2>/dev/null || true
fi

# Services
systemctl enable NetworkManager.service || true
if pacman -Qq gdm &>/dev/null; then
  systemctl enable gdm.service || true
  mkdir -p /etc/gdm
  # Determine autologin user (use configured user, fallback to root)
  AUTO_LOGIN_USER="$USERNAME"
  if [[ -z "$AUTO_LOGIN_USER" ]] || [[ "$AUTO_LOGIN_USER" == "None" ]] || [[ -z "$USER_PASSWORD" ]]; then
    AUTO_LOGIN_USER="root"
  fi

  cat > /etc/gdm/custom.conf <<EOF
[daemon]
AutomaticLoginEnable=True
AutomaticLogin=$AUTO_LOGIN_USER
# Enable Wayland by default (fallback to X11 if needed)
WaylandEnable=true
EOF

  # Ensure Wayland session is available and configured
  mkdir -p /etc/environment.d
  cat > /etc/environment.d/10-wayland.conf <<EOF
# Enable Wayland support
XDG_SESSION_TYPE=wayland
EOF
  echo "Configured Wayland support for GDM"
fi

# Ensure optimal screen resolution on first login
cat > /usr/local/bin/set-optimal-resolution.sh <<'EOF'
#!/bin/bash
set -euo pipefail

if ! command -v xrandr >/dev/null 2>&1; then
  exit 0
fi

while read -r output status _; do
  if [[ "$status" != "connected" ]]; then
    continue
  fi
  preferred=$(xrandr --query | awk -v out="$output" '
    $1 == out {{active=1; next}}
    active && $0 ~ /^[[:space:]]+[0-9]+x[0-9]+/ {{
      if ($0 ~ /\\+/) {{print $1; exit}}
    }}
    active && $0 !~ /^[[:space:]]/ {{active=0}}
  ')
  if [[ -n "$preferred" ]]; then
    xrandr --output "$output" --mode "$preferred" --rate 60 2>/dev/null || \
      xrandr --output "$output" --mode "$preferred" 2>/dev/null || true
  else
    xrandr --output "$output" --auto 2>/dev/null || true
  fi
done < <(xrandr --query | awk '/ connected / {{print $1 " connected"}}')
EOF
chmod 755 /usr/local/bin/set-optimal-resolution.sh

mkdir -p /etc/xdg/autostart
cat > /etc/xdg/autostart/set-optimal-resolution.desktop <<EOF
[Desktop Entry]
Type=Application
Name=Set Optimal Resolution
Exec=/usr/local/bin/set-optimal-resolution.sh
Terminal=false
X-GNOME-Autostart-enabled=true
EOF

# Bootloader: systemd-boot
bootctl install
ROOT_UUID=\\$(blkid -s UUID -o value "{'{'}ROOT_PART{'}'}")
KERNEL_VMLINUZ="$INSTALLED_KERNEL_VMLINUZ"
KERNEL_INITRD="$INSTALLED_KERNEL_INITRD"
KERNEL_NAME="$INSTALLED_KERNEL"

# Verify kernel files exist, if not try to find them
if [[ ! -f "/boot$KERNEL_VMLINUZ" ]]; then
  echo "WARNING: Kernel image not found at /boot$KERNEL_VMLINUZ, searching..."
  # Try to find the kernel image
  KERNEL_VMLINUZ=$(find /boot -name "vmlinuz-$KERNEL_NAME*" -o -name "vmlinuz-$KERNEL_NAME" 2>/dev/null | head -1 | sed 's|/boot||')
  if [[ -n "$KERNEL_VMLINUZ" ]]; then
    echo "Found kernel at: $KERNEL_VMLINUZ"
  else
    echo "ERROR: Could not find kernel image, using default path"
    KERNEL_VMLINUZ="/vmlinuz-$KERNEL_NAME"
  fi
fi

if [[ ! -f "/boot$KERNEL_INITRD" ]]; then
  echo "WARNING: Initramfs not found at /boot$KERNEL_INITRD, searching..."
  # Try to find the initramfs
  KERNEL_INITRD=$(find /boot -name "initramfs-$KERNEL_NAME*.img" 2>/dev/null | head -1 | sed 's|/boot||')
  if [[ -n "$KERNEL_INITRD" ]]; then
    echo "Found initramfs at: $KERNEL_INITRD"
  else
    echo "ERROR: Could not find initramfs, using default path"
    KERNEL_INITRD="/initramfs-$KERNEL_NAME.img"
  fi
fi

cat > /boot/loader/loader.conf <<EOF
default arch
timeout 3
beep   off
editor  0
EOF

cat > /boot/loader/entries/arch.conf <<EOF
title   Arch Linux (Custom - $KERNEL_NAME)
linux   $KERNEL_VMLINUZ
initrd  $KERNEL_INITRD
options root=UUID=\\$ROOT_UUID rw
EOF

echo "Created bootloader entry with kernel: $KERNEL_NAME"
echo "  Kernel: $KERNEL_VMLINUZ"
echo "  Initramfs: $KERNEL_INITRD"
CHROOT

echo "[7/8] Done. Unmounting..."
umount -R /mnt

echo "[8/8] Installation complete."
echo "Reboot when ready."
