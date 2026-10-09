import time

import cv2
import numpy as np
import pyautogui
import pytesseract
import os
import state
import config

from capture import (
    capture_ring_source,
    capture_ring_equipment,
    capture_window_background,
)

from config import (
    SECOND_WINDOW,
    FOCUS_DELAY,
    RED_MIN,
    RED_RATIO,
    RED_PIXEL_THRESHOLD,
    OCR_CONFIG,
    MOUSE_RETURN_X,
    MOUSE_RETURN_Y,
)
from logger import log
from capture import capture_battlelist
from windows import get_window, bring_to_front

def battlelist_ocr(image):
    if image is None:
        return ""

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(
        gray, None, fx=3, fy=3,
        interpolation=cv2.INTER_CUBIC
    )
    gray = cv2.GaussianBlur(gray, (3, 3), 0)

    _, threshold = cv2.threshold(
        gray, 0, 255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )

    text = pytesseract.image_to_string(
        threshold, config=OCR_CONFIG
    )
    return text.strip()


def detect_red_pixels(image):
    if image is None:
        return False, 0

    b = image[:, :, 0].astype(np.int16)
    g = image[:, :, 1].astype(np.int16)
    r = image[:, :, 2].astype(np.int16)

    red_mask = (
        (r > RED_MIN)
        & (r > g * RED_RATIO)
        & (r > b * RED_RATIO)
    )

    red_pixels = int(np.sum(red_mask))
    return red_pixels > RED_PIXEL_THRESHOLD, red_pixels

def analyze_battlelist():
    image = capture_battlelist()

    if image is None:
        return False, False, "", 0, image

    ocr_text = battlelist_ocr(image)
    clean_text = (
        ocr_text.replace(" ", "")
        .replace("\n", "")
        .replace("\r", "")
        .replace("\t", "")
    )

    has_target = bool(clean_text)
    attacking, red_pixels = detect_red_pixels(image)

    return has_target, attacking, ocr_text, red_pixels, image

def check_for_target():
    (
        has_target,
        attacking,
        ocr_text,
        red_pixels,
        image
    ) = analyze_battlelist()

    if ocr_text:
        log(f"BATTLELIST OCR: {ocr_text!r}", "debug")

    if has_target:
        log(
            f"TARGET FOUND | red={red_pixels} | "
            f"attacking={attacking}"
        )

    return has_target, attacking, ocr_text, red_pixels, image


def send_key_to_second_window(key):
    log(f"SENDING KEY: {key.upper()}")

    try:
        second = get_window(SECOND_WINDOW)
        bring_to_front(second)
        time.sleep(FOCUS_DELAY)

        pyautogui.press(key)
        log(f"KEY SENT: {key.upper()}")

        time.sleep(FOCUS_DELAY)

    except Exception as e:
        log(f"Key sending error: {e!r}", "error")

def move_mouse_to_safe_position():
    try:
        second = get_window(SECOND_WINDOW)

        x = second.left + MOUSE_RETURN_X
        y = second.top + MOUSE_RETURN_Y

        x = max(
            second.left,
            min(x, second.left + second.width - 1)
        )
        y = max(
            second.top,
            min(y, second.top + second.height - 1)
        )

        pyautogui.moveTo(x, y, duration=0.05)

        log(
            f"Mouse returned inside SECOND window: ({x},{y})"
        )

    except Exception as e:
        log(f"Mouse return error: {e!r}", "error")