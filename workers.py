import threading
import time
import numpy as np
import config
import state
from capture import capture_region
import battle
from logger import log
import re
import cv2
import numpy as np
import pytesseract
import config
import state
from capture import capture_region


class WorkerManager:
    def __init__(self):
        self._workers = {}
        self._lock = threading.Lock()

    def start(self, name, target):
        with self._lock:
            existing = self._workers.get(name)

            if existing and existing["thread"].is_alive():
                return False

            stop_event = threading.Event()

            def run():
                log(f"{name}: started")
                try:
                    target(stop_event)
                except Exception as exc:
                    log(f"{name}: worker failed: {exc!r}", "error")
                finally:
                    log(f"{name}: stopped")

            thread = threading.Thread(
                target=run,
                name=name,
                daemon=True,
            )

            self._workers[name] = {
                "thread": thread,
                "stop_event": stop_event,
            }
            thread.start()
            return True

    def stop(self, name):
        with self._lock:
            worker = self._workers.get(name)
            if worker is None:
                return

            worker["stop_event"].set()

    def is_running(self, name):
        with self._lock:
            worker = self._workers.get(name)
            return bool(worker and worker["thread"].is_alive())


def ring_worker(stop_event):
    import ring_manager

    while not stop_event.is_set():
        try:
            ring_manager.check_and_equip_ring(force=True)
            time.sleep(1)
        except Exception as exc:
            log(f"Ring manager error: {exc!r}", "error")

        stop_event.wait(0.5)

def read_vital(region, fallback_max):
    """
    Read a numeric value from a selected screen region.

    Supports '425 / 1000' and '425'.
    Returns (current, maximum), or None if OCR fails.
    """
    if region is None:
        return None

    image = capture_region(region)
    if image is None or image.size == 0:
        return None

    # Convert the captured region to grayscale.
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    # Enlarge and improve contrast for OCR.
    gray = cv2.resize(
        gray, None, fx=3, fy=3,
        interpolation=cv2.INTER_CUBIC,
    )
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    _, processed = cv2.threshold(
        gray, 0, 255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU,
    )

    text = pytesseract.image_to_string(
        processed,
        config="--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789/",
    )

    # Prefer a current/max pair, e.g. 425/1000.
    pair = re.search(r"(\d+)\s*/\s*(\d+)", text)
    if pair:
        current = int(pair.group(1))
        maximum = int(pair.group(2))
    else:
        # Otherwise use the configured maximum.
        numbers = re.findall(r"\d+", text)
        if not numbers:
            return None

        current = int(numbers[0])
        maximum = fallback_max

    if maximum <= 0 or current < 0 or current > maximum:
        return None

    return current, maximum

def bar_fill_percent(region, bar_type):
    """Estimate HP or mana percentage from a selected bar region."""
    if region is None:
        return None

    image = capture_region(region)
    if image is None or image.size == 0:
        return None

    # Sample the middle of the bar, avoiding borders.
    row = image[image.shape[0] // 2].astype(np.int16)

    blue = row[:, 0]
    green = row[:, 1]
    red = row[:, 2]

    if bar_type == "hp":
        mask = (
            (red > 100)
            & (red > green * 1.35)
            & (red > blue * 1.35)
        )
    elif bar_type == "mana":
        mask = (
            (blue > 80)
            & (blue > green * 1.15)
            & (blue > red * 1.15)
        )
    else:
        return None

    # Percentage of the selected width classified as filled.
    return float(np.count_nonzero(mask)) / len(row) * 100.0

def vital_percent(region, fallback_max):
    result = read_vital(region, fallback_max)
    if result is None:
        return None

    current, maximum = result
    return current * 100.0 / maximum

def potion_worker(stop_event):
    """Use HP and mana potions when the corresponding bar is low."""
    last_hp_potion = 0.0
    last_mana_potion = 0.0

    while not stop_event.is_set():
        try:
            hp = bar_fill_percent(state.hp_bar_region, "hp")
            mana = bar_fill_percent(state.mana_bar_region, "mana")
            now = time.monotonic()

            if hp is not None:
                if (
                    hp <= config.HP_POTION_THRESHOLD
                    and now - last_hp_potion >= config.POTION_COOLDOWN
                ):
                    log(f"Low HP ({hp:.1f}%): using HP potion")
                    battle.send_key_to_second_window(
                        config.HP_POTION_KEY
                    )
                    last_hp_potion = time.monotonic()

            if mana is not None:
                if (
                    mana <= config.MANA_POTION_THRESHOLD
                    and now - last_mana_potion >= config.POTION_COOLDOWN
                ):
                    log(f"Low mana ({mana:.1f}%): using mana potion")
                    battle.send_key_to_second_window(
                        config.MANA_POTION_KEY
                    )
                    last_mana_potion = time.monotonic()

        except Exception as exc:
            log(f"Potion worker error: {exc!r}", "error")

        stop_event.wait(config.VITALS_CHECK_INTERVAL)


def magic_training_worker(stop_event):
    """Continuously cast the configured spell while mana is sufficient."""
    log("Magic training worker loop started")

    while not stop_event.is_set():
        try:
            mana = bar_fill_percent(
                state.mana_bar_region,
                "mana",
            )

            if mana is None:
                log("Magic training: could not read mana")
                stop_event.wait(0.5)
                continue

            log(f"Magic training: mana is {mana:.1f}%")

            if mana >= config.MAGIC_MIN_MANA_PERCENT:
                log("Magic training: sending spell hotkey")

                battle.send_key_to_second_window(
                    config.MAGIC_SPELL_KEY
                )

                # Wait between casts, but wake immediately when stopped.
                stop_event.wait(config.MAGIC_CAST_INTERVAL)
            else:
                log("Magic training: mana too low; waiting")
                stop_event.wait(0.5)

        except Exception as exc:
            log(f"Magic training error: {exc!r}", "error")
            stop_event.wait(1.0)

    log("Magic training worker loop ended")
manager = WorkerManager()