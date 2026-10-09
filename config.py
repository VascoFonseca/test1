import logging

FIRST_WINDOW = "Projector - Source: Game Capture"
SECOND_WINDOW = "Eder Mamute"

RING_MATCH_THRESHOLD = 0.90
EMPTY_SLOT_MAX_DIFFERENCE = 15.0

RING_CHECK_INTERVAL = 1.0
RING_CLICK_COOLDOWN = 5.0

RING_TEMPLATE_FILE = "templates/ring.png"
EMPTY_SLOT_TEMPLATE_FILE = "templates/empty_slot.png"

MINIMAP_REGION = (874, 485, 108, 191)

BATTLELIST_REGION = (874, 484, 138, 90)

MATCH_THRESHOLD = 0.85

# More precise arrival detection
ARRIVAL_TOLERANCE_X = 4
ARRIVAL_TOLERANCE_Y = 4

# Destination must be centered for 3 consecutive checks
ARRIVAL_REQUIRED_CHECKS = 3
ARRIVAL_CHECK_INTERVAL = 0.1

ATTACK_KEY = "g"
LOOT_KEY = "h"

SCAN_INTERVAL = 0.2
MOVE_DELAY = 0.1
FOCUS_DELAY = 0.15

AFTER_ATTACK_DELAY = 0
AFTER_LOOT_DELAY = 0

CLICK_COOLDOWN = 1.0

RED_MIN = 120
RED_RATIO = 1.35
RED_PIXEL_THRESHOLD = 2

OCR_CONFIG = "--oem 3 --psm 6"

MOUSE_RETURN_X = 20
MOUSE_RETURN_Y = 20

LOG_FILE = "automation.log"

logger = logging.getLogger("RouteAutomation")
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    file_handler = logging.FileHandler(
        LOG_FILE,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)