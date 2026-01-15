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
