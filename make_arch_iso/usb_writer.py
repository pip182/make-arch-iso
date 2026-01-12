"""USB Writer Thread"""
import os
import subprocess

from .qt_compat import QThread, pyqtSignal
from .utils import run_command


class USBWriterThread(QThread):
    """Thread for writing ISO to USB drive without blocking the UI"""
    output_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, iso_path, device):
        super().__init__()
        self.iso_path = iso_path
        self.device = device
        self.process = None

    def _emit(self, message: str) -> None:
        self.output_signal.emit(message)

    def run(self):
        """Write ISO to USB device"""
        try:
            if os.geteuid() != 0:
                self.finished_signal.emit(
                    False,
                    "Error: Must run as root (use sudo) to write to USB"
                )
                return

            if not os.path.exists(self.device):
                self.finished_signal.emit(
                    False, f"Error: Device {self.device} does not exist"
                )
                return

            iso_size = os.path.getsize(self.iso_path)
            iso_size_gb = iso_size / (1024**3)

            self._emit(
                f"\n[INFO] Writing ISO to USB device: {self.device}\n"
            )
            self._emit(
                f"[INFO] ISO size: {iso_size_gb:.2f} GB\n"
            )
            self._emit(
                f"[WARN] This will erase all data on {self.device}!\n"
            )
            self._emit(
                "[INFO] Writing... (this may take several minutes)\n"
            )
            self.progress_signal.emit(10)

            self._emit(
                "[INFO] Unmounting device partitions...\n"
            )
            result = run_command(
                ['umount', '-f', self.device + '*'], check=False
            )
            if result.returncode != 0:
                for part_num in range(1, 10):
                    part = f"{self.device}{part_num}"
                    if os.path.exists(part):
                        run_command(['umount', '-f', part], check=False)

            self.progress_signal.emit(20)

            self._emit(
                f"[INFO] Writing ISO to {self.device}...\n"
            )
            self.process = subprocess.Popen(
                [
                    'dd', f'if={self.iso_path}', f'of={self.device}',
                    'bs=4M', 'status=progress', 'oflag=sync'
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            for line in self.process.stdout:
                self._emit(line)
                if 'records in' in line or 'records out' in line:
                    self.progress_signal.emit(60)
                elif 'copied' in line.lower():
                    self.progress_signal.emit(80)

            self.process.wait()

            if self.process.returncode == 0:
                self.progress_signal.emit(100)
                self._emit(
                    "\n[SUCCESS] ISO written to USB device successfully!\n"
                )
                self._emit(f"[INFO] Device: {self.device}\n")
                self._emit(
                    "[INFO] You can now boot from this USB drive.\n"
                )
                self.finished_signal.emit(
                    True, f"ISO written to {self.device}"
                )
            else:
                self._emit(
                    "\n[ERROR] Failed to write ISO to USB device!\n"
                )
                self.finished_signal.emit(False, "USB write process failed")

        except Exception as e:
            self._emit(f"\n[ERROR] {str(e)}\n")
            self.finished_signal.emit(False, str(e))

    def stop(self):
        """Stop the write process"""
        if self.process:
            self.process.terminate()
