#!/bin/bash
set -euo pipefail

echo "[customize_airootfs] running..."

# 1) Set root password
echo "root:{ROOT_PASSWORD}" | chpasswd

# 2) Create user account
TARGET_USER=""
TEMPLATE_USER="{TEMPLATE_USER}"
TEMPLATE_DIR="/etc/skel/user_template_$TEMPLATE_USER"
if [[ -n "{USERNAME}" ]] && [[ "{USERNAME}" != "None" ]] && [[ -n "{USER_PASSWORD}" ]]; then
  echo "Creating user account: {USERNAME}"
  TARGET_USER="{USERNAME}"
  # Create user with home directory and common groups
  useradd -m -G wheel,users,audio,video,optical,storage,games,power,scanner,network -s /bin/bash "$TARGET_USER" || true
  
  # Set user password
  echo "$TARGET_USER:{USER_PASSWORD}" | chpasswd
  
  # Configure sudo access if enabled
  if [[ "{USER_SUDO}" == "true" ]]; then
    echo "Configuring sudo access for $TARGET_USER"
    # Ensure sudo is installed
    pacman -S --noconfirm --needed sudo || true
    # Configure sudoers for wheel group (standard Arch way)
    sed -i 's/^# %wheel ALL=(ALL:ALL) ALL/%wheel ALL=(ALL:ALL) ALL/' /etc/sudoers || true
    # User is already in wheel group from useradd command above
  fi
  
  # Copy user template from template user if specified
  if [[ -n "$TEMPLATE_USER" ]] && [[ "$TEMPLATE_USER" != "None" ]]; then
    if [[ -d "$TEMPLATE_DIR" ]]; then
      echo "Copying template from $TEMPLATE_DIR to /home/$TARGET_USER"
      rsync -a "$TEMPLATE_DIR/" "/home/$TARGET_USER/" || true
      chown -R "$TARGET_USER:$TARGET_USER" "/home/$TARGET_USER" || true
    fi
  fi

  # Copy user themes to system-wide location
  if [[ -n "$TEMPLATE_USER" ]] && [[ "$TEMPLATE_USER" != "None" ]]; then
    for theme_dir in ".themes" ".local/share/themes"; do
      if [[ -d "$TEMPLATE_DIR/$theme_dir" ]]; then
        mkdir -p /usr/share/themes
        rsync -a "$TEMPLATE_DIR/$theme_dir/" /usr/share/themes/ || true
      fi
    done
  fi

  # Copy user .desktop entries system-wide
  if [[ -n "$TEMPLATE_USER" ]] && [[ "$TEMPLATE_USER" != "None" ]]; then
    if [[ -d "$TEMPLATE_DIR/.local/share/applications" ]]; then
      mkdir -p /usr/share/applications
      rsync -a --include '*/' --include '*.desktop' --exclude '*' \
        "$TEMPLATE_DIR/.local/share/applications/" /usr/share/applications/ || true
    fi
    if [[ -d "$TEMPLATE_DIR/.config/autostart" ]]; then
      mkdir -p /etc/xdg/autostart
      rsync -a --include '*/' --include '*.desktop' --exclude '*' \
        "$TEMPLATE_DIR/.config/autostart/" /etc/xdg/autostart/ || true
    fi
  fi

  # Update GNOME Files bookmarks if username differs from template user
  if [[ -n "$TEMPLATE_USER" ]] && [[ "$TEMPLATE_USER" != "None" ]] && [[ "$TEMPLATE_USER" != "$TARGET_USER" ]]; then
    bookmarks_file="/home/$TARGET_USER/.config/gtk-3.0/bookmarks"
    if [[ -f "$bookmarks_file" ]]; then
      sed -i "s|/home/$TEMPLATE_USER/|/home/$TARGET_USER/|g" "$bookmarks_file"
    fi
  fi

else
  echo "No user account configured, using root account only"
fi

# Set fish as the default shell system-wide
if pacman -Qq fish &>/dev/null; then
  if ! grep -q "^/usr/bin/fish$" /etc/shells; then
    echo "/usr/bin/fish" >> /etc/shells
  fi
  chsh -s /usr/bin/fish root || true
  if [[ -n "$TARGET_USER" ]]; then
    chsh -s /usr/bin/fish "$TARGET_USER" || true
  fi
  if [[ -f /etc/default/useradd ]]; then
    if grep -q "^SHELL=" /etc/default/useradd; then
      sed -i 's|^SHELL=.*|SHELL=/usr/bin/fish|' /etc/default/useradd
    else
      echo "SHELL=/usr/bin/fish" >> /etc/default/useradd
    fi
  else
    echo "SHELL=/usr/bin/fish" > /etc/default/useradd
  fi
fi

# Copy oh-my-posh configuration system-wide
if pacman -Qq oh-my-posh &>/dev/null; then
  OMP_SOURCE=""
  if [[ -n "$TEMPLATE_USER" ]] && [[ "$TEMPLATE_USER" != "None" ]]; then
    if [[ -d "$TEMPLATE_DIR/.config/oh-my-posh" ]]; then
      OMP_SOURCE="$TEMPLATE_DIR/.config/oh-my-posh"
    elif [[ -d "$TEMPLATE_DIR/.poshthemes" ]]; then
      OMP_SOURCE="$TEMPLATE_DIR/.poshthemes"
    fi
  fi

  if [[ -n "$OMP_SOURCE" ]]; then
    mkdir -p /etc/oh-my-posh
    rsync -a "$OMP_SOURCE/" /etc/oh-my-posh/ || true
  fi

  OMP_CONFIG="$(find /etc/oh-my-posh -maxdepth 2 -type f -name '*.json' | head -n 1)"
  if [[ -n "$OMP_CONFIG" ]]; then
    mkdir -p /etc/fish/conf.d
    cat > /etc/fish/conf.d/oh-my-posh.fish <<EOF
if type -q oh-my-posh
    oh-my-posh init fish --config "$OMP_CONFIG" | source
end
EOF
  fi
fi

# 3) Restore root home from template (if present) - keep for compatibility
TEMPLATE_DIR="/etc/skel/root_template"
if [[ -d "$TEMPLATE_DIR" ]]; then
  rsync -a "$TEMPLATE_DIR/" /root/ || true
  chown -R root:root /root || true
fi

# Remove user template directories after use
rm -rf /etc/skel/user_template_* || true

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
systemctl disable NetworkManager-wait-online.service || true
systemctl disable systemd-networkd-wait-online.service || true

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
if pacman -Qq nvidia &>/dev/null || pacman -Qq nvidia-open &>/dev/null || pacman -Qq | grep -qE '^nvidia-.*-dkms$'; then
  # Ensure NVIDIA DRM modesetting is enabled for Wayland and GDM
  mkdir -p /etc/modprobe.d
  cat > /etc/modprobe.d/nvidia-drm.conf <<EOF
# Enable DRM modesetting for NVIDIA
options nvidia_drm modeset=1
EOF

  # Load NVIDIA modules during boot if they aren't brought in by initramfs
  mkdir -p /etc/modules-load.d
  cat > /etc/modules-load.d/nvidia.conf <<EOF
nvidia
nvidia_modeset
nvidia_uvm
nvidia_drm
EOF

  # Prefer NVIDIA over nouveau if present
  cat > /etc/modprobe.d/blacklist-nouveau.conf <<EOF
# Disable nouveau when NVIDIA proprietary drivers are installed
blacklist nouveau
options nouveau modeset=0
EOF
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
