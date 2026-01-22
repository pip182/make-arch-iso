"""ISO Builder Thread"""
import os
import subprocess
from pathlib import Path
from typing import List, Tuple

from PyQt6.QtCore import QThread, pyqtSignal
from .constants import Messages
from .utils import run_command, safe_remove, safe_makedirs


class ISOBuilderThread(QThread):
    """Thread for building ISO without blocking the UI"""
    output_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(bool, str)

    # Default directories to exclude from ISO (temp/cache files)
    DEFAULT_EXCLUDE_DIRS = [
        # -----------------------------
        # Cache directories (general)
        # -----------------------------
        '.cache',
        'cache',
        '.thumbnails',
        '.thumbs',

        # Application cache subfolders
        '.cache/spotify',

        # Trash
        '.local/share/Trash',

        # ---------------------------------
        # User folders (potentially large)
        # ---------------------------------
        'Documents',
        'Downloads',
        'Music',
        'Pictures',
        'Public',
        'Templates',
        'Videos',

        # ---------------------------------
        # Browser caches and profiles
        # ---------------------------------
        # Firefox
        '.mozilla/firefox/*/Cache',
        '.mozilla/firefox/*/Code Cache',
        '.mozilla/firefox/*/cache',
        '.mozilla/firefox/*/cache2',
        '.mozilla/firefox/*/startupCache',

        # Chrome/Chromium, Brave, Vivaldi, etc.
        '.config/google-chrome/*/Cache',
        '.config/google-chrome/*/OptGuideOnDeviceModel',
        '.config/google-chrome/*/WasmTtsEngine',
        '.config/google-chrome/*/Safe Browsing',
        '.config/google-chrome/*/cache',
        '.config/google-chrome/*/component_crx_cache',
        '.config/google-chrome/*/optimization_guide_model_store',

        '.config/chromium/*/Cache',
        '.config/chromium/*/OptGuideOnDeviceModel',
        '.config/chromium/*/cache',
        '.config/chromium/*/optimization_guide_model_store',

        '.config/BraveSoftware/*/Cache',
        '.config/BraveSoftware/*/OptGuideOnDeviceModel',
        '.config/BraveSoftware/*/cache',

        '.config/microsoft-edge/*/Cache',
        '.config/microsoft-edge/*/cache',
        '.config/opera/*/Cache',
        '.config/opera/*/cache',
        '.config/vivaldi/*/Cache',
        '.config/vivaldi/*/cache',
        '.config/torbrowser',

        # -------------------------------
        # Messaging/communication apps
        # -------------------------------
        '.discord',
        '.local/share/TelegramDesktop',
        '.thunderbird',
        '.config/Element',
        '.config/Signal',
        '.config/discord',
        '.config/slack',
        '.config/telegram-desktop',

        # -----------------------------------------
        # Snap/containers/virtualization/VM config
        # -----------------------------------------
        '.VirtualBox',
        '.docker',
        '.kube',
        '.lxc',
        '.local/share/lxc',
        '.snap',
        '.vagrant',
        'VirtualBox VMs',
        'docker',
        'snap',

        # -------------------------------
        # Temp directories
        # -------------------------------
        '.temp',
        '.tmp',
        'temp',
        'tmp',

        # -------------------------------------------------
        # Build artifacts/directories, development caches
        # -------------------------------------------------
        '.PyCharm*',
        '.WebStorm*',
        '.build',
        '.coverage',
        '.eggs',
        '.env',
        '.idea',
        '.pytest_cache',
        '.sublime-*',
        '.tox',
        '__pycache__',
        'build',
        'dist',
        'env',
        'htmlcov',
        'node_modules',
        'target',
        'venv',
        '*.egg-info',
        '*.lock',
        '*.swp',
        '*.swo',
        '*.swn',
        '*~',
        '.viminfo',
        '.vim',
        '.gitconfig',
        '.IntelliJIdea*',
        '.PhpStorm*',
        '.RubyMine*',
        '.AndroidStudio*',
        '.CLion*',
        '.vscode',
        '.vs',
        '.emacs',
        '.emacs.d',
        '.local/share/nvim',
        '.config/nvim',
        '.atom',
        '.venv',

        # ------------------------------------------
        # App/editor/config data (large, opt-in)
        # ------------------------------------------
        '.config/Antigravity',
        '.config/Code',
        '.config/Code - OSS',
        '.config/Cursor',
        '.config/Electron',
        '.config/GIMP',
        '.config/RedisInsight',
        '.config/Upscayl',
        '.config/gmic',
        '.config/libreoffice',
        '.config/unity3d',
        '.local/share/Colossal Order',
        '.local/share/DBeaverData',
        '.local/share/GitKrakenCLI',
        '.local/share/Paradox Interactive',

        # -------------------------------
        # Cloud sync and backup folders
        # -------------------------------
        '.dropbox',
        '.nextcloud',
        '.nextcloud-client',

        # -------------------------------
        # Media players and video calls
        # -------------------------------
        '.config/spotify',
        '.config/zoom',
        '.zoom',

        # ---------------
        # Log files
        # ---------------
        '*.log',
        '.logs',

        # ---------------------------------
        # Locks, backup, and recovery files
        # ---------------------------------
        '*.bak',
        '*.backup',
        '*.lock',
        '*.orig',
        '.lock',
        '.recovery',

        # ---------------------------------
        # System/OS-specific files
        # ---------------------------------
        '.DS_Store',
        '.Trash-*',
        '.Xauthority',
        'Thumbs.db',

        # ---------------------------------------------------------------------------
        # Database/data store directories (user or system, large data, likely omitted)
        # ---------------------------------------------------------------------------
        'cassandra',
        'couchdb',
        'influxdb',
        'mariadb',
        'mongodb',
        'mysql',
        'postgres',
        'postgresql',
        'redis',
        '.cassandra',
        '.couchdb',
        '.influxdb',
        '.mariadb',
        '.mongodb',
        '.mysql',
        '.postgres',
        '.postgresql',
        '.redis',
        '.sqlite',

        # Database files
        '*.db',
        '*.db_backup',
        '*.dump',
        '*.sql',
        '*.sql.gz',
        '*.sqlite',
        '*.sqlite3',

        # -----------------
        # System database directories (absolute paths)
        # -----------------
        '/var/lib/cassandra',
        '/var/lib/couchdb',
        '/var/lib/influxdb',
        '/var/lib/mariadb',
        '/var/lib/mongodb',
        '/var/lib/mysql',
        '/var/lib/postgres',
        '/var/lib/postgresql',
        '/var/lib/redis',

        # -----------------------------------------
        # Package manager caches
        # -----------------------------------------
        '.cargo/git',
        '.cargo/registry',
        '.composer',
        '.gem',
        '.gradle',
        '.m2',
        '.npm',
        '.nuget',
        '.pip',
        '.yarn',
        '.yarn/cache',
        'go/pkg',
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
        # -----------------------------
        # Cache directories (general)
        # -----------------------------
        '.cache',
        '.cache/*',
        '.thumbnails',
        '.thumb',
        '.thumbs',
        '.local/share/Trash',

        # -------------------------------
        # Browser caches and profiles
        # -------------------------------
        # Firefox
        '.mozilla/firefox/*/Cache',
        '.mozilla/firefox/*/Code Cache',
        '.mozilla/firefox/*/cache',
        '.mozilla/firefox/*/cache2',
        '.mozilla/firefox/*/startupCache',

        # Chrome/Chromium, Brave, Vivaldi, etc.
        '.config/google-chrome/*/Cache',
        '.config/google-chrome/*/OptGuideOnDeviceModel',
        '.config/google-chrome/*/Safe Browsing',
        '.config/google-chrome/*/WasmTtsEngine',
        '.config/google-chrome/*/cache',
        '.config/google-chrome/*/component_crx_cache',
        '.config/google-chrome/*/optimization_guide_model_store',

        '.config/chromium/*/Cache',
        '.config/chromium/*/OptGuideOnDeviceModel',
        '.config/chromium/*/cache',
        '.config/chromium/*/optimization_guide_model_store',

        '.config/BraveSoftware/*/Cache',
        '.config/BraveSoftware/*/OptGuideOnDeviceModel',
        '.config/BraveSoftware/*/cache',

        '.config/microsoft-edge/*/Cache',
        '.config/microsoft-edge/*/cache',

        '.config/opera/*/Cache',
        '.config/opera/*/cache',

        '.config/vivaldi/*/Cache',
        '.config/vivaldi/*/cache',

        '.config/torbrowser',

        # -------------------------------
        # Application caches (large)
        # -------------------------------
        '.cache/BraveSoftware',
        '.cache/Code',
        '.cache/Cursor',
        '.cache/chromium',
        '.cache/electron',
        '.cache/gnome-software',
        '.cache/google-chrome',
        '.cache/ms-playwright-go',
        '.cache/mozilla',
        '.cache/node-gyp',
        '.cache/npm',
        '.cache/nvidia',
        '.cache/pacman',
        '.cache/pamac',
        '.cache/paru',
        '.cache/pip',
        '.cache/yarn',
        '.cache/yay',

        # -------------------------------
        # Temp directories
        # -------------------------------
        '.temp',
        '.tmp',
        'Downloads',
        'temp',
        'tmp',

        # -----------------------------------------
        # Package manager caches
        # -----------------------------------------
        '.cargo/git',
        '.cargo/registry',
        '.composer',
        '.gem',
        '.gradle',
        '.m2',
        '.npm',
        '.nuget',
        '.pip',
        '.yarn',
        '.yarn/cache',
        'go/pkg',

        # -------------------------------------------------
        # Build artifacts/directories, development caches
        # -------------------------------------------------
        '.PyCharm*',
        '.WebStorm*',
        '.build',
        '.coverage',
        '.eggs',
        '.env',
        '.env/*',
        '.idea',
        '.pytest_cache',
        '.sublime-*',
        '.tox',
        '__pycache__',
        'build',
        'dist',
        'env',
        'htmlcov',
        'node_modules',
        'target',
        'venv',
        '.venv',
        '.venv/*',
        '*.egg-info',
        '*.lock',
        '*.pyc',
        '*.pyo',
        '*.swp',
        '*.swo',
        '*.swn',
        '*~',
        '.vim',
        '.viminfo',
        '.IntelliJIdea*',
        '.PhpStorm*',
        '.RubyMine*',
        '.AndroidStudio*',
        '.CLion*',
        '.vscode',
        '.vs',
        '.emacs',
        '.emacs.d',
        '.local/share/nvim',
        '.config/nvim',
        '.atom',
        '.gitconfig',

        # ------------------------------------------
        # App/editor/config data (large, opt-in)
        # ------------------------------------------
        '.config/Antigravity',
        '.config/Code',
        '.config/Code - OSS',
        '.config/Cursor',
        '.config/Electron',
        '.config/GIMP',
        '.config/RedisInsight',
        '.config/Upscayl',
        '.config/gmic',
        '.config/libreoffice',
        '.config/unity3d',
        '.local/share/Colossal Order',
        '.local/share/DBeaverData',
        '.local/share/GitKrakenCLI',
        '.local/share/Paradox Interactive',

        # -------------------------------
        # Messaging/communication apps
        # -------------------------------
        '.discord',
        '.local/share/TelegramDesktop',
        '.thunderbird',
        '.config/Element',
        '.config/Signal',
        '.config/discord',
        '.config/slack',
        '.config/telegram-desktop',

        # -----------------------------------------
        # Snap/containers/virtualization/VM config
        # -----------------------------------------
        '.VirtualBox',
        '.docker',
        '.kube',
        '.lxc',
        '.local/share/containers',
        '.local/share/docker',
        '.local/share/libvirt',
        '.local/share/lxc',
        '.local/share/podman',
        '.snap',
        '.vagrant',
        'VirtualBox VMs',
        'docker',
        'snap',

        # -------------------------------
        # Cloud sync and backup folders
        # -------------------------------
        '.dropbox',
        '.nextcloud',
        '.nextcloud-client',

        # -------------------------------
        # Media players and video calls
        # -------------------------------
        '.config/spotify',
        '.cache/spotify',
        '.config/zoom',
        '.zoom',

        # -------------------------------
        # Flatpak/Snap application data
        # -------------------------------
        '.local/share/applications',
        '.local/share/flatpak',
        '.local/share/runtime',
        '.steam',
        '.local/share/Steam',
        '.local/share/lutris',
        '.wine',
        '.var',

        # ---------------------------------------------------------------------------
        # Database/data store directories (large data, likely omitted)
        # ---------------------------------------------------------------------------
        'cassandra',
        'couchdb',
        'influxdb',
        'mariadb',
        'mongodb',
        'mysql',
        'postgres',
        'postgresql',
        'redis',
        '.cassandra',
        '.couchdb',
        '.influxdb',
        '.mariadb',
        '.mongodb',
        '.mysql',
        '.postgres',
        '.postgresql',
        '.redis',
        '.sqlite',

        # Database files
        '*.db',
        '*.db_backup',
        '*.dump',
        '*.sql',
        '*.sql.gz',
        '*.sqlite',
        '*.sqlite3',

        # ---------------
        # Log files
        # ---------------
        '*.log',
        '*.log.*',
        '.logs',

        # ---------------------------------
        # Locks, backup, and recovery files
        # ---------------------------------
        '*.bak',
        '*.backup',
        '*.lock',
        '*.orig',
        '.lock',
        '.recovery',

        # ---------------------------------
        # System/OS-specific files
        # ---------------------------------
        '.DS_Store',
        '.Trash-*',
        '.Xauthority',
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

    def _get_scripts_dir(self) -> str:
        """Get the path to the scripts directory"""
        # Scripts directory is in the project root, relative to this file
        # __file__ is at make_arch_iso/builder.py, need to go up 2 levels to project root
        scripts_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'scripts'
        )
        return scripts_dir

    def _load_script_template(self, script_name: str) -> str:
        """Load a script template from the scripts directory"""
        scripts_dir = self._get_scripts_dir()
        script_path = os.path.join(scripts_dir, script_name)
        if not os.path.exists(script_path):
            raise FileNotFoundError(
                f"Script template not found: {script_path}"
            )
        with open(script_path, 'r', encoding='utf-8') as f:
            return f.read()

    def _template_replace(self, content: str, replacements: dict) -> str:
        """Replace template placeholders in content"""
        result = content
        for key, value in replacements.items():
            result = result.replace(f'{{{key}}}', str(value))
        return result

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

        # Get CachyOS kernel info from config if available
        is_cachyos = getattr(self, '_is_cachyos', False)
        cachyos_kernel = getattr(self, '_cachyos_kernel', None)

        required_packages = {
            'mkinitcpio',
            'mkinitcpio-archiso',
            'squashfs-tools',
            'linux' if not is_cachyos else (cachyos_kernel or 'linux-cachyos'),
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

    # Makes the built ISO boot into GNOME with configured user
    def _write_customize_airootfs(
        self, airootfs: str, root_password: str, username: str = None,
        user_password: str = None, user_sudo: bool = True,
        template_user: str = None
    ) -> None:
        customize_path = os.path.join(
            airootfs, 'root', 'customize_airootfs.sh'
        )
        # Load template from scripts directory
        content = self._load_script_template('customize_airootfs.sh')
        # Replace template placeholders
        content = self._template_replace(content, {
            'ROOT_PASSWORD': root_password,
            'USERNAME': username or '',
            'USER_PASSWORD': user_password or '',
            'USER_SUDO': 'true' if user_sudo else 'false',
            'TEMPLATE_USER': template_user or ''
        })
        self._write_script(customize_path, content)

    def run(self):
        """Run the ISO build process"""
        try:
            # Check if running as root
            if os.geteuid() != 0:
                self.finished_signal.emit(False, Messages.ROOT_REQUIRED)
                return

            # Detect CachyOS and kernel variant
            self._is_cachyos = False
            self._cachyos_kernel = None
            result = run_command(['pacman', '-Q'], check=False)
            if result.returncode == 0:
                installed_packages = result.stdout
                # Check for CachyOS kernel packages (linux-cachyos, linux-cachyos-bore, etc.)
                cachyos_kernel_patterns = [
                    'linux-cachyos ',  # Default CachyOS kernel
                    'linux-cachyos-bore ',
                    'linux-cachyos-bmq ',
                    'linux-cachyos-deckify ',
                    'linux-cachyos-eevdf ',
                    'linux-cachyos-lts ',
                    'linux-cachyos-hardened ',
                    'linux-cachyos-rc ',
                    'linux-cachyos-server ',
                    'linux-cachyos-rt-bore ',
                ]
                for pattern in cachyos_kernel_patterns:
                    if pattern in installed_packages:
                        # Extract kernel name (remove version)
                        kernel_line = [p for p in installed_packages.split('\n') if pattern.strip() in p]
                        if kernel_line:
                            self._cachyos_kernel = kernel_line[0].split()[0]
                            self._is_cachyos = True
                            self._emit(
                                f"[INFO] Detected CachyOS kernel: {self._cachyos_kernel}\n"
                            )
                            break

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
                                # Use cp with --reflink=auto for faster copies on COW filesystems
                                # Falls back to normal copy if reflink not supported
                                subprocess.run(
                                    ['cp', '--reflink=auto', str(pkg_file), local_repo_dir],
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
                # NVIDIA driver packages - modern drivers take priority
                # nvidia (proprietary) and nvidia-open (open-source) are the primary options
                # Legacy DKMS drivers (580xx, 470xx, 390xx, 340xx) only for very old hardware
                ['nvidia', 'nvidia-open', 'nvidia-580xx-dkms', 'nvidia-470xx-dkms',
                 'nvidia-390xx-dkms', 'nvidia-340xx-dkms'],
            ]

            # Detect which NVIDIA driver is installed on current system (for intelligent defaults)
            # Check for all possible NVIDIA driver packages including DKMS versions
            detected_nvidia_driver = None
            detected_nvidia_related = []

            # Check for standard drivers first
            result = run_command(['pacman', '-Q', 'nvidia', 'nvidia-open'], check=False)
            if result.returncode == 0:
                # Check stdout for which one is installed
                if 'nvidia ' in result.stdout:
                    detected_nvidia_driver = 'nvidia'
                elif 'nvidia-open ' in result.stdout:
                    detected_nvidia_driver = 'nvidia-open'

            # Check for DKMS NVIDIA drivers (580xx, 470xx, 390xx, 340xx)
            if detected_nvidia_driver is None:
                dkms_drivers = [
                    'nvidia-580xx-dkms', 'nvidia-470xx-dkms',
                    'nvidia-390xx-dkms', 'nvidia-340xx-dkms'
                ]
                for dkms_driver in dkms_drivers:
                    result = run_command(['pacman', '-Q', dkms_driver], check=False)
                    if result.returncode == 0:
                        detected_nvidia_driver = dkms_driver
                        # Extract version prefix (e.g., '580xx' from 'nvidia-580xx-dkms')
                        version_prefix = (
                            dkms_driver.replace('nvidia-', '').replace('-dkms', '')
                        )
                        # Find related packages
                        related_check = run_command(
                            ['pacman', '-Q'], check=False
                        )
                        if related_check.returncode == 0:
                            for line in related_check.stdout.split('\n'):
                                pkg_name = line.split()[0] if line.strip() else ''
                                if (f'nvidia-{version_prefix}' in pkg_name or
                                        f'lib32-nvidia-{version_prefix}' in pkg_name):
                                    if pkg_name not in detected_nvidia_related:
                                        detected_nvidia_related.append(pkg_name)
                        break

            # If still not found, check package list
            if detected_nvidia_driver is None:
                # Try checking if either is in the package list
                if 'nvidia' in packages and 'nvidia-open' not in packages:
                    # Check if it's a DKMS version
                    for pkg in packages:
                        if pkg.startswith('nvidia-') and pkg.endswith('-dkms'):
                            detected_nvidia_driver = pkg
                            version_prefix = (
                                pkg.replace('nvidia-', '').replace('-dkms', '')
                            )
                            # Collect related packages from package list
                            for related in packages:
                                if (f'nvidia-{version_prefix}' in related or
                                        f'lib32-nvidia-{version_prefix}' in related):
                                    if related not in detected_nvidia_related:
                                        detected_nvidia_related.append(related)
                            break
                    if detected_nvidia_driver is None:
                        detected_nvidia_driver = 'nvidia'
                elif 'nvidia-open' in packages:
                    detected_nvidia_driver = 'nvidia-open'

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
                # Video driver packages for various hardware
                "xf86-video-amdgpu",  # AMD GPUs (modern, replaces xf86-video-ati)
                # Note: xf86-video-intel is deprecated, Intel uses modesetting driver
                # Note: xf86-video-ati is deprecated, replaced by xf86-video-amdgpu
                # Audio drivers and firmware
                "pipewire",
                "pipewire-alsa",
                "pipewire-pulse",
                "wireplumber",
                "alsa-utils",
                "sof-firmware",  # Intel audio firmware (many modern systems)
                # Network/WiFi drivers and utilities
                "iwd",  # Modern wireless daemon
                "wpa_supplicant",  # WiFi authentication (backup/compatibility)
                # linux-firmware is already in required_packages, but list for clarity
            ]

            # Add sudo if user account with sudo access is configured
            user_config = self.config.get('user_config', {})
            username = user_config.get('username', '')
            user_sudo = user_config.get('user_sudo', False)
            if username and user_sudo:
                if 'sudo' not in packages and 'sudo' not in gui_must:
                    gui_must.append('sudo')
                    self._emit(
                        "[INFO] Adding 'sudo' package for user account with sudo access.\n"
                    )

            # Add NVIDIA driver based on what's detected/installed
            # Prefer proprietary nvidia over nvidia-open for better compatibility
            if detected_nvidia_driver:
                # For DKMS drivers, ensure driver and related packages are included
                if detected_nvidia_driver.endswith('-dkms'):
                    # Add the DKMS driver
                    if detected_nvidia_driver not in packages:
                        gui_must.append(detected_nvidia_driver)
                    # Add related packages if they're not already in the list
                    for related_pkg in detected_nvidia_related:
                        if related_pkg not in packages and related_pkg not in gui_must:
                            gui_must.append(related_pkg)
                    # Ensure DKMS package is included (needed to build DKMS modules)
                    if 'dkms' not in packages and 'dkms' not in gui_must:
                        gui_must.append('dkms')
                        self._emit(
                            "[INFO] Adding 'dkms' package for DKMS driver build.\n"
                        )
                    # Ensure kernel headers are included for DKMS build
                    # Try to detect which kernel is being used
                    kernel_packages = [
                        'linux-headers', 'linux-lts-headers',
                        'linux-cachyos-headers', 'linux-cachyos-bore-headers',
                        'linux-cachyos-lts-headers', 'linux-cachyos-hardened-headers'
                    ]
                    kernel_detected = False
                    for kernel_hdr in kernel_packages:
                        if kernel_hdr.replace('-headers', '') in packages:
                            if kernel_hdr not in packages and kernel_hdr not in gui_must:
                                gui_must.append(kernel_hdr)
                                kernel_detected = True
                                break
                    if not kernel_detected:
                        # Default to linux-headers if no specific kernel detected
                        if 'linux-headers' not in packages and 'linux-headers' not in gui_must:
                            gui_must.append('linux-headers')
                    self._emit(
                        f"[INFO] Detected NVIDIA DKMS driver: {detected_nvidia_driver}\n"
                    )
                    if detected_nvidia_related:
                        self._emit(
                            f"[INFO] Including related NVIDIA packages: "
                            f"{', '.join(detected_nvidia_related)}\n"
                        )
                    self._emit(
                        "[INFO] DKMS modules will be built during ISO creation.\n"
                    )
                else:
                    # Standard nvidia or nvidia-open driver
                    if detected_nvidia_driver not in packages:
                        gui_must.append(detected_nvidia_driver)
                    self._emit(
                        f"[INFO] Detected NVIDIA driver on system: "
                        f"{detected_nvidia_driver}, will include in ISO.\n"
                    )
            # If no NVIDIA driver detected but nvidia package exists, use it
            elif 'nvidia' in packages and 'nvidia-open' not in packages:
                # Check if it's a DKMS version in packages
                dkms_found = False
                for pkg in packages:
                    if pkg.startswith('nvidia-') and pkg.endswith('-dkms'):
                        dkms_found = True
                        # Try to find related packages
                        version_prefix = (
                            pkg.replace('nvidia-', '').replace('-dkms', '')
                        )
                        for related in packages:
                            if (f'nvidia-{version_prefix}' in related or
                                    f'lib32-nvidia-{version_prefix}' in related):
                                if related not in detected_nvidia_related:
                                    detected_nvidia_related.append(related)
                        break
                if dkms_found:
                    # Ensure kernel headers for DKMS
                    kernel_packages = [
                        'linux-headers', 'linux-lts-headers',
                        'linux-cachyos-headers', 'linux-cachyos-bore-headers',
                        'linux-cachyos-lts-headers', 'linux-cachyos-hardened-headers'
                    ]
                    for kernel_hdr in kernel_packages:
                        if kernel_hdr.replace('-headers', '') in packages:
                            if kernel_hdr not in packages and kernel_hdr not in gui_must:
                                gui_must.append(kernel_hdr)
                                break
            elif 'nvidia-open' in packages:
                # Don't add to gui_must, already in packages
                pass

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

            # Disable PC speaker beep by:
            # 1. Commenting out GRUB play commands (disables beep during countdown)
            # 2. Blacklisting pcspkr module via kernel parameter (disables beep in live session)
            # This will be added to all kernel command lines in GRUB/efiboot configs
            self._emit(
                "[INFO] Configuring boot options to disable GRUB beep and motherboard speaker...\n"
            )

            # Add kernel parameter to bootloader configs if they exist
            # archiso uses grub/ and efiboot/ directories for boot configs
            grub_dir = os.path.join(profile_dir, 'grub')
            efiboot_dir = os.path.join(profile_dir, 'efiboot')

            kernel_params = ' modprobe.blacklist=pcspkr'

            # Modify GRUB config files
            if os.path.exists(grub_dir):
                for grub_cfg in Path(grub_dir).rglob('*.cfg'):
                    try:
                        with open(grub_cfg, 'r', encoding='utf-8') as f:
                            content = f.read()
                        # Add kernel parameter to linux entries
                        # Match lines like: linux ... archisobasedir=arch ...
                        # Also comment out GRUB play commands to disable beep on countdown
                        modified_content = []
                        for line in content.split('\n'):
                            # Comment out GRUB play commands to disable beep sound
                            stripped = line.strip()
                            if stripped.startswith('play ') and not stripped.startswith('#'):
                                # Comment out the play command
                                indent = len(line) - len(line.lstrip())
                                line = ' ' * indent + '#' + stripped
                            elif line.strip().startswith('linux') and 'archisobasedir' in line:
                                # Add modprobe.blacklist=pcspkr if not already present
                                if 'modprobe.blacklist=pcspkr' not in line:
                                    # Add before archisobasedir or at end of options
                                    if 'archisobasedir=' in line:
                                        line = line.replace(
                                            'archisobasedir=',
                                            kernel_params + ' archisobasedir='
                                        )
                                    else:
                                        line = line.rstrip() + kernel_params
                            modified_content.append(line)
                        with open(grub_cfg, 'w', encoding='utf-8') as f:
                            f.write('\n'.join(modified_content))
                    except Exception as e:
                        self._emit(
                            f"[WARN] Could not modify GRUB config {grub_cfg}: {e}\n"
                        )

            # Modify efiboot/systemd-boot config files
            if os.path.exists(efiboot_dir):
                for boot_cfg in Path(efiboot_dir).rglob('*.conf'):
                    try:
                        with open(boot_cfg, 'r', encoding='utf-8') as f:
                            content = f.read()
                        modified_content = []
                        for line in content.split('\n'):
                            if line.strip().startswith('options ') and 'archisobasedir' in line:
                                # Add modprobe.blacklist=pcspkr if not already present
                                if 'modprobe.blacklist=pcspkr' not in line:
                                    line = line.rstrip() + kernel_params
                            modified_content.append(line)
                        with open(boot_cfg, 'w', encoding='utf-8') as f:
                            f.write('\n'.join(modified_content))
                    except Exception as e:
                        self._emit(
                            f"[WARN] Could not modify boot config {boot_cfg}: {e}\n"
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

            # Determine which modules to include based on packages
            # Check final package list for video drivers
            modules_list = ['i915', 'amdgpu', 'radeon']

            # Only add nvidia module if nvidia or nvidia-open driver is in packages
            # Check for actual driver packages, not utility packages
            # According to Arch wiki, nvidia should be in MODULES for early KMS
            has_nvidia = any(
                pkg in ['nvidia', 'nvidia-open'] or
                (pkg.startswith('nvidia-') and pkg.endswith('-dkms'))
                for pkg in packages
            )
            if has_nvidia:
                modules_list.append('nvidia')
                self._emit(
                    "[INFO] NVIDIA driver detected - adding nvidia module to "
                    "mkinitcpio MODULES for early KMS (DRM kernel mode setting).\n"
                )

            # Add audio and network modules for early loading
            # These ensure hardware works in live session
            audio_modules = ['snd_hda_intel', 'snd_sof_pci', 'snd_sof_intel_hda_common']
            network_modules = ['iwlwifi', 'r8169', 'e1000e', 'igb', 'ath10k_pci', 'ath9k', 'rtw89']

            # Add commonly needed modules (these are generic and won't hurt)
            modules_list.extend(audio_modules)
            modules_list.extend(network_modules)

            self._emit(
                "[INFO] Adding audio and network modules to mkinitcpio for "
                "live session compatibility.\n"
            )

            modules_str = ' '.join(modules_list)

            # Modify MODULES line to include video drivers for early KMS
            lines = mkinitcpio_content.split('\n')
            modified_lines = []
            modules_updated = False
            for line in lines:
                stripped = line.strip()
                if (stripped.startswith('MODULES=') and
                        not stripped.startswith('# MODULES')):
                    # Update MODULES to include detected video drivers for early KMS
                    modified_lines.append(
                        f'MODULES=({modules_str})'
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
                            j, f'MODULES=({modules_str})'
                        )
                        break

            self._write_text(
                mkinitcpio_conf, '\n'.join(modified_lines) + '\n'
            )

            # Configure user accounts
            user_config = self.config.get('user_config', {})
            username = user_config.get('username', 'archuser')
            user_password = user_config.get('user_password', 'arch')
            root_password = user_config.get('root_password', 'root')
            user_sudo = user_config.get('user_sudo', True)
            template_user = user_config.get('template_user', None)

            # Copy selected user's home as template for the configured user
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
                    # Copy user home to template directory for configured user
                    if username:
                        dest_template = os.path.join(
                            airootfs, 'etc', 'skel', f'user_template_{template_user}'
                        )
                    else:
                        # Fallback to root template if no username configured
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
                    # Use rsync with excludes - optimized for speed
                    # Use --no-perms/--no-owner for faster copying (permissions set later)
                    # --inplace avoids creating temporary files for better performance
                    # --partial allows resuming if interrupted
                    rsync_cmd = (
                        ['rsync', '-a', '--info=progress2',
                         '--numeric-ids', '--no-perms', '--no-owner', '--no-group',
                         '--inplace', '--partial', '--no-inc-recursive'] +
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
                if username:
                    self._emit(
                        "[INFO] No user template selected - "
                        f"user {username} will have blank home directory\n"
                    )
                else:
                    self._emit(
                        "[INFO] No user template selected - "
                        "using blank root home\n"
                    )

            # mkarchiso executes customize_airootfs.sh during build
            # This creates user account, sets passwords, restores templates, enables GDM
            self._write_customize_airootfs(
                airootfs, root_password, username, user_password,
                user_sudo, template_user
            )

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
            # Load template from scripts directory
            install_content = self._load_script_template('install.sh')
            # Replace template placeholders
            install_content = self._template_replace(install_content, {
                'ROOT_PASSWORD': root_password,
                'USERNAME': username or '',
                'USER_PASSWORD': user_password or '',
                'USER_SUDO': 'true' if user_sudo else 'false'
            })
            self._write_script(install_script, install_content)

            # Create desktop shortcut
            desktop_shortcut = os.path.join(
                airootfs, 'root', 'Desktop', 'Install Arch.desktop'
            )
            desktop_content = self._load_script_template('Install Arch.desktop')
            self._write_text(desktop_shortcut, desktop_content)
            # Desktop files should be executable and readable
            os.chmod(desktop_shortcut, 0o755)
            
            # Also create desktop file in system-wide applications directory
            # This ensures it appears in application menus even if Desktop folder isn't visible
            applications_dir = os.path.join(
                airootfs, 'usr', 'share', 'applications'
            )
            os.makedirs(applications_dir, exist_ok=True)
            system_desktop = os.path.join(
                applications_dir, 'Install Arch.desktop'
            )
            self._write_text(system_desktop, desktop_content)
            os.chmod(system_desktop, 0o644)  # Standard permissions for .desktop files
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

            # Get compression settings from config (default to faster zstd)
            compression_type = self.config.get('compression_type', 'zstd')
            compression_level = self.config.get('compression_level', None)

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
                elif stripped.startswith('bootmodes='):
                    # Preserve original bootmodes, or set default if not present
                    # This ensures GRUB is configured properly
                    if 'bootmodes=' not in '\n'.join(updated_lines):
                        updated_lines.append(line)
                elif stripped.startswith('COMPRESSION=') or stripped.startswith('#COMPRESSION='):
                    # Set compression type for squashfs (much faster builds)
                    if compression_type == 'zstd':
                        # Zstd: faster compression/decompression, good ratio
                        if compression_level:
                            updated_lines.append(f'COMPRESSION="zstd -Xcompression-level {compression_level}"\n')
                        else:
                            # Default level 6: good balance of speed and size
                            updated_lines.append('COMPRESSION="zstd -Xcompression-level 6"\n')
                    elif compression_type == 'gzip':
                        # Gzip: faster than xz, better than zstd at low levels
                        if compression_level:
                            updated_lines.append(f'COMPRESSION="gzip -Xcompression-level {compression_level}"\n')
                        else:
                            updated_lines.append('COMPRESSION="gzip"\n')
                    elif compression_type == 'xz':
                        # XZ: slower but best compression (default archiso behavior)
                        # Note: XZ compression level is set via -Xcompression-level
                        if compression_level:
                            updated_lines.append(
                                f'COMPRESSION="xz -Xbcj x86 -Xdict-size 25% -Xcompression-level {compression_level}"\n'
                            )
                        else:
                            # Default: no level specified (uses mkarchiso default)
                            updated_lines.append('COMPRESSION="xz -Xbcj x86 -Xdict-size 25%"\n')
                    else:
                        # Default to zstd for speed
                        updated_lines.append('COMPRESSION="zstd -Xcompression-level 6"\n')
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
