#!/bin/bash
set -euo pipefail

echo "[customize_airootfs] running..."

# 1) Set root password
echo "root:{ROOT_PASSWORD}" | chpasswd

# 2) Create user account
if [[ -n "{USERNAME}" ]] && [[ "{USERNAME}" != "None" ]] && [[ -n "{USER_PASSWORD}" ]]; then
  echo "Creating user account: {USERNAME}"
  # Create user with home directory and common groups
  useradd -m -G wheel,users,audio,video,optical,storage,games,power,scanner,network -s /bin/bash "{USERNAME}" || true

  # Set user password
  echo "{USERNAME}:{USER_PASSWORD}" | chpasswd

  # Configure sudo access if enabled
  if [[ "{USER_SUDO}" == "true" ]]; then
    echo "Configuring sudo access for {USERNAME}"
    # Ensure sudo is installed
    pacman -S --noconfirm --needed sudo || true
    # Configure sudoers for wheel group (standard Arch way)
    sed -i 's/^# %wheel ALL=(ALL:ALL) ALL/%wheel ALL=(ALL:ALL) ALL/' /etc/sudoers || true
    # User is already in wheel group from useradd command above
  fi

  # Copy user template from template user if specified
  TEMPLATE_USER="{TEMPLATE_USER}"
  if [[ -n "$TEMPLATE_USER" ]] && [[ "$TEMPLATE_USER" != "None" ]]; then
    TEMPLATE_DIR="/etc/skel/user_template_$TEMPLATE_USER"
    if [[ -d "$TEMPLATE_DIR" ]]; then
      echo "Copying template from $TEMPLATE_DIR to /home/{USERNAME}"
      rsync -a "$TEMPLATE_DIR/" "/home/{USERNAME}/" || true
      chown -R "{USERNAME}:{USERNAME}" "/home/{USERNAME}" || true
    fi
  fi
else
  echo "No user account configured, using root account only"
fi

# 3) Restore root home from template (if present) - keep for compatibility
TEMPLATE_DIR="/etc/skel/root_template"
if [[ -d "$TEMPLATE_DIR" ]]; then
  rsync -a "$TEMPLATE_DIR/" /root/ || true
  chown -R root:root /root || true
fi

# 4) Networking
systemctl enable NetworkManager.service || true

# 4a) Ensure audio services are enabled
if pacman -Qq pipewire &>/dev/null; then
  # Enable PipeWire services for audio
  systemctl --global enable pipewire pipewire-pulse wireplumber || true
fi

# 4b) Ensure network services are available
if pacman -Qq iwd &>/dev/null; then
  systemctl enable iwd.service || true
fi
if pacman -Qq wpa_supplicant &>/dev/null; then
  systemctl enable wpa_supplicant.service || true
fi

# 4c) Disable motherboard speaker beep (pcspkr module)
# Blacklist pcspkr module to prevent beeping during boot and in live session
mkdir -p /etc/modprobe.d
cat > /etc/modprobe.d/blacklist-pcspkr.conf <<EOF
# Disable motherboard speaker (pcspkr) to prevent beeping
blacklist pcspkr
EOF

# Also disable terminal bell in inputrc
mkdir -p /etc/skel
if ! grep -q "set bell-style none" /etc/inputrc 2>/dev/null; then
  cat >> /etc/inputrc <<EOF

# Disable terminal bell
set bell-style none
EOF
fi

# 5) Ensure video drivers are loaded (KMS modules are in mkinitcpio)
# The video driver modules (i915, amdgpu, radeon, nvidia) are already
# configured in mkinitcpio.conf for early loading during boot

# 5a) Configure NVIDIA drivers for live session
# Detect if NVIDIA driver is installed and configure X11/Wayland support
if pacman -Qq nvidia nvidia-open nvidia-580xx-dkms nvidia-470xx-dkms nvidia-390xx-dkms nvidia-340xx-dkms &>/dev/null 2>&1; then
  echo "NVIDIA driver detected, configuring for live session..."

  # Determine which NVIDIA driver is installed
  NVIDIA_DRIVER=""
  NVIDIA_VERSION=""
  if pacman -Qq nvidia &>/dev/null; then
    NVIDIA_DRIVER="nvidia"
  elif pacman -Qq nvidia-open &>/dev/null; then
    NVIDIA_DRIVER="nvidia-open"
  elif pacman -Qq nvidia-580xx-dkms &>/dev/null; then
    NVIDIA_DRIVER="nvidia-580xx-dkms"
    NVIDIA_VERSION="580xx"
  elif pacman -Qq nvidia-470xx-dkms &>/dev/null; then
    NVIDIA_DRIVER="nvidia-470xx-dkms"
    NVIDIA_VERSION="470xx"
  elif pacman -Qq nvidia-390xx-dkms &>/dev/null; then
    NVIDIA_DRIVER="nvidia-390xx-dkms"
    NVIDIA_VERSION="390xx"
  elif pacman -Qq nvidia-340xx-dkms &>/dev/null; then
    NVIDIA_DRIVER="nvidia-340xx-dkms"
    NVIDIA_VERSION="340xx"
  fi

  if [[ -n "$NVIDIA_DRIVER" ]]; then
    echo "Configuring NVIDIA driver: $NVIDIA_DRIVER"

    # Create X11 configuration for NVIDIA (proprietary driver only)
    # Modern X11 uses auto-detection, but a minimal config helps with compatibility
    # nvidia-open driver doesn't need explicit X11 config
    if [[ "$NVIDIA_DRIVER" != "nvidia-open" ]] && [[ "$NVIDIA_DRIVER" != "" ]]; then
      mkdir -p /etc/X11/xorg.conf.d
      cat > /etc/X11/xorg.conf.d/20-nvidia.conf <<'XEOF'
