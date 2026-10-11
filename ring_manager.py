import os
import time

import cv2
import numpy as np
import pyautogui

import state
import config
from capture import capture_region
from logger import log
from windows import get_window


TEMPLATE_DIR = "templates"
RING_TEMPLATE_PATH = os.path.join(TEMPLATE_DIR, "ring.png")
EMPTY_SLOT_TEMPLATE_PATH = os.path.join(
    TEMPLATE_DIR, "empty_slot.png"
)

_last_check = 0.0
_last_attempt = 0.0


def _load_template(path):
    """Load an image template, returning None if unavailable."""
    if not os.path.isfile(path):
        log(f"Ring manager: template not found: {path}", "warning")
        return None

    image = cv2.imread(path, cv2.IMREAD_COLOR)

    if image is None:
        log(f"Ring manager: could not load {path}", "warning")

    return image


def _equipment_is_empty():
    """Compare the equipment slot against the empty-slot template."""
    if state.ring_equipment_region is None:
        log("Ring manager: equipment region is not configured", "warning")
        return None

    current = capture_region(state.ring_equipment_region)
    empty_template = _load_template(EMPTY_SLOT_TEMPLATE_PATH)

    if current is None or empty_template is None:
        return None

    if current.size == 0:
        return None

    # Compare images at the same dimensions.
    if current.shape[:2] != empty_template.shape[:2]:
        empty_template = cv2.resize(
            empty_template,
            (current.shape[1], current.shape[0]),
            interpolation=cv2.INTER_AREA,
        )

    difference = cv2.absdiff(current, empty_template)
    mean_difference = float(np.mean(difference))

    is_empty = mean_difference <= config.EMPTY_SLOT_MAX_DIFFERENCE

    return is_empty


def _find_ring_in_backpack():
    """Find the ring's RGB pixel inside the backpack region."""
    if state.backpack_slot_region is None:
        log("Ring manager: backpack region is not configured", "warning")
        return None

    backpack = capture_region(state.backpack_slot_region)

    if backpack is None or backpack.size == 0:
        return None

    # The requested colour is RGB, but OpenCV captures images in BGR.
    target_bgr = np.array([246, 136, 98], dtype=np.uint8)

    # Find pixels matching the ring colour.
    matches = np.all(backpack[:, :, :3] == target_bgr, axis=2)
    ys, xs = np.where(matches)

    if len(xs) == 0:
        log("Ring manager: ring colour not found in backpack", "debug")
        return None

    # Use the centre of all matching pixels as the drag position.
    match_x = int(xs[0])
    match_y = int(ys[0])

    region_x, region_y, _, _ = state.backpack_slot_region

    screen_x = region_x + match_x
    screen_y = region_y + match_y

    log(
        f"Ring manager: found {len(xs)} matching pixels "
        f"at ({screen_x}, {screen_y})",
        "debug",
    )

    return screen_x, screen_y

def _drag_ring_to_equipment(source_x, source_y):
    """Explicitly hold the left mouse button while dragging the ring."""
    if state.ring_equipment_region is None:
        log("Ring manager: equipment region is not configured", "warning")
        return False

    x, y, width, height = state.ring_equipment_region

    if width <= 0 or height <= 0:
        log("Ring manager: invalid equipment region", "warning")
        return False

    target_x = x + width // 2
    target_y = y + height // 2

    window = get_window(config.SECOND_WINDOW)

    source_screen_x = window.left + source_x
    source_screen_y = window.top + source_y
    target_screen_x = window.left + target_x
    target_screen_y = window.top + target_y

    try:
        # Move to the ring.
        pyautogui.moveTo(source_screen_x, source_screen_y, duration=0.2)

        # Explicitly press and hold the left button.
        pyautogui.mouseDown(button="left")

        # Move while holding the button.
        pyautogui.moveTo(
            target_screen_x,
            target_screen_y,
            duration=0.2,
            tween=pyautogui.linear,
        )
        # Release at the centre of the equipment slot.
        pyautogui.mouseUp(button="left")

        log(
            f"Ring manager: drag completed from "
            f"({source_screen_x}, {source_screen_y}) to "
            f"({target_screen_x}, {target_screen_y})"
        )

        return True

    except Exception as exc:
        # Ensure the mouse button is released if an error occurs.
        pyautogui.mouseUp(button="left")
        log(f"Ring manager: drag failed: {exc!r}", "error")
        return False
    
def check_and_equip_ring(force=False):
    global _last_check, _last_attempt

    now = time.monotonic()

    if not force and now - _last_check < config.RING_CHECK_INTERVAL:
        return

    _last_check = now

    slot_empty = _equipment_is_empty()

    if slot_empty is None:
        return

    # Ring is already equipped: don't search the backpack.
    if not slot_empty:
        log("Ring manager: ring slot occupied", "debug")
        return

    if now - _last_attempt < config.RING_CLICK_COOLDOWN:
        return

    ring_position = _find_ring_in_backpack()

    if ring_position is None:
        return

    _last_attempt = now

    if not _drag_ring_to_equipment(*ring_position):
        return

    time.sleep(0.5)

    slot_empty_after_drop = _equipment_is_empty()

    if slot_empty_after_drop is False:
        log("Ring manager: ring equipped successfully")
    elif slot_empty_after_drop is True:
        log(
            "Ring manager: slot still appears empty; "
            "will retry after cooldown",
            "warning",
        )