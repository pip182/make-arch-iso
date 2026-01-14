"""Utility functions"""
import os
import subprocess
from typing import List

def run_command(
    cmd: List[str],
    check: bool = False,
    capture_output: bool = True
) -> subprocess.CompletedProcess:
    """Run a shell command with consistent error handling"""
    return subprocess.run(
        cmd,
        check=check,
        capture_output=capture_output,
        text=True
    )


def safe_remove(path: str, emit_func=None) -> bool:
    """Safely remove a file or directory using optimized bulk deletion"""
    if os.path.exists(path):
        if emit_func:
            emit_func(f"  - Removing: {path}\n")
        try:
            if os.path.isdir(path):
                # For large directories, use rsync to clear (fastest method)
                # This is significantly faster than rm -rf for large dirs
                # because it doesn't need to traverse the directory tree
                empty_dir = '/tmp/.empty_rsync_dir'
                os.makedirs(empty_dir, exist_ok=True)
                try:
                    # Use rsync to sync empty dir to target (deletes)
                    empty_path = f'{empty_dir}/'
                    target_path = f'{path}/'
                    result = subprocess.run(
                        ['rsync', '-a', '--delete', empty_path, target_path],
                        check=False,
                        stderr=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL
                    )
                    # Remove the now-empty directory
                    if result.returncode == 0:
                        os.rmdir(path)
                    else:
                        # Fall back to rm -rf if rsync fails
                        subprocess.run(
                            ['rm', '-rf', '--', path],
                            check=False,
                            stderr=subprocess.DEVNULL
                        )
                finally:
                    # Clean up temp empty dir
                    try:
                        os.rmdir(empty_dir)
                    except OSError:
                        pass
            else:
                os.remove(path)
            return True
        except Exception:
            # Final fallback to rm -rf
            try:
                if os.path.isdir(path):
                    subprocess.run(
                        ['rm', '-rf', '--', path],
                        check=False,
                        stderr=subprocess.DEVNULL
                    )
                else:
                    os.remove(path)
            except Exception:
                return False
            return True
    return False


def safe_makedirs(path: str, mode: int = 0o755) -> None:
    """Safely create directories"""
    os.makedirs(path, mode=mode, exist_ok=True)
    os.chmod(path, mode)


def get_qt_dialog_code():
    """Get the correct QDialog code constant for PyQt version"""
    try:
        from PyQt6.QtWidgets import QDialog
        return QDialog.DialogCode.Accepted, QDialog.DialogCode.Rejected
    except ImportError:
        from PyQt5.QtWidgets import QDialog
        return QDialog.Accepted, QDialog.Rejected


def create_app_icon():
    """Create an application icon for Arch Linux ISO Builder"""
    from .qt_compat import QIcon, QPixmap, QPainter, QColor, Qt, HAS_PYQT6

    # Create a 64x64 pixmap for the icon
    size = 64
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(0, 0, 0, 0))  # Transparent background

    painter = QPainter(pixmap)
    if HAS_PYQT6:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    else:
        painter.setRenderHint(QPainter.Antialiasing)

    # Draw a disc/circle (silver/metallic color for ISO disc)
    center = size // 2
    disc_radius = 24

    # Outer disc circle (silver gradient effect)
    painter.setPen(QColor(180, 180, 180))
    painter.setBrush(QColor(220, 220, 220))
    painter.drawEllipse(center - disc_radius, center - disc_radius,
                       disc_radius * 2, disc_radius * 2)

    # Inner circle (center hole of disc)
    inner_radius = 6
    painter.setPen(QColor(60, 60, 60))
    painter.setBrush(QColor(40, 40, 40))
    painter.drawEllipse(center - inner_radius, center - inner_radius,
                       inner_radius * 2, inner_radius * 2)

    # Draw Arch Linux triangle (Arch brand blue color)
    triangle_size = 14
    triangle_y_offset = -2  # Slightly above center

    # Arch Linux triangle vertices (upside down triangle)
    triangle_points = [
        (center, center + triangle_y_offset - triangle_size // 2),  # Top point
        (center - triangle_size // 2, center + triangle_y_offset + triangle_size // 3),  # Bottom left
        (center + triangle_size // 2, center + triangle_y_offset + triangle_size // 3),  # Bottom right
    ]

    # Use Arch Linux blue (#1793D1)
    arch_blue = QColor(23, 147, 209)
    painter.setPen(arch_blue)
    painter.setBrush(arch_blue)

    # Use QPoint and QPolygon for PyQt compatibility
    if HAS_PYQT6:
        from PyQt6.QtGui import QPolygon
        from PyQt6.QtCore import QPoint
    else:
        from PyQt5.QtGui import QPolygon, QPoint

    polygon = QPolygon()
    for point in triangle_points:
        polygon.append(QPoint(point[0], point[1]))

    painter.drawPolygon(polygon)

    painter.end()

    # Create icon from pixmap
    icon = QIcon(pixmap)
    return icon
