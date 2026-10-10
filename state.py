import config

minimap_region = config.MINIMAP_REGION
battlelist_region = config.BATTLELIST_REGION

running = False
state = "STOPPED"
ui = None

ring_source_region = None
ring_equipment_region = None
backpack_slot_region = None
ring_equipment_region = (860, 236, 33, 33)
backpack_slot_region = (18, 485, 146, 183)
last_ring_check_time = 0.0
last_ring_click_time = 0.0

location_templates = []

current_location_index = 0

permanent_destination_index = None
permanent_destination_template = None

current_destination_match = None


last_click_time = 0