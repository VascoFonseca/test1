import cv2
import state

from config import FIRST_WINDOW
from logger import log
from windows import get_window, capture_window_background
import sys
from pathlib import Path

RADAR_PARENT = Path(r"C:\Users\PC\Desktop\TIBSBOTS")
if str(RADAR_PARENT) not in sys.path:
    sys.path.insert(0, str(RADAR_PARENT))

def capture_region(region):
    if region is None:
        return None

    try:
        first = get_window(FIRST_WINDOW)
        window_image = capture_window_background(first)

        if window_image is None:
            return None

        x, y, width, height = region
        window_height, window_width = window_image.shape[:2]

        x = max(0, min(x, window_width - 1))
        y = max(0, min(y, window_height - 1))

        width = min(width, window_width - x)
        height = min(height, window_height - y)

        if width <= 0 or height <= 0:
            return None

        return window_image[
            y:y + height,
            x:x + width
        ].copy()

    except Exception as e:
        log(f"Background capture error: {e!r}", "error")
        return None


def capture_radar_screenshot():
    """
    Capture the entire first window in grayscale for radar detection.
    The radar locator needs the full window, not just the minimap crop.
    """
    try:
        first = get_window(FIRST_WINDOW)
        image = capture_window_background(first)

        if image is None:
            return None

        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    except Exception as e:
        log(f"Radar screenshot error: {e!r}", "error")
        return None


def capture_minimap():
    return capture_region(state.minimap_region)


def capture_battlelist():
    return capture_region(state.battlelist_region)


def capture_ring_source():
    return capture_region(state.ring_source_region)


def capture_ring_equipment():
    return capture_region(state.ring_equipment_region)