Section "Device"
    Identifier "NVIDIA Card"
    Driver "nvidia"
    VendorName "NVIDIA Corporation"
    # Modern options for better compatibility
    # UseDisplayDevice "none" allows X to start without a connected display
    # AllowEmptyInitialConfiguration enables headless operation
    Option "UseDisplayDevice" "none"
    Option "AllowEmptyInitialConfiguration" "true"
    Option "TripleBuffer" "true"
EndSection
XEOF
      echo "Created X11 configuration for NVIDIA proprietary driver"
    fi

    # Set environment variables for Wayland NVIDIA support (proprietary driver only)
    if [[ "$NVIDIA_DRIVER" != "nvidia-open" ]]; then
      mkdir -p /etc/environment.d
      cat > /etc/environment.d/10-nvidia-wayland.conf <<'WEOF'
# NVIDIA Wayland support
WLR_NO_HARDWARE_CURSORS=1
__GLX_VENDOR_LIBRARY_NAME=nvidia
WEOF
      echo "Configured environment for NVIDIA Wayland support"
    fi

    # Ensure NVIDIA modules are loaded
    mkdir -p /etc/modules-load.d
    cat > /etc/modules-load.d/nvidia.conf <<'NEOF'
nvidia
nvidia_uvm
nvidia_drm
nvidia_modeset
NEOF
    echo "Configured NVIDIA modules to load on boot"

    # For DKMS drivers, ensure modules are built during ISO creation
    if [[ "$NVIDIA_DRIVER" == *"-dkms" ]]; then
      echo "DKMS driver detected: $NVIDIA_DRIVER"
      # Verify DKMS and kernel headers are present
      if ! pacman -Qq dkms &>/dev/null 2>&1; then
        echo "WARNING: DKMS package not found. Installing dkms..."
        pacman -S --noconfirm --needed dkms || true
      fi
      if ! pacman -Qq linux-headers linux-lts-headers linux-cachyos-headers linux-cachyos-bore-headers linux-cachyos-lts-headers linux-cachyos-hardened-headers &>/dev/null 2>&1; then
        echo "WARNING: Kernel headers not found for DKMS build. NVIDIA DKMS driver may not work."
      else
        # Ensure DKMS modules are built for the current kernel
        # This is needed because archiso installs packages but modules may not be built yet
        echo "Building DKMS modules for current kernel..."
        dkms autoinstall -k "$(uname -r)" || true
        # Also try building for all installed kernels
        dkms autoinstall || true
      fi
    fi
  fi
fi

# 6) GNOME Display Manager + graphical boot with Wayland support
if pacman -Qq gdm &>/dev/null; then
  systemctl enable gdm.service || true

  # Autologin configuration
  mkdir -p /etc/gdm
  AUTO_LOGIN_USER="{USERNAME}"
  if [[ -z "$AUTO_LOGIN_USER" ]] || [[ "$AUTO_LOGIN_USER" == "None" ]] || [[ -z "{USER_PASSWORD}" ]]; then
    AUTO_LOGIN_USER="root"
  fi

  cat > /etc/gdm/custom.conf <<EOF
[daemon]
AutomaticLoginEnable=True
AutomaticLogin=$AUTO_LOGIN_USER
# Enable Wayland by default (fallback to X11 if needed)
WaylandEnable=true

[security]

[xdmcp]

[chooser]

[debug]
EOF

  # Ensure Wayland session is available and configured
  # GDM will automatically use Wayland for compatible systems
  mkdir -p /etc/environment.d
  cat > /etc/environment.d/10-wayland.conf <<EOF
# Enable Wayland support
XDG_SESSION_TYPE=wayland
EOF
fi

# Ensure we boot to graphical target by default
ln -sf /usr/lib/systemd/system/graphical.target /etc/systemd/system/default.target || true

echo "[customize_airootfs] done."
