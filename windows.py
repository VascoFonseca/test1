import ctypes
from ctypes import wintypes
import time

import numpy as np
import pygetwindow as gw

from config import FIRST_WINDOW, SECOND_WINDOW, FOCUS_DELAY
from logger import log

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

PW_RENDERFULLCONTENT = 0x00000002


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [
        ("bmiHeader", BITMAPINFOHEADER),
        ("bmiColors", wintypes.DWORD * 3),
    ]


def get_window(title):
    windows = gw.getWindowsWithTitle(title)

    if not windows:
        raise RuntimeError(f"Window not found: {title}")

    return windows[0]


def bring_to_front(window):
    try:
        if window.isMinimized:
            window.restore()
            time.sleep(0.2)

        window.activate()
        time.sleep(FOCUS_DELAY)

    except Exception as e:
        log(f"Window activation error: {e!r}", "error")


def bring_first_to_front():
    window = get_window(FIRST_WINDOW)
    bring_to_front(window)
    return window


def bring_second_to_front():
    window = get_window(SECOND_WINDOW)
    bring_to_front(window)
    return window


def synchronize_window_size():
    try:
        first = get_window(FIRST_WINDOW)
        second = get_window(SECOND_WINDOW)

        target_width = second.width
        target_height = second.height

        if (
            first.width != target_width
            or first.height != target_height
        ):
            log(
                f"Resizing FIRST window: "
                f"{first.width}x{first.height} -> "
                f"{target_width}x{target_height}"
            )

            first.resizeTo(target_width, target_height)
            time.sleep(0.3)

    except Exception as e:
        log(f"Window synchronization error: {e!r}", "error")


def capture_window_background(window):
    try:
        hwnd = window._hWnd
    except Exception:
        log("Could not get HWND.", "error")
        return None

    width = window.width
    height = window.height

    if width <= 0 or height <= 0:
        return None

    hwnd_dc = user32.GetWindowDC(hwnd)
    if not hwnd_dc:
        return None

    mfc_dc = gdi32.CreateCompatibleDC(hwnd_dc)
    if not mfc_dc:
        user32.ReleaseDC(hwnd, hwnd_dc)
        return None

    bitmap = gdi32.CreateCompatibleBitmap(
        hwnd_dc, width, height
    )

    if not bitmap:
        gdi32.DeleteDC(mfc_dc)
        user32.ReleaseDC(hwnd, hwnd_dc)
        return None

    old_bitmap = gdi32.SelectObject(mfc_dc, bitmap)

    try:
        result = user32.PrintWindow(
            hwnd, mfc_dc, PW_RENDERFULLCONTENT
        )

        if result != 1:
            result = user32.PrintWindow(hwnd, mfc_dc, 0)

        if result != 1:
            log("PrintWindow failed.", "warning")
            return None

        bmi = BITMAPINFO()
        bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.bmiHeader.biWidth = width
        bmi.bmiHeader.biHeight = -height
        bmi.bmiHeader.biPlanes = 1
        bmi.bmiHeader.biBitCount = 32
        bmi.bmiHeader.biCompression = 0

        buffer_size = width * height * 4
        buffer = ctypes.create_string_buffer(buffer_size)

        bits = gdi32.GetDIBits(
            mfc_dc,
            bitmap,
            0,
            height,
            buffer,
            ctypes.byref(bmi),
            0
        )

        if bits == 0:
            log("GetDIBits failed.", "warning")
            return None

        image = np.frombuffer(buffer, dtype=np.uint8)
        image = image.reshape((height, width, 4))

        return image[:, :, :3].copy()

    finally:
        gdi32.SelectObject(mfc_dc, old_bitmap)
        gdi32.DeleteObject(bitmap)
        gdi32.DeleteDC(mfc_dc)
        user32.ReleaseDC(hwnd, hwnd_dc)