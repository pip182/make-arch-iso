"""GUI Thread classes"""
import subprocess

from ..qt_compat import QThread, pyqtSignal
from ..utils import run_command


class PackageLoaderThread(QThread):
    """Thread for loading packages without blocking the UI"""
    progress_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(list, set)

    def run(self):
        """Load all packages from the system and identify AUR packages"""
        all_packages = []
        aur_packages = set()
        try:
            # Get all installed packages
            self.progress_signal.emit("Loading package list...")
            result = run_command(['pacman', '-Qqe'], check=True)
            package_names = [
                pkg.strip() for pkg in result.stdout.strip().split('\n')
                if pkg.strip()
            ]
            total = len(package_names)
            self.progress_signal.emit(
                f"Checking {total} packages for AUR status..."
            )

            for idx, pkg in enumerate(package_names):
                # Update progress every 50 packages
                if idx % 50 == 0:
                    self.progress_signal.emit(
                        f"Collecting packages, please wait... ({idx}/{total})"
                    )

                # Check if package is in official/custom repos
                result = subprocess.run(
                    ['pacman', '-Si', pkg],
                    capture_output=True, text=True
                )

                if result.returncode == 0:
                    # Package is in repos
                    all_packages.append({
                        'name': pkg,
                        'is_aur': False
                    })
                else:
                    # Package is likely AUR
                    all_packages.append({
                        'name': pkg,
                        'is_aur': True
                    })
                    aur_packages.add(pkg)

            # Sort packages: AUR first, then alphabetically
            all_packages.sort(
                key=lambda x: (not x['is_aur'], x['name'].lower())
            )
            self.progress_signal.emit("Package loading complete!")
            self.finished_signal.emit(all_packages, aur_packages)
        except Exception as e:
            self.progress_signal.emit(f"Error: {str(e)}")
            self.finished_signal.emit([], set())
