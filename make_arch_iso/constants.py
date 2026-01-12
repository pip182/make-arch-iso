"""Constants for Arch Linux ISO Builder"""
import os

class Colors:
    """Color constants for UI styling - comprehensive dark theme palette"""

    # Status colors
    SUCCESS = "#51cf66"
    ERROR = "#ff6b6b"
    INFO = "#74c0fc"
    WARNING = "#ff6b6b"

    # Background colors (dark theme)
    BG_PRIMARY = "#1e1e1e"              # Main window background
    BG_SECONDARY = "#252525"            # Input fields, list widgets
    BG_TERTIARY = "#2a2a2a"             # Hover states, tooltips
    BG_QUATERNARY = "#292929"           # Alternate backgrounds
    BG_DARKEST = "#1a1a1a"              # Text edit backgrounds
    BG_BUTTON = "#3a3a3a"               # Default button background
    BG_BUTTON_HOVER = "#454545"         # Button hover state
    BG_BUTTON_PRESSED = "#2d2d2d"       # Button pressed state
    BG_DISABLED = "#1e1e1e"             # Disabled widget background

    # Text colors
    TEXT_PRIMARY = "#f0f0f0"            # Primary text color
    TEXT_SECONDARY = "#e0e0e0"          # Secondary text (group box titles)
    TEXT_DISABLED = "#707070"           # Disabled text
    TEXT_SELECTION = "#ffffff"          # Selected text color

    # Border colors
    BORDER_DEFAULT = "#404040"          # Default border
    BORDER_HOVER = "#505050"            # Hover border
    BORDER_ACTIVE = "#606060"           # Active/hover border (lighter)
    BORDER_FOCUS = "#4682b4"            # Focus border (blue)
    BORDER_DISABLED = "#353535"         # Disabled border (dashed)

    # Button colors
    BUTTON_SUCCESS = "#4a7c59"          # Success button (green)
    BUTTON_SUCCESS_HOVER = "#5a9c69"
    BUTTON_SUCCESS_PRESSED = "#295137"
    BUTTON_SUCCESS_BORDER = "#5a9c69"
    BUTTON_SUCCESS_BORDER_HOVER = "#6aac79"

    BUTTON_ERROR = "#7c4a4a"            # Error button (red)
    BUTTON_ERROR_HOVER = "#9c5a5a"
    BUTTON_ERROR_PRESSED = "#6c3a3a"
    BUTTON_ERROR_BORDER = "#9c5a5a"
    BUTTON_ERROR_BORDER_HOVER = "#ac6a6a"

    # Selection colors
    SELECTION_BG = "#4682b4"            # Selection background (blue)
    SELECTION_TEXT = "#ffffff"          # Selection text

    # List/Item colors
    LIST_ITEM_BORDER = "#353535"        # List item separator
    LIST_ITEM_HOVER = "#353535"         # List item hover

    # Checkbox colors
    CHECKBOX_BORDER = "#505050"         # Checkbox border
    CHECKBOX_BORDER_HOVER = "#606060"   # Checkbox hover border
    CHECKBOX_CHECKED = "#4682b4"        # Checkbox checked background

    # Progress bar colors
    PROGRESS_BG = "#252525"             # Progress bar background
    PROGRESS_CHUNK = "#4682b4"          # Progress bar fill

    # Scrollbar colors
    SCROLLBAR_BG = "#252525"            # Scrollbar background
    SCROLLBAR_HANDLE = "#404040"        # Scrollbar handle
    SCROLLBAR_HANDLE_HOVER = "#505050"  # Scrollbar handle hover

    # Combo box colors
    COMBO_ARROW = "#a0a0a0"             # Combo box dropdown arrow

    # Tooltip colors
    TOOLTIP_BG = "#2a2a2a"              # Tooltip background
    TOOLTIP_TEXT = "#ffffff"            # Tooltip text
    TOOLTIP_BORDER = "#555555"          # Tooltip border


class LayoutSpacing:
    """Spacing constants for layouts"""
    MAIN_SPACING = 8
    MAIN_MARGINS = 12
    GROUP_SPACING = 6
    GROUP_MARGINS = (8, 12, 8, 8)
    FIELD_SPACING = 6
    MIN_INPUT_HEIGHT = 24
    MIN_PROGRESS_HEIGHT = 28


class Paths:
    """Default path constants"""
    DEFAULT_WORK_DIR = os.path.expanduser('~/archiso_work')
    DEFAULT_OUTPUT_DIR = os.path.expanduser('~/iso_output')
    CONFIG_DIR = os.path.expanduser('~/.config')
    CONFIG_FILE = os.path.join(CONFIG_DIR, 'iso_builder_gui.json')
    RELENG_PROFILE = '/usr/share/archiso/configs/releng/'
    PACMAN_CACHE = '/var/cache/pacman/pkg/'


class Messages:
    """Message constants"""
    ROOT_REQUIRED = "Error: Must run as root (use sudo)"
    BUILD_SUCCESS = "Build completed successfully!"
    BUILD_FAILED = "Build failed"
    USB_WRITE_SUCCESS = "USB write completed successfully!"
    USB_WRITE_FAILED = "USB write failed"
    USB_WRITING = "Writing to USB..."
    READY = "Ready to build"
    BUILDING = "Building..."
