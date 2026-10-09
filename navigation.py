import time
import config
import cv2

import state, state,config
from config import (
    MATCH_THRESHOLD,
    CLICK_COOLDOWN,
    SECOND_WINDOW,
    SCAN_INTERVAL,
)
from logger import log, update_status
from capture import capture_minimap
from windows import get_window, bring_to_front, capture_window_background
from battle import move_mouse_to_safe_position

import os
import numpy as np
import pyautogui

from capture import capture_region

def set_permanent_destination(index=None):
    if index is None:
        index = state.current_location_index

    if not 0 <= index < len(state.location_templates):
        log(
            f"Cannot set permanent destination: invalid index {index}",
            "warning"
        )
        return False

    state.permanent_destination_index = index
    state.permanent_destination_template = (
        state.location_templates[index]
    )
    state.current_destination_match = None

    destination = state.permanent_destination_template
    log(
        f"PERMANENT DESTINATION SET | index={index + 1} | "
        f"name={destination['name']}"
    )
    return True


def get_current_location():
    if not state.location_templates:
        return None

    if state.permanent_destination_index is None:
        state.permanent_destination_index = (
            state.current_location_index
        )

    index = state.permanent_destination_index

    if not 0 <= index < len(state.location_templates):
        return None

    return state.location_templates[index]


def find_current_location():
    template_data = state.permanent_destination_template

    if template_data is None:
        template_data = get_current_location()

    if template_data is None or state.minimap_region is None:
        state.current_destination_match = None
        return None

    minimap = capture_minimap()
    if minimap is None:
        state.current_destination_match = None
        return None

    template = template_data["image"]
    mh, mw = minimap.shape[:2]
    th, tw = template.shape[:2]

    if tw > mw or th > mh:
        state.current_destination_match = None
        return None

    result = cv2.matchTemplate(
        minimap, template, cv2.TM_CCOEFF_NORMED
    )
    _, confidence, _, location = cv2.minMaxLoc(result)

    if confidence < MATCH_THRESHOLD:
        state.current_destination_match = None
        return None

    center_x = location[0] + tw // 2
    center_y = location[1] + th // 2

    match = {
        "template": template_data,
        "confidence": confidence,
        "x": center_x,
        "y": center_y,
        "rect": (location[0], location[1], tw, th),
    }

    state.current_destination_match = match
    return match


def is_location_centered(match):
    if match is None:
        return False

    minimap = capture_minimap()
    if minimap is None:
        return False

    height, width = minimap.shape[:2]

    center_x = width // 2
    center_y = height // 2

    distance_x = abs(match["x"] - center_x)
    distance_y = abs(match["y"] - center_y)

    centered = (
        distance_x <= config.ARRIVAL_TOLERANCE_X
        and distance_y <= config.ARRIVAL_TOLERANCE_Y
    )

    if centered:
        destination = get_current_location()
        name = destination["name"] if destination else "UNKNOWN"

        log(
            f"ARRIVAL POSITION CHECK | "
            f"destination={name} | "
            f"distance=({distance_x},{distance_y})"
        )

    return centered



def click_destination(match, reason="destination"):
    if match is None:
        log("CLICK SKIPPED: match is None", "warning")
        return False

    now = time.time()
    if now - state.last_click_time < CLICK_COOLDOWN:
        log("CLICK SKIPPED: cooldown", "debug")
        return False

    if state.minimap_region is None:
        log("CLICK ERROR: minimap not selected", "error")
        return False

    try:
        second = get_window(SECOND_WINDOW)
        minimap_x, minimap_y, _, _ = state.minimap_region

        relative_x = minimap_x + match["x"]
        relative_y = minimap_y + match["y"]

        current = get_current_location()
        name = current["name"] if current else "UNKNOWN"

        log(
            f"CLICK DESTINATION | reason={reason} | "
            f"permanent={name} | "
            f"confidence={match['confidence']:.3f} | "
            f"minimap=({match['x']},{match['y']}) | "
            f"window_relative=({relative_x},{relative_y})"
        )

        bring_to_front(second)
        time.sleep(0.20)

        second = get_window(SECOND_WINDOW)
        click_x = second.left + relative_x
        click_y = second.top + relative_y

        import pyautogui
        pyautogui.moveTo(click_x, click_y, duration=0.15)
        time.sleep(0.10)
        pyautogui.click(x=click_x, y=click_y)

        state.last_click_time = time.time()
        log(f"CLICKED: ({click_x},{click_y})")

        move_mouse_to_safe_position()
        time.sleep(0.25)
        return True

    except Exception as e:
        log(f"CLICK ERROR: {e!r}", "error")
        return False


def save_destination(match):
    if match is None:
        return

    state.current_destination_match = {
        "template": match["template"],
        "confidence": match["confidence"],
        "x": match["x"],
        "y": match["y"],
        "rect": match["rect"],
    }

    destination = get_current_location()
    if destination:
        log(
            f"DESTINATION MATCH UPDATED | "
            f"permanent={destination['name']} | "
            f"x={match['x']} | y={match['y']} | "
            f"confidence={match['confidence']:.3f}",
            "debug"
        )


