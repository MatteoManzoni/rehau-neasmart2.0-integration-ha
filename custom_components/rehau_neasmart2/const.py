"""Constants for the Rehau Neasmart 2.0 integration."""

DOMAIN = "rehau_neasmart2"
MAX_BASES = 5
MAX_ZONES_PER_BASE = 12
MAX_ZONES = MAX_BASES * MAX_ZONES_PER_BASE
BINARY_STATUSES = {
    0: "Off",
    1: "On"
}
PRESENCE_STATES = {
    True: "Present",
    False: "Not Present"
}
PRESET_STATES_MAPPING = {
    "Normal": 1,
    "Reduced": 2,
    "Standby": 3,
    "Time Program": 4,
    "Party": 5,
    "Absence": 6
}
PRESET_STATES_MAPPING_REVERSE = {v: k for k, v in PRESET_STATES_MAPPING.items()}
PRESET_CLIMATE_MODES_MAPPING = {
    "Auto": 1,
    "Heating": 2,
    "Cooling": 3,
    "Forced Heating": 4,
    "Forced Cooling": 5
}
PRESET_CLIMATE_MODES_MAPPING_REVERSE = {v: k for k, v in PRESET_CLIMATE_MODES_MAPPING.items()}
REQUEST_TIMEOUT_SECONDS = 5
ENDPOINT_CACHE_TTL_SECONDS = 1
MIN_REASONABLE_TEMPERATURE = -50
MAX_REASONABLE_TEMPERATURE = 120
