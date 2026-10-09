
import time

import state
from config import (
    SCAN_INTERVAL,
    MOVE_DELAY,
    AFTER_ATTACK_DELAY,
    AFTER_LOOT_DELAY,
    ATTACK_KEY,
    LOOT_KEY,
)
from logger import log, set_state, update_status
from windows import synchronize_window_size
from battle import check_for_target, send_key_to_second_window
from navigation import (
    get_current_location,
    find_current_location,
    is_location_centered,
    click_destination,
    save_destination,
    advance_location,
    set_permanent_destination,
)
import navigation


def automation_loop():
    log("=" * 40)
    log("AUTOMATION STARTED")
    log(f"Route contains {len(state.location_templates)} locations")

    if state.permanent_destination_template:
        log(
            "Permanent destination: "
            f"{state.permanent_destination_template['name']}"
        )

    log("=" * 40)

    set_state("FIND_LOCATION", "starting automation")

    while state.running:
        try:
            if state.state == "FIND_LOCATION":
                current = get_current_location()

                if current is None:
                    time.sleep(SCAN_INTERVAL)
                    continue

                index = state.permanent_destination_index
                update_status(
                    f"Searching destination {index + 1}/"
                    f"{len(state.location_templates)}: {current['name']}"
                )

                has_target, attacking, ocr_text, red_pixels, image = (
                    check_for_target()
                )

                if has_target:
                    log("TARGET FOUND WHILE FINDING DESTINATION")
                    send_key_to_second_window(ATTACK_KEY)
                    set_state("ATTACKING", "target found before destination click")
                    update_status("Attacking target")
                    continue

                match = find_current_location()

                if match:
                    save_destination(match)

                    if click_destination(match, reason="start movement"):
                        set_state("MOVING", "destination clicked")
                        update_status(f"Moving to location {index + 1}")
                        time.sleep(MOVE_DELAY)
                else:
                    time.sleep(SCAN_INTERVAL)

            elif state.state == "MOVING":
                has_target, attacking, ocr_text, red_pixels, image = (
                    check_for_target()
                )

                if has_target:
                    log("TARGET FOUND WHILE MOVING")

                    if state.permanent_destination_template:
                        log(
                            "Permanent destination preserved: "
                            f"{state.permanent_destination_template['name']}"
                        )

                    send_key_to_second_window(ATTACK_KEY)
                    set_state("ATTACKING", "target found while moving")
                    update_status("Attacking while moving")
                    continue

                match = find_current_location()

                if match:
                    save_destination(match)

                    if navigation.is_location_centered(match):
                        log(
                            "DESTINATION REACHED - "
                            "permanent destination is centered"
                        )
                        set_state("AT_LOCATION", "destination centered")
                        update_status("At location - checking battlelist")
                    else:
                        update_status(
                            f"Moving to location "
                            f"{state.permanent_destination_index + 1}"
                        )

                time.sleep(SCAN_INTERVAL)

            elif state.state == "AT_LOCATION":
                has_target, attacking, ocr_text, red_pixels, image = (
                    check_for_target()
                )

                if has_target:
                    log("TARGET FOUND AT LOCATION")
                    send_key_to_second_window(ATTACK_KEY)
                    set_state("ATTACKING", "target found at destination")
                    update_status("Attacking")
                else:
                    log("BATTLELIST EMPTY AT LOCATION")
                    advance_location()
                    set_state("FIND_LOCATION", "location clear")
                    time.sleep(MOVE_DELAY)

            elif state.state == "ATTACKING":
                has_target, attacking, ocr_text, red_pixels, image = (
                    check_for_target()
                )

                if attacking:
                    update_status(f"Attacking - red={red_pixels}")
                    time.sleep(SCAN_INTERVAL)
                    continue

                if has_target:
                    log("TARGET STILL FOUND BUT NO RED PIXELS")
                    log("Sending G again.")
                    send_key_to_second_window(LOOT_KEY)
                    send_key_to_second_window(ATTACK_KEY)
                    
                    continue

                log("NO RED + NO TARGET = TARGET DEAD")
                update_status("Creature dead - looting")

                send_key_to_second_window(LOOT_KEY)
                send_key_to_second_window(LOOT_KEY)
                send_key_to_second_window(LOOT_KEY)

                time.sleep(AFTER_LOOT_DELAY)

                if state.permanent_destination_template:
                    log(
                        "Combat finished. Resuming permanent destination: "
                        f"{state.permanent_destination_template['name']}"
                    )
                    set_state("RESUME_MOVEMENT", "combat finished")
                else:
                    log(
                        "No permanent destination. Returning to FIND_LOCATION.",
                        "warning"
                    )
                    set_state(
                        "FIND_LOCATION",
                        "combat finished without permanent destination"
                    )

            elif state.state == "RESUME_MOVEMENT":
                has_target, attacking, ocr_text, red_pixels, image = (
                    check_for_target()
                )

                if has_target:
                    log("TARGET FOUND WHILE RESUMING MOVEMENT")
                    send_key_to_second_window(ATTACK_KEY)
                    set_state("ATTACKING", "new target found during resume")
                    update_status("Attacking during resume")
                    
                    continue

                destination = get_current_location()

                if destination is None:
                    log("RESUME: permanent destination missing", "warning")
                    set_state("FIND_LOCATION", "permanent destination missing")
                    continue

                match = find_current_location()

                if match is None:
                    log(
                        f"RESUME: '{destination['name']}' "
                        "not currently visible",
                        "debug"
                    )
                    time.sleep(SCAN_INTERVAL)
                    continue

                log(
                    f"RESUME: permanent destination matched | "
                    f"name={destination['name']} | "
                    f"confidence={match['confidence']:.3f} | "
                    f"current=({match['x']},{match['y']})"
                )

                if navigation.is_location_centered(match):
                    log("RESUME: destination already centered")
                    set_state(
                        "AT_LOCATION",
                        "permanent destination reached during combat"
                    )
                    update_status("At destination")
                    continue

                if click_destination(
                    match,
                    reason="resume permanent destination after combat"
                ):
                    set_state("MOVING", "re-clicked permanent destination")
                    update_status(
                        "Resuming movement to location "
                        f"{state.permanent_destination_index + 1}"
                    )

                time.sleep(SCAN_INTERVAL)

        except Exception as e:
            log(f"AUTOMATION ERROR: {e!r}", "error")
            update_status(f"ERROR: {e}")
            time.sleep(1)

        time.sleep(SCAN_INTERVAL)