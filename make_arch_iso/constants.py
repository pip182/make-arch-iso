"""Constants for Arch Linux ISO Builder"""
import os


class Colors:
    """Color constants for UI styling - comprehensive dark theme palette"""

    # Status colors
    SUCCESS = "#51c460"                      # Status: success (green)
    ERROR = "#ff6b6b"                        # Status: error (red)
    INFO = "#74b6ef"                         # Status: info (blue)
    WARNING = "#ff6b6b"                      # Status: warning (red, same as error)

    # Background colors (dark theme) - blue-based grays, high contrast
    BG_PRIMARY = "#1c181e"                     # Main window background
    BG_SECONDARY = "#1f1c24"                   # Input fields, list widgets
    BG_TERTIARY = "#212027"                    # Hover states, tooltips, group boxes
    BG_QUATERNARY = "#25222e"                  # Alternate backgrounds
    BG_DARKEST = "#15141a"                     # Text edit backgrounds
    BG_BUTTON = "#282733"                      # Default button background
    BG_BUTTON_HOVER = "#2e2738"                # Button hover state background
    BG_BUTTON_PRESSED = "#1e2028"              # Button pressed state background
    BG_DISABLED = "#1c181e"                    # Disabled widget background

    # Text colors - higher contrast
    TEXT_PRIMARY = "#ECEFF1"                 # Primary text color (brighter)
    TEXT_SECONDARY = "#CFD4DC"               # Secondary text (group box titles)
    TEXT_DISABLED = "#78889C"                # Disabled text color
    TEXT_SELECTION = "#ffffff"               # Selected text color

    # Border colors - increased contrast
    BORDER_DEFAULT = "#455564"               # Default border (blue-gray)
    BORDER_HOVER = "#5467aA"                 # Hover border (blue)
    BORDER_ACTIVE = "#60758B"                # Active/hover border (lighter)
    BORDER_FOCUS = "#64a2e9"                 # Focus border (blue highlight)
    BORDER_DISABLED = "#37444F"              # Disabled border (dashed look)

    # Button colors
    # Button colors for "Success" (e.g., confirm, OK actions) - green-based
    BUTTON_SUCCESS = "#4a7554"               # Success button background
    BUTTON_SUCCESS_HOVER = "#5a9463"         # Success button background (hover state)
    BUTTON_SUCCESS_PRESSED = "#294c34"       # Success button background (pressed state)
    BUTTON_SUCCESS_BORDER = "#5a9463"        # Success button border (default)
    BUTTON_SUCCESS_BORDER_HOVER = "#6aa372"  # Success button border (hover state)

    BUTTON_ERROR = "#7c4a4a"                 # Error button background (red)
    BUTTON_ERROR_HOVER = "#9c5a5a"           # Error button background (hover state)
    BUTTON_ERROR_PRESSED = "#6c3a3a"         # Error button background (pressed state)
    BUTTON_ERROR_BORDER = "#9c5a5a"          # Error button border (default)
    BUTTON_ERROR_BORDER_HOVER = "#ac6a6a"    # Error button border (hover state)

    # Selection colors - brighter blue
    SELECTION_BG = "#64a2e9"                 # Background for selected items (blue)
    SELECTION_TEXT = "#ffffff"               # Selection text (white)

    # List/Item colors
    LIST_ITEM_BORDER = "#353235"             # List item separator border
    LIST_ITEM_HOVER = "#353235"              # List item hover background/border

    # Checkbox colors - blue-based
    CHECKBOX_BORDER = "#54677A"              # Checkbox border
    CHECKBOX_BORDER_HOVER = "#60758B"        # Checkbox hover border
    CHECKBOX_CHECKED = "#64a2e9"             # Checkbox checked indicator (blue)

    # Progress bar colors - blue-based
    PROGRESS_BG = "#252833"                  # Progress bar background
    PROGRESS_CHUNK = "#64a2e9"               # Progress bar filled portion (chunk)

    # Scrollbar colors
    SCROLLBAR_BG = "#252833"                 # Scrollbar background
    SCROLLBAR_HANDLE = "#455564"             # Scrollbar handle
    SCROLLBAR_HANDLE_HOVER = "#54677A"       # Scrollbar handle (hover state)

    # Combo box colors
    COMBO_ARROW = "#a0a0a0"                  # Combo box dropdown arrow color

    # Tooltip colors - blue-based
    TOOLTIP_BG = "#2a3039"                   # Tooltip background
    TOOLTIP_TEXT = "#ECEFF1"                 # Tooltip text color
    TOOLTIP_BORDER = "#54677A"               # Tooltip border color


class LayoutSpacing:
    """Spacing constants for layouts"""
    MAIN_SPACING = 16  # Increased from 8
    MAIN_MARGINS = 16  # Increased from 12
    GROUP_SPACING = 12  # Increased from 6
    GROUP_MARGINS = (12, 16, 12, 12)  # Increased from (8, 12, 8, 8)
    FIELD_SPACING = 10  # Increased from 6
    MIN_INPUT_HEIGHT = 28  # Increased from 24
    MIN_PROGRESS_HEIGHT = 32  # Increased from 28
    SECTION_SPACING = 20  # Spacing between major sections


class Paths:
    """Default path constants"""
    DEFAULT_WORK_DIR = os.path.expanduser('~/archiso_work')
    DEFAULT_OUTPUT_DIR = os.path.expanduser('~/iso_output')
    CONFIG_DIR = os.path.expanduser('.config/')
    CONFIG_FILE = os.path.join(CONFIG_DIR, 'iso_builder_gui.json')
    LOG_DIR = os.path.join(CONFIG_DIR, 'iso_builder_logs')
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