def resume_saved_destination():
    destination = get_current_location()

    if destination is None:
        log("RESUME FAILED: no permanent destination", "warning")
        return False

    log(f"RESUMING PERMANENT DESTINATION: {destination['name']}")

    for attempt in range(1, 11):
        if not state.running:
            return False

        match = find_current_location()

        if match:
            log(
                f"RESUME MATCH FOUND | attempt={attempt} | "
                f"destination={destination['name']} | "
                f"confidence={match['confidence']:.3f}"
            )

            if is_location_centered(match):
                return True

            if click_destination(
                match,
                reason="resume permanent destination after combat"
            ):
                return True
        else:
            log(
                f"RESUME: permanent destination not visible | "
                f"attempt={attempt}",
                "debug"
            )

        time.sleep(SCAN_INTERVAL)

    log(
        f"RESUME FAILED: could not locate destination "
        f"'{destination['name']}'",
        "warning"
    )
    return False


def advance_location():
    state.current_location_index += 1

    if state.current_location_index >= len(state.location_templates):
        state.current_location_index = 0
        log("ROUTE COMPLETE - returning to LOCATION 1")
    else:
        location = state.location_templates[state.current_location_index]
        log(
            f"NEXT LOCATION: {state.current_location_index + 1} | "
            f"{location['name']}"
        )

    set_permanent_destination(state.current_location_index)

    update_status(
        f"Going to location {state.current_location_index + 1}/"
        f"{len(state.location_templates)}"
    )
arrival_candidate_index = None
arrival_confirmations = 0


def confirm_arrival(match):
    global arrival_candidate_index
    global arrival_confirmations

    if match is None or not is_location_centered(match):
        arrival_candidate_index = None
        arrival_confirmations = 0
        return False

    destination_index = state.permanent_destination_index

    if destination_index != arrival_candidate_index:
        arrival_candidate_index = destination_index
        arrival_confirmations = 1
    else:
        arrival_confirmations += 1

    return (
        arrival_confirmations
        >= config.ARRIVAL_REQUIRED_CHECKS
    )

def backpack_slot_is_empty():
    region = state.backpack_slot_region

    if region is None:
        return False

    slot = capture_region(region)

    if slot is None:
        return False

    template_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        config.EMPTY_SLOT_TEMPLATE_FILE,
    )

    empty_template = cv2.imread(
        template_path,
        cv2.IMREAD_COLOR,
    )

    if empty_template is None:
        log("Empty-slot template could not be loaded.", "warning")
        return False

    if slot.shape != empty_template.shape:
        log("Empty-slot template dimensions do not match.", "warning")
        return False

    difference = cv2.absdiff(slot, empty_template)
    score = float(np.mean(difference))

    log(f"Backpack empty-slot difference: {score:.2f}", "debug")

    return score <= config.EMPTY_SLOT_MAX_DIFFERENCE


def find_ring():
    template_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        config.RING_TEMPLATE_FILE,
    )

    ring_template = cv2.imread(
        template_path,
        cv2.IMREAD_COLOR,
    )

    if ring_template is None:
        log("Ring template could not be loaded.", "warning")
        return None

    # Capture the first window using the existing capture system.
    first = get_window(config.FIRST_WINDOW)
    screenshot = capture_window_background(first)

    if screenshot is None:
        return None

    height, width = screenshot.shape[:2]
    ring_height, ring_width = ring_template.shape[:2]

    if ring_height > height or ring_width > width:
        return None

    result = cv2.matchTemplate(
        screenshot,
        ring_template,
        cv2.TM_CCOEFF_NORMED,
    )

    _, confidence, _, location = cv2.minMaxLoc(result)

    if confidence < config.RING_MATCH_THRESHOLD:
        return None

    center_x = location[0] + ring_width // 2
    center_y = location[1] + ring_height // 2

    return (
        first.left + center_x,
        first.top + center_y,
        confidence,
    )


def check_ring():
    now = time.monotonic()

    if state.backpack_slot_region is None:
        return

    if now - state.last_ring_check_time < config.RING_CHECK_INTERVAL:
        return

    state.last_ring_check_time = now

    if now - state.last_ring_click_time < config.RING_CLICK_COOLDOWN:
        return

    if not backpack_slot_is_empty():
        return

    ring = find_ring()

    if ring is None:
        log("Empty slot detected, but ring was not found.", "debug")
        return

    x, y, confidence = ring

    log(
        f"Ring found at ({x}, {y}), "
        f"confidence={confidence:.3f}"
    )

    pyautogui.doubleClick(x, y, interval=0.12)

    state.last_ring_click_time = time.monotonic()
    log("Ring double-clicked.")