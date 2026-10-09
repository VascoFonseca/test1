import json
import os
import re

PROFILE_DIR = "profiles"


def ensure_profile_dir():
    os.makedirs(PROFILE_DIR, exist_ok=True)


def safe_filename(name):
    name = name.strip()
    name = re.sub(r'[<>:"/\\|?*]', "_", name)

    if not name:
        raise ValueError("Profile name cannot be empty.")

    return name


def save_profile(name, minimap_region, battlelist_region,
                 location_templates):
    ensure_profile_dir()

    filename = safe_filename(name) + ".json"
    path = os.path.join(PROFILE_DIR, filename)

    data = {
        "name": name.strip(),
        "minimap_region": minimap_region,
        "battlelist_region": battlelist_region,
        "locations": [
            location["file"]
            for location in location_templates
        ],
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

    return path


def load_profile(name):
    ensure_profile_dir()

    filename = safe_filename(name) + ".json"
    path = os.path.join(PROFILE_DIR, filename)

    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"Profile not found: {name}"
        )

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def list_profiles():
    ensure_profile_dir()

    return sorted(
        filename[:-5]
        for filename in os.listdir(PROFILE_DIR)
        if filename.lower().endswith(".json")
    )