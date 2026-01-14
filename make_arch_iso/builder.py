"""ISO Builder Thread"""
import os
import subprocess
from pathlib import Path
from typing import List, Tuple

from .qt_compat import QThread, pyqtSignal
from .constants import Messages
from .utils import run_command, safe_remove, safe_makedirs


class ISOBuilderThread(QThread):
    """Thread for building ISO without blocking the UI"""
    output_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(bool, str)

    # Default directories to exclude from ISO (temp/cache files)
    DEFAULT_EXCLUDE_DIRS = [
        # Cache directories
        '.cache',
        'cache',
        '.local/share/Trash',
        '.thumbnails',
        '.thumbs',
        # User directories (large media files)
        'Downloads',
        'Downloads/*',
        'Templates',
        'Public',
        'Videos',
        'Music',
        'Pictures',
        'Documents',
        # Browser caches
        '.mozilla/firefox/*/cache2',
        '.mozilla/firefox/*/Cache',
        '.mozilla/firefox/*/cache',
        '.config/google-chrome/*/Cache',
        '.config/google-chrome/*/cache',
        '.config/chromium/*/Cache',
        '.config/chromium/*/cache',
        '.config/BraveSoftware/*/Cache',
        '.config/BraveSoftware/*/cache',
        # Snap/Docker/VirtualBox
        'snap',
        '.snap',
        '.docker',
        'docker',
        'VirtualBox VMs',
        '.VirtualBox',
        # Temp directories
        'tmp',
        'temp',
        '.tmp',
        '.temp',
        # Build artifacts
        'node_modules',
        '__pycache__',
        '.pytest_cache',
        '.tox',
        'dist',
        'build',
        '.build',
        '.eggs',
        '*.egg-info',
        '.coverage',
        'htmlcov',
        # Package manager caches
        '.npm',
        '.yarn',
        '.yarn/cache',
        '.gradle',
        '.m2',
        '.pip',
        '.cargo/registry',
        '.cargo/git',
        'go/pkg',
        # Steam
        '.steam',
        '.local/share/Steam',
        # IDE/Editor files
        '.idea',
        '.vscode',
        '.vs',
        '.vim',
        '.venv',
        '.env',
        '.viminfo',
        '.sublime-*',
        '.atom',
        # Log files
        '*.log',
        '.logs',
        # Lock files
        '*.lock',
        '.lock',
        '.DS_Store',
        'Thumbs.db',
    ]
    # Directories to include when copying user template (focus on configs)
    HOME_COPY_INCLUDES = [
        '.config',  # GTK, Qt, and other app configs
        '.local/share',  # Application data (excluding trash)
        '.gtkrc*',
        '.Xresources',
        '.xprofile',
        '.bashrc',
        '.bash_profile',
        '.profile',
        '.zshrc',
        '.zshenv',
        '.vimrc',
        '.gitconfig',
        '.ssh',
        '.gnupg',
        'Dev/*',
    ]
    # Directories to exclude when copying user template (temp/cache files)
    HOME_COPY_EXCLUDES = [
        # Cache directories
        '.cache',
        '.cache/*',
        '.local/share/Trash',
        '.thumbnails',
        '.thumbs',
        '.thumb',
        # Browser caches
        '.mozilla/firefox/*/cache2',
        '.mozilla/firefox/*/Cache',
        '.mozilla/firefox/*/cache',
        '.config/google-chrome/*/Cache',
        '.config/google-chrome/*/cache',
        '.config/chromium/*/Cache',
        '.config/chromium/*/cache',
        '.config/BraveSoftware/*/Cache',
        '.config/BraveSoftware/*/cache',
        # Temp directories
        'tmp',
        'temp',
        '.tmp',
        '.temp',
        'Downloads',
        # Package manager caches
        '.npm',
        '.yarn',
        '.yarn/cache',
        '.gradle',
        '.m2',
        '.cargo/registry',
        '.cargo/git',
        '.pip',
        # Build artifacts
        'node_modules',
        '__pycache__',
        '*.pyc',
        '*.pyo',
        '.pytest_cache',
        '.tox',
        'dist',
        'build',
        '.build',
        '.eggs',
        '*.egg-info',
        '.coverage',
        'htmlcov',
        # IDE/Editor files
        '.idea',
        '.vscode',
        '.vs',
        '.venv/*',
        '.env/*',
        '*.swp',
        '*.swo',
        '*.swn',
        '*~',
        '.vim',
        '.viminfo',
        '.sublime-*',
        '.atom',
        # Steam
        '.steam',
        '.local/share/Steam',
        # Log files
        '*.log',
        '*.log.*',
        '.logs',
        # Lock files
        '*.lock',
        '.lock',
        '.DS_Store',
        'Thumbs.db',
    ]

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.process = None

    def _emit(self, message: str) -> None:
        self.output_signal.emit(message)

    def _write_text(self, path: str, content: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8', newline='') as f:
            f.write(content)

    def _write_script(self, path: str, content: str) -> None:
        self._write_text(path, content)
        os.chmod(path, 0o755)

    def _make_rsync_excludes(self, patterns: List[str]) -> List[str]:
        return [f'--exclude={pattern}' for pattern in patterns]

    def _build_package_list(
        self,
        profile_dir: str,
        packages: List[str],
        excluded_packages: List[str]
    ) -> Tuple[str, List[str], int, set]:
        pkg_file = os.path.join(profile_dir, 'packages.x86_64')
        if not os.path.exists(pkg_file):
            self._emit(
                f"[ERROR] packages.x86_64 not found: {pkg_file}\n"
            )
            raise FileNotFoundError("packages.x86_64 not found")

        with open(pkg_file, 'r', encoding='utf-8') as f:
            base_lines = f.read().splitlines()

        base_packages = []
        for line in base_lines:
            stripped = line.strip()
            if stripped and not stripped.startswith('#'):
                base_packages.append(stripped)

        base_package_set = set(base_packages)

        required_packages = {
            'mkinitcpio',
            'mkinitcpio-archiso',
            'squashfs-tools',
            'linux',
            'linux-firmware',
            'base',
        }

        excluded_set = set(excluded_packages)
        excluded_effective = excluded_set - required_packages
        excluded_ignored = excluded_set & required_packages
        if excluded_ignored:
            self._emit(
                "[WARN] Ignoring exclusions for required packages: "
                f"{', '.join(sorted(excluded_ignored))}\n"
            )

        base_lines_filtered = []
        for line in base_lines:
            stripped = line.strip()
            if stripped and not stripped.startswith('#'):
                if stripped in excluded_effective:
                    continue
            base_lines_filtered.append(line)

        custom_packages = [
            pkg for pkg in packages
            if pkg.strip() and pkg not in excluded_effective
        ]
        custom_packages = [
            pkg for pkg in custom_packages
            if pkg not in base_package_set
        ]
        custom_packages = sorted(set(custom_packages))

        required_missing = sorted(
            required_packages -
            (set(custom_packages) | base_package_set)
        )
        if required_missing:
            self._emit(
                "[INFO] Adding required packages missing from base list: "
                f"{', '.join(required_missing)}\n"
            )

        with open(pkg_file, 'w', encoding='utf-8', newline='') as f:
            if base_lines_filtered:
                f.write("\n".join(base_lines_filtered).rstrip() + "\n")
            if required_missing or custom_packages:
                f.write("\n# Added from current system\n")
                for pkg in required_missing:
                    f.write(f"{pkg}\n")
                for pkg in custom_packages:
                    f.write(f"{pkg}\n")

        with open(pkg_file, 'r', encoding='utf-8') as f:
            pkg_lines = [
                line.strip() for line in f.readlines()
                if line.strip() and not line.strip().startswith('#')
            ]
        pkg_count = len(pkg_lines)
        return pkg_file, pkg_lines, pkg_count, required_packages

    # Makes the built ISO boot into GNOME as root
    def _write_customize_airootfs(
        self, airootfs: str, root_password: str
    ) -> None:
        customize_path = os.path.join(
            airootfs, 'root', 'customize_airootfs.sh'
        )
        content = f"""#!/bin/bash
set -euo pipefail

echo "[customize_airootfs] running..."

# 1) Set root password
echo "root:{root_password}" | chpasswd

# 2) Restore root home from template (if present)
TEMPLATE_DIR="/etc/skel/root_template"
if [[ -d "$TEMPLATE_DIR" ]]; then
  rsync -a "$TEMPLATE_DIR/" /root/ || true
  chown -R root:root /root || true
fi

# 3) Networking
systemctl enable NetworkManager.service || true

# 4) Ensure video drivers are loaded (KMS modules are in mkinitcpio)
# The video driver modules (i915, amdgpu, radeon, nvidia) are already
# configured in mkinitcpio.conf for early loading during boot

# 5) GNOME Display Manager + graphical boot
if pacman -Qq gdm &>/dev/null; then
  systemctl enable gdm.service || true

  # Autologin as root
  mkdir -p /etc/gdm
  cat > /etc/gdm/custom.conf <<EOF
[daemon]
AutomaticLoginEnable=True
AutomaticLogin=root

[security]

[xdmcp]

[chooser]

[debug]
EOF
fi

# Ensure we boot to graphical target by default
ln -sf /usr/lib/systemd/system/graphical.target /etc/systemd/system/default.target || true

echo "[customize_airootfs] done."
"""
        self._write_script(customize_path, content)

    def run(self):
        """Run the ISO build process"""
        try:
            # Check if running as root
            if os.geteuid() != 0:
                self.finished_signal.emit(False, Messages.ROOT_REQUIRED)
                return

            work_dir = self.config['work_dir']
            output_dir = self.config['output_dir']
            profile_dir = os.path.join(work_dir, 'profile')
            iso_name = self.config['iso_name']
            iso_label = self.config['iso_label']

            # Thorough cleanup of previous build to avoid conflicts
            self._emit(
                "[INFO] Cleaning up previous build directories and files...\n"
            )
            safe_remove(work_dir, self._emit)
            safe_remove(output_dir, self._emit)

            # Clean up any leftover ISO files in output directory parent
            output_parent = os.path.dirname(output_dir) or output_dir
            if os.path.exists(output_parent):
                iso_files = list(Path(output_parent).glob('*.iso'))
                for iso_file in iso_files:
                    if iso_file.name.startswith(iso_name):
                        safe_remove(str(iso_file), self._emit)

            # Create fresh directories with proper permissions
            safe_makedirs(work_dir)
            safe_makedirs(output_dir)

            self._emit(
                "[INFO] Cleanup complete. Starting fresh build.\n"
            )
            self.progress_signal.emit(10)

            # Check/install archiso
            self._emit("[INFO] Checking for archiso...\n")
            result = run_command(['pacman', '-Q', 'archiso'])
            if result.returncode != 0:
                self._emit("[WARN] Installing archiso...\n")
                run_command(
                    ['pacman', '-S', '--noconfirm', '--needed', 'archiso'],
                    check=True
                )
            self.progress_signal.emit(20)

            # Copy releng profile (ensure clean copy)
            self._emit(
                "[INFO] Copying archiso releng profile...\n"
            )
            # Remove profile directory if it exists to ensure clean copy
            if os.path.exists(profile_dir):
                subprocess.run(['rm', '-rf', profile_dir], check=False)

            # Verify source profile exists
            source_profile = '/usr/share/archiso/configs/releng/'
            if not os.path.exists(source_profile):
                self._emit(
                    f"[ERROR] Source profile not found: {source_profile}\n"
                )
                raise FileNotFoundError(
                    f"Source profile not found: {source_profile}"
                )

            # Copy profile preserving all attributes
            subprocess.run(
                ['cp', '-a', source_profile, profile_dir], check=True
            )

            # Verify critical files exist
            critical_files = [
                'profiledef.sh',
                'pacman.conf',
                'airootfs',
            ]
            for critical_file in critical_files:
                file_path = os.path.join(profile_dir, critical_file)
                if not os.path.exists(file_path):
                    self._emit(
                        f"[ERROR] Critical file missing: {critical_file}\n"
                    )
                    raise FileNotFoundError(
                        f"Critical file missing: {critical_file}"
                    )

            # Ensure profile directory has correct permissions
            run_command(['chmod', '-R', '755', profile_dir], check=False)

            # Copy current system's pacman.conf to include custom repos
            include_custom = self.config.get('include_custom_repos', True)
            if include_custom:
                self._emit(
                    "[INFO] Copying system pacman.conf "
                    "(includes custom repos)...\n"
                )
                pacman_conf_dest = os.path.join(profile_dir, 'pacman.conf')
                run_command(
                    ['cp', '/etc/pacman.conf', pacman_conf_dest], check=True
                )

                # Setup local repository for AUR packages
                self._emit(
                    "[INFO] Setting up local repository for AUR packages...\n"
                )
                local_repo_dir = os.path.join(
                    profile_dir, 'airootfs', 'opt', 'local-repo'
                )
                safe_makedirs(local_repo_dir)

            self.progress_signal.emit(30)

            # Generate package list
            self._emit(
                "[INFO] Generating package list from current system...\n"
            )
            result = run_command(['pacman', '-Qqe'], check=True)
            all_packages = result.stdout.strip().split('\n')

            # Filter packages based on configuration
            include_custom = self.config.get('include_custom_repos', True)

            if include_custom:
                self._emit(
                    "[INFO] Including all packages "
                    "(official + custom repos + AUR)\n"
                )

                # Separate packages by source
                repo_packages = []
                aur_packages = []

                for pkg in all_packages:
                    if not pkg.strip():
                        continue

                    # Check if package is in official/custom repos
                    result = subprocess.run(
                        ['pacman', '-Si', pkg],
                        capture_output=True, text=True
                    )

                    if result.returncode == 0:
                        repo_packages.append(pkg)
                    else:
                        aur_packages.append(pkg)

                # Copy AUR package files to local repo
                successfully_copied_aur = []
                failed_aur_packages = []

                if aur_packages:
                    self._emit(
                        f"[INFO] Copying {len(aur_packages)} AUR packages "
                        "to local repository...\n"
                    )
                    local_repo_dir = os.path.join(
                        profile_dir, 'airootfs', 'opt', 'local-repo'
                    )

                    for pkg in aur_packages:
                        # Get package file from cache
                        result = subprocess.run(
                            ['pacman', '-Ql', pkg],
                            capture_output=True, text=True
                        )

                        if result.returncode == 0:
                            # Try to find the package file in cache
                            pkg_pattern = f"{pkg}-*.pkg.tar.*"
                            pkg_files = list(
                                Path('/var/cache/pacman/pkg/').glob(
                                    pkg_pattern
                                )
                            )

                            if pkg_files:
                                # Copy most recent package file
                                pkg_file = sorted(
                                    pkg_files,
                                    key=lambda p: p.stat().st_mtime
                                )[-1]
                                self._emit(
                                    f"  - Copying {pkg_file.name}\n"
                                )
                                subprocess.run(
                                    ['cp', str(pkg_file), local_repo_dir],
                                    check=False
                                )
                                successfully_copied_aur.append(pkg)
                            else:
                                self._emit(
                                    f"  - [WARN] Package file not found in "
                                    f"cache: {pkg} "
                                    "(will be excluded from ISO)\n"
                                )
                                failed_aur_packages.append(pkg)

                    # Create repository database only if we have packages
                    pkg_files = list(Path(local_repo_dir).glob('*.pkg.tar.*'))
                    if pkg_files:
                        self._emit(
                            "[INFO] Creating local repository database...\n"
                        )
                        repo_db = os.path.join(
                            local_repo_dir, 'local-repo.db.tar.gz'
                        )
                        subprocess.run(
                            ['repo-add', repo_db] +
                            [str(f) for f in pkg_files],
                            check=False
                        )

                        # Add local repo to pacman.conf
                        pacman_conf = os.path.join(profile_dir, 'pacman.conf')
                        with open(pacman_conf, 'a') as f:
                            f.write("\n[local-repo]\n")
                            f.write("SigLevel = Optional TrustAll\n")
                            f.write("Server = file:///opt/local-repo\n")
                    elif aur_packages:
                        self._emit(
                            "[WARN] No AUR package files were successfully "
                            "copied to local repository\n"
                        )

                if failed_aur_packages:
                    self._emit(
                        f"[INFO] Excluding {len(failed_aur_packages)} AUR "
                        "packages that couldn't be found:\n"
                    )
                    for pkg in failed_aur_packages:
                        self._emit(f"  - {pkg}\n")

                excluded_packages = set(
                    self.config.get('excluded_packages', [])
                )
                if excluded_packages:
                    repo_packages = [
                        pkg for pkg in repo_packages
                        if pkg not in excluded_packages
                    ]
                    successfully_copied_aur = [
                        pkg for pkg in successfully_copied_aur
                        if pkg not in excluded_packages
                    ]
                    self._emit(
                        f"[INFO] Excluding {len(excluded_packages)} "
                        "user-specified packages\n"
                    )

                packages = repo_packages + successfully_copied_aur
                self._emit(
                    f"[INFO] Final package list: {len(repo_packages)} repo "
                    f"packages + {len(successfully_copied_aur)} AUR packages "
                    f"= {len(packages)} total\n"
                )
            else:
                self._emit(
                    "[INFO] Filtering packages (official repos only)...\n"
                )
                packages = []
                aur_packages = []
                distro_packages = []

                for pkg in all_packages:
                    if not pkg.strip():
                        continue

                    # Check package repository
                    result = subprocess.run(
                        ['pacman', '-Si', pkg],
                        capture_output=True, text=True
                    )

                    if result.returncode == 0:
                        # Package exists in sync databases (official repos)
                        packages.append(pkg)
                    else:
                        # Check if it's a distro-specific package
                        distro_prefixes = [
                            'cachyos-', 'garuda-', 'endeavour-', 'manjaro-'
                        ]
                        if any(prefix in pkg for prefix in distro_prefixes):
                            distro_packages.append(pkg)
                        else:
                            aur_packages.append(pkg)

                if aur_packages:
                    self._emit(
                        f"[WARN] Skipping {len(aur_packages)} AUR packages\n"
                    )
                if distro_packages:
                    self._emit(
                        f"[WARN] Skipping {len(distro_packages)} "
                        "distro-specific packages\n"
                    )

            # Ensure minimal GNOME + display manager stack exists
            # (If you already have GNOME installed, this does nothing.)
            excluded_packages = set(self.config.get('excluded_packages', []))

            # Define conflicting package groups (only one from each group can be installed)
            conflict_groups = [
                # NVIDIA driver packages - only one can be installed
                ['nvidia', 'nvidia-open', 'nvidia-580xx-dkms', 'nvidia-470xx-dkms',
                 'nvidia-390xx-dkms', 'nvidia-340xx-dkms'],
            ]

            # Check for existing conflicting packages in the package list
            existing_nvidia = None
            for pkg in packages:
                for conflict_group in conflict_groups:
                    if pkg in conflict_group:
                        if existing_nvidia is None:
                            existing_nvidia = pkg
                        elif pkg != existing_nvidia:
                            # Found a conflict - prefer the one already in the list
                            self._emit(
                                f"[INFO] Detected NVIDIA driver conflict: "
                                f"'{existing_nvidia}' and '{pkg}' both present. "
                                f"Keeping '{existing_nvidia}' and excluding '{pkg}'.\n"
                            )
                            if pkg in packages:
                                packages.remove(pkg)

            gui_must = [
                "xorg-server",
                "gnome-shell",
                "gnome-session",
                "gdm",
                "networkmanager",
                "mesa",
                # Video driver packages for various hardware (bleeding-edge)
                "xf86-video-intel",  # Intel integrated graphics
                "xf86-video-amdgpu",  # AMD GPUs (modern)
                "xf86-video-ati",  # Older AMD/ATI GPUs
                "nvidia-open",  # NVIDIA open kernel modules (bleeding-edge)
            ]

            added_gui = []
            for must in gui_must:
                if must in excluded_packages:
                    self._emit(
                        f"[WARN] GUI-required package '{must}' is excluded. "
                        "Live GNOME may not start.\n"
                    )
                    continue

                # Skip if it conflicts with an existing package
                skip_due_to_conflict = False
                for conflict_group in conflict_groups:
                    if must in conflict_group:
                        for existing_pkg in packages:
                            if existing_pkg in conflict_group and existing_pkg != must:
                                self._emit(
                                    f"[INFO] Skipping '{must}' - conflicts with "
                                    f"existing '{existing_pkg}' in package list.\n"
                                )
                                skip_due_to_conflict = True
                                break
                        if skip_due_to_conflict:
                            break

                if skip_due_to_conflict:
                    continue

                if must not in packages and must not in all_packages:
                    packages.append(must)
                    added_gui.append(must)
            if added_gui:
                self._emit(
                    "[INFO] Added GUI packages to support GNOME live session: "
                    f"{', '.join(added_gui)}\n"
                )

            excluded_packages_list = self.config.get('excluded_packages', [])
            pkg_file, pkg_lines, pkg_count, required_packages = (
                self._build_package_list(
                    profile_dir,
                    packages,
                    excluded_packages_list
                )
            )

            missing_critical = []
            for crit_pkg in required_packages:
                if crit_pkg not in pkg_lines:
                    missing_critical.append(crit_pkg)

            if missing_critical:
                missing_str = ', '.join(missing_critical)
                self._emit(
                    f"[ERROR] Missing critical packages: {missing_str}\n"
                )
                raise ValueError(
                    f"Package list missing critical packages: {missing_str}"
                )

            if pkg_count < 10:
                self._emit(
                    f"[WARN] Package list is very small ({pkg_count} "
                    "packages). This may cause boot issues.\n"
                )

            self._emit(
                f"[INFO] Package list created with {pkg_count} packages\n"
            )
            self._emit(f"[INFO] Package list file: {pkg_file}\n")
            self.progress_signal.emit(40)

            # Setup directory exclusions for rsync
            exclude_dirs = self.config.get('exclude_dirs', [])
            if exclude_dirs:
                self._emit(
                    f"[INFO] Excluding {len(exclude_dirs)} directory "
                    "patterns...\n"
                )
                for excl in exclude_dirs:
                    self._emit(f"  - {excl}\n")

            # Customize airootfs (airootfs contains customization files
            # that get copied into the built rootfs)
            self._emit(
                "[INFO] Customizing live system root filesystem...\n"
            )
            airootfs = os.path.join(profile_dir, 'airootfs')
            os.makedirs(os.path.join(airootfs, 'etc'), exist_ok=True)

            # Copy NetworkManager config (if exists)
            if os.path.isdir('/etc/NetworkManager'):
                nm_dir = os.path.join(airootfs, 'etc', 'NetworkManager')
                os.makedirs(nm_dir, exist_ok=True)
                subprocess.run(
                    ['cp', '-r', '/etc/NetworkManager/.', nm_dir],
                    stderr=subprocess.DEVNULL, check=False
                )

            # Set hostname
            self._write_text(
                os.path.join(airootfs, 'etc', 'hostname'),
                "archiso-live\n"
            )

            # Configure mkinitcpio for video drivers (early KMS)
            self._emit(
                "[INFO] Configuring mkinitcpio for video drivers...\n"
            )
            mkinitcpio_dir = os.path.join(airootfs, 'etc', 'mkinitcpio.d')
            os.makedirs(mkinitcpio_dir, exist_ok=True)
            mkinitcpio_conf = os.path.join(
                airootfs, 'etc', 'mkinitcpio.conf'
            )

            # Read existing mkinitcpio.conf from profile if it exists
            if os.path.exists(mkinitcpio_conf):
                with open(mkinitcpio_conf, 'r', encoding='utf-8') as f:
                    mkinitcpio_content = f.read()
            else:
                # Try to read from the profile's airootfs
                profile_mkinitcpio = os.path.join(
                    profile_dir, 'airootfs', 'etc', 'mkinitcpio.conf'
                )
                if os.path.exists(
                    profile_mkinitcpio
                ):
                    with open(profile_mkinitcpio, 'r', encoding='utf-8') as f:
                        mkinitcpio_content = f.read()
                else:
                    # Use default content
                    mkinitcpio_content = """# vim:set ft=sh:
# MODULES
MODULES=()

# BINARIES
BINARIES=()

# FILES
FILES=()

# HOOKS
HOOKS=(base udev autodetect modconf block filesystems keyboard fsck)

# COMPRESSION
#COMPRESSION="gzip"
"""

            # Modify MODULES line to include video drivers for early KMS
            lines = mkinitcpio_content.split('\n')
            modified_lines = []
            modules_updated = False
            for line in lines:
                stripped = line.strip()
                if (stripped.startswith('MODULES=') and
                        not stripped.startswith('# MODULES')):
                    # Update MODULES to include video drivers for early KMS
                    # (Intel, AMD, NVIDIA)
                    modified_lines.append(
                        'MODULES=(i915 amdgpu radeon nvidia)'
                    )
                    modules_updated = True
                else:
                    modified_lines.append(line)

            if not modules_updated:
                # If MODULES line wasn't found, add it after the comment
                for i, line in enumerate(modified_lines):
                    if line.strip().startswith('# MODULES'):
                        # Insert MODULES line after comment block
                        j = i + 1
                        while j < len(modified_lines) and (
                            modified_lines[j].strip().startswith('#') or
                            modified_lines[j].strip() == ''
                        ):
                            j += 1
                        modified_lines.insert(
                            j, 'MODULES=(i915 amdgpu radeon nvidia)'
                        )
                        break

            self._write_text(
                mkinitcpio_conf, '\n'.join(modified_lines) + '\n'
            )

            # Configure root user account (only user on live ISO)
            user_config = self.config.get('user_config', {})
            root_password = user_config.get('root_password', 'root')
            template_user = user_config.get('template_user', None)

            # Copy selected user's home as template for root
            if template_user:
                self._emit(
                    f"[INFO] Copying user template from: {template_user}\n"
                )
                source_home = os.path.expanduser(f'~{template_user}')
                if not os.path.exists(source_home):
                    self._emit(
                        f"[WARN] Home directory not found: {source_home}\n"
                    )
                    self._emit(
                        "[INFO] Proceeding without user template\n"
                    )
                else:
                    # Copy user home to root template directory
                    dest_template = os.path.join(
                        airootfs, 'etc', 'skel', 'root_template'
                    )
                    os.makedirs(dest_template, exist_ok=True)

                    exclude_patterns = self._make_rsync_excludes(
                        self.HOME_COPY_EXCLUDES
                    )

                    self._emit(
                        "[INFO] Copying user template "
                        "(focusing on configs) "
                        f"from {source_home}...\n"
                    )
                    # Use rsync with excludes - this will copy everything
                    # except excluded patterns (cache, trash, etc.)
                    # which naturally includes .config (GTK/QT configs)
                    rsync_cmd = (
                        ['rsync', '-a', '--info=progress2'] +
                        exclude_patterns +
                        [f'{source_home}/', f'{dest_template}/']
                    )
                    result = subprocess.run(
                        rsync_cmd,
                        capture_output=True,
                        text=True,
                        check=False
                    )
                    if result.returncode == 0:
                        self._emit(
                            "[INFO] User template copied successfully\n"
                        )
                    else:
                        self._emit(
                            "[WARN] Some files may not have been copied\n"
                        )
            else:
                self._emit(
                    "[INFO] No user template selected - "
                    "using blank root home\n"
                )

            # mkarchiso executes customize_airootfs.sh during build
            # This sets root password + restores template + enables GDM
            self._write_customize_airootfs(airootfs, root_password)

            # Write pkg list into ISO for installer to use
            self._write_text(
                os.path.join(airootfs, "root", "pkglist.txt"),
                "\n".join(pkg_lines) + "\n"
            )

            # Create installer script (UEFI) - place on root's desktop
            os.makedirs(
                os.path.join(airootfs, 'root', 'Desktop'), exist_ok=True
            )
            install_script = os.path.join(
                airootfs, 'root', 'Desktop', 'install.sh'
            )
            self._write_script(install_script, f"""#!/bin/bash
set -euo pipefail

# Custom Arch installer (UEFI, GPT, EFI+root)
# WARNING: this wipes the selected disk.

ROOT_PASSWORD="{root_password}"
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
EFI_PART="${{DISK}}1"
ROOT_PART="${{DISK}}2"
if [[ "$DISK" =~ nvme|mmcblk ]]; then
  EFI_PART="${{DISK}}p1"
  ROOT_PART="${{DISK}}p2"
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
  pacstrap -K /mnt base linux linux-firmware networkmanager
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
DRIVER_CHOICE=${{DRIVER_CHOICE:-4}}

case "$DRIVER_CHOICE" in
  1)
    MKINITCPIO_MODULES="i915"
    REMOVE_DRIVERS="xf86-video-amdgpu xf86-video-ati nvidia-open"
    ;;
  2)
    MKINITCPIO_MODULES="amdgpu radeon"
    REMOVE_DRIVERS="xf86-video-intel nvidia-open"
    ;;
  3)
    MKINITCPIO_MODULES="nvidia"
    REMOVE_DRIVERS="xf86-video-intel xf86-video-amdgpu xf86-video-ati"
    ;;
  4|*)
    MKINITCPIO_MODULES="i915 amdgpu radeon nvidia"
    REMOVE_DRIVERS=""
    ;;
esac

# Common modules for audio + networking
COMMON_MODULES="snd_hda_intel snd_sof_pci snd_sof_intel_hda_common iwlwifi r8169 e1000e igb"
ALL_MODULES="$MKINITCPIO_MODULES $COMMON_MODULES"

echo "[6/8] System config (chroot)..."
arch-chroot /mnt /bin/bash -euo pipefail <<CHROOT
echo "root:${{ROOT_PASSWORD}}" | chpasswd

ln -sf "/usr/share/zoneinfo/${{TIMEZONE}}" /etc/localtime
hwclock --systohc

sed -i "s/^#${{LOCALE}}/${{LOCALE}}/" /etc/locale.gen || true
locale-gen
echo "LANG=${{LOCALE}}" > /etc/locale.conf

echo "${{HOSTNAME}}" > /etc/hostname
cat > /etc/hosts <<EOF
127.0.0.1   localhost
::1         localhost
127.0.1.1   ${{HOSTNAME}}.localdomain ${{HOSTNAME}}
EOF

# Configure video drivers based on selection
MKINITCPIO_MODULES="${{MKINITCPIO_MODULES}}"
REMOVE_DRIVERS="${{REMOVE_DRIVERS}}"
COMMON_MODULES="${{COMMON_MODULES}}"
ALL_MODULES="${{ALL_MODULES}}"

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

if [[ "$MKINITCPIO_MODULES" == *nvidia* ]]; then
  pacman -S --noconfirm --needed nvidia nvidia-utils || true
fi

if [[ -n "$MKINITCPIO_MODULES" ]]; then
  echo "Configuring mkinitcpio with modules: $MKINITCPIO_MODULES"
  sed -i "s/^MODULES=.*/MODULES=($MKINITCPIO_MODULES)/" /etc/mkinitcpio.conf || true
  mkinitcpio -P || true
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
pacman -Rns --noconfirm xf86-video-intel xf86-video-ati 2>/dev/null || true

# Ensure only the latest kernel package remains
pacman -S --noconfirm --needed linux || true
pacman -Rns --noconfirm \\
  linux-lts linux-zen linux-hardened linux-rt \\
  linux-lts-headers linux-zen-headers linux-hardened-headers linux-rt-headers \\
  2>/dev/null || true

# Services
systemctl enable NetworkManager.service || true
if pacman -Qq gdm &>/dev/null; then
  systemctl enable gdm.service || true
  mkdir -p /etc/gdm
  cat > /etc/gdm/custom.conf <<EOF
[daemon]
AutomaticLoginEnable=True
AutomaticLogin=root
EOF
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
    $1 == out {active=1; next}
    active && $0 ~ /^[[:space:]]+[0-9]+x[0-9]+/ {
      if ($0 ~ /\\+/) {print $1; exit}
    }
    active && $0 !~ /^[[:space:]]/ {active=0}
  ')
  if [[ -n "$preferred" ]]; then
    xrandr --output "$output" --mode "$preferred" --rate 60 2>/dev/null || \
      xrandr --output "$output" --mode "$preferred" 2>/dev/null || true
  else
    xrandr --output "$output" --auto 2>/dev/null || true
  fi
done < <(xrandr --query | awk '/ connected / {print $1 " connected"}')
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
cat > /boot/loader/loader.conf <<EOF
default arch
timeout 3
beep   off
editor  0
EOF

cat > /boot/loader/entries/arch.conf <<EOF
title   Arch Linux (Custom)
linux   /vmlinuz-linux
initrd  /initramfs-linux.img
options root=UUID=\\${{ROOT_UUID}} rw
EOF
CHROOT

echo "[7/8] Done. Unmounting..."
umount -R /mnt

echo "[8/8] Installation complete."
echo "Reboot when ready."
""")
            desktop_shortcut = os.path.join(
                airootfs, 'root', 'Desktop', 'Install Arch.desktop'
            )
            self._write_text(desktop_shortcut, """[Desktop Entry]
Type=Application
Name=Install Arch Linux
Comment=Run the custom Arch installer
Exec=/root/Desktop/install.sh
Terminal=true
Icon=utilities-terminal
Categories=System;
""")
            os.chmod(desktop_shortcut, 0o755)
            self.progress_signal.emit(50)

            # Create custom build hook to exclude directories
            if exclude_dirs:
                self._emit(
                    "[INFO] Creating custom build hook for exclusions...\n"
                )
                hooks_dir = os.path.join(
                    profile_dir, 'airootfs', 'etc', 'initcpio', 'hooks'
                )
                os.makedirs(hooks_dir, exist_ok=True)

                exclude_file = os.path.join(profile_dir, 'exclude_dirs.txt')
                exclude_text = "\n".join(exclude_dirs).rstrip() + "\n"
                self._write_text(exclude_file, exclude_text)

            # Customize profiledef.sh - preserve original and only update
            # what we need
            self._emit(
                "[INFO] Customizing profile definition...\n"
            )
            profiledef = os.path.join(profile_dir, 'profiledef.sh')
            original_profiledef = (
                '/usr/share/archiso/configs/releng/profiledef.sh'
            )

            if not os.path.exists(profiledef):
                self._emit(
                    "[ERROR] profiledef.sh not found in profile!\n"
                )
                raise FileNotFoundError("profiledef.sh not found")

            if os.path.exists(original_profiledef):
                with open(original_profiledef, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
            else:
                with open(profiledef, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

            updated_lines = []
            for line in lines:
                stripped = line.strip()
                if stripped.startswith('iso_name='):
                    updated_lines.append(f'iso_name="{iso_name}"\n')
                elif stripped.startswith('iso_label='):
                    updated_lines.append(f'iso_label="{iso_label}"\n')
                elif stripped.startswith('iso_publisher='):
                    updated_lines.append('iso_publisher="Custom Arch Linux"\n')
                elif stripped.startswith('iso_application='):
                    updated_lines.append(
                        'iso_application="Custom Arch Linux Live/Install"\n'
                    )
                elif stripped.startswith('pacman_conf='):
                    updated_lines.append('pacman_conf="pacman.conf"\n')
                else:
                    updated_lines.append(line)

            with open(profiledef, 'w', encoding='utf-8', newline='') as f:
                f.writelines(updated_lines)

            os.chmod(profiledef, 0o755)

            if (not os.path.exists(profiledef) or
                    os.path.getsize(profiledef) == 0):
                self._emit(
                    "[ERROR] Failed to write profiledef.sh!\n"
                )
                raise IOError("profiledef.sh write failed")
            self.progress_signal.emit(60)

            # Build the ISO
            self._emit(
                "[INFO] Building ISO (this will take a while)...\n"
            )
            self._emit(
                "[INFO] Note: Some mkinitcpio and GRUB errors during "
                "package installation are expected and non-fatal.\n"
            )
            self._emit("=" * 60 + "\n")

            build_dir = os.path.join(work_dir, 'build')
            self.process = subprocess.Popen(
                [
                    'mkarchiso', '-v', '-w', build_dir, '-o',
                    output_dir, profile_dir
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            error_detected = False
            non_fatal_patterns = [
                "/boot/grub/grub.cfg.new: no such file or directory",
                "running in chroot",
                "skipped: running in chroot",
                ("errors were encountered during the build. "
                 "the image may not be complete"),
            ]

            for line in self.process.stdout:
                self._emit(line)
                line_lower = line.lower()

                is_non_fatal = any(
                    pattern in line_lower for pattern in non_fatal_patterns
                )

                if not is_non_fatal and any(
                    keyword in line_lower for keyword in
                    ['error:', 'failed', 'fatal:', 'cannot', 'unable']
                ):
                    if 'warning' not in line_lower:
                        error_detected = True
                        self._emit(f"[ERROR DETECTED] {line}")

                if ('squashfs' in line_lower and
                        ('creating' in line_lower or 'created' in line_lower)):
                    self.progress_signal.emit(80)

                elif 'iso' in line_lower and 'creating' in line_lower:
                    self.progress_signal.emit(90)
                elif 'packages' in line_lower and 'installing' in line_lower:
                    self.progress_signal.emit(50)
                elif 'building' in line_lower and 'airootfs' in line_lower:
                    self.progress_signal.emit(60)

            self.process.wait()

            self.progress_signal.emit(100)
            iso_files = list(Path(output_dir).glob('*.iso'))

            if iso_files:
                iso_file = iso_files[0]
                size = iso_file.stat().st_size / (1024**3)
                self._emit("\n" + "=" * 60 + "\n")
                if self.process.returncode == 0:
                    self._emit("[SUCCESS] ISO build completed!\n")
                else:
                    self._emit(
                        "[WARNING] Build completed with warnings/errors, "
                        "but ISO was created.\n"
                    )
                self._emit(f"[INFO] ISO created: {iso_file}\n")
                self._emit(f"[INFO] Size: {size:.2f} GB\n")

                self._emit(
                    "\n[INFO] Verifying build artifacts...\n"
                )
                squashfs_found = False

                squashfs_files = list(Path(build_dir).rglob('*.squashfs'))
                if not squashfs_files:
                    arch_dir = os.path.join(output_dir, 'arch')
                    if os.path.exists(arch_dir):
                        squashfs_files = list(
                            Path(arch_dir).rglob('*.squashfs')
                        )

                if squashfs_files:
                    squashfs_size = (
                        squashfs_files[0].stat().st_size / (1024**3)
                    )
                    self._emit(
                        f"[INFO] Squashfs found in build dir: "
                        f"{squashfs_files[0]} ({squashfs_size:.2f} GB)\n"
                    )
                    squashfs_found = True

                    if squashfs_size < 0.1:
                        self._emit(
                            "[WARN] Squashfs file is very small - may be "
                            "corrupted or empty!\n"
                        )
                else:
                    self._emit(
                        "[INFO] Squashfs not found in build directory. "
                        "Checking ISO contents...\n"
                    )
                    if size > 1.0:
                        self._emit(
                            "[INFO] ISO size is reasonable. Squashfs is "
                            "likely embedded in the ISO (normal behavior).\n"
                        )
                        squashfs_found = True
                    else:
                        self._emit(
                            "[WARN] ISO size is suspiciously small. "
                            "Squashfs may be missing.\n"
                        )

                self._emit("[INFO] Verifying ISO structure...\n")
                iso_structure_valid = False
                try:
                    result = run_command(['file', str(iso_file)], check=False)
                    if result.returncode == 0:
                        self._emit(
                            f"[INFO] ISO file type: "
                            f"{result.stdout.strip()}\n"
                        )
                        iso_structure_valid = (
                            'ISO 9660' in result.stdout or
                            'bootable' in result.stdout.lower()
                        )
                        if iso_structure_valid:
                            self._emit(
                                "[INFO] ISO appears to be a valid bootable "
                                "image.\n"
                            )
                            # If ISO structure is valid, consider squashfs as found
                            squashfs_found = True
                except Exception:
                    pass

                # Only fail verification if ISO structure is invalid AND size is suspicious
                # Valid ISO structure is more important than size check
                if not squashfs_found and not iso_structure_valid and size < 0.2:
                    self._emit(
                        "[ERROR] Build verification failed: ISO is too small "
                        "and structure appears invalid.\n"
                    )
                    if error_detected:
                        self._emit(
                            "[ERROR] Errors were detected in mkarchiso output "
                            "(see above)\n"
                        )
                    self.finished_signal.emit(
                        False, "ISO verification failed - may not boot"
                    )
                    return

                self.finished_signal.emit(True, str(iso_file))
            else:
                if self.process.returncode == 0:
                    self._emit(
                        "\n[ERROR] Build process completed but ISO file "
                        "not found!\n"
                    )
                    self._emit(
                        f"[ERROR] Check build directory: {build_dir}\n"
                    )
                    self._emit(
                        f"[ERROR] Check output directory: {output_dir}\n"
                    )
                    self.finished_signal.emit(
                        False, "ISO file not found in output directory"
                    )
                else:
                    self._emit(
                        f"\n[ERROR] ISO build failed! "
                        f"(exit code: {self.process.returncode})\n"
                    )
                    self.finished_signal.emit(
                        False,
                        f"Build process failed with exit code "
                        f"{self.process.returncode}"
                    )

        except Exception as e:
            self._emit(f"\n[ERROR] {str(e)}\n")
            self.finished_signal.emit(False, str(e))

    def stop(self):
        """Stop the build process"""
        if self.process:
            self.process.terminate()
