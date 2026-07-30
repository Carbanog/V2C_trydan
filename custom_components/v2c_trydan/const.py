"""Constants for V2C Trydan."""

from datetime import timedelta

DOMAIN = "v2c_trydan"
CONF_IP_ADDRESS = "ip_address"
CONF_CONFIG_ENTRY_ID = "config_entry_id"

MIN_INTENSITY = 6
MAX_INTENSITY = 32
MIN_DYNAMIC_POWER_MODE = 0
MAX_DYNAMIC_POWER_MODE = 5

POLL_INTERVAL = timedelta(seconds=15)
READ_TIMEOUT = 20
COMMAND_TIMEOUT = 10
READ_RETRY_LIMIT = 3
READ_RETRY_DELAY = 2

SERVICE_SET_INTENSITY = "set_intensity"
SERVICE_SET_MIN_INTENSITY = "set_min_intensity"
SERVICE_SET_MAX_INTENSITY = "set_max_intensity"
SERVICE_SET_DYNAMIC_POWER_MODE = "set_dynamic_power_mode"
