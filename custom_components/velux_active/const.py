DOMAIN = "velux_active"
PLATFORMS = ["sensor", "binary_sensor"]

CONF_ACCOUNT = "account"
CONF_PASSWORD = "password"
CONF_TOKEN = "token"
CONF_TOKEN_TIME = "token_time"

STORAGE_VERSION = 1

# If API has been failing continuously for longer than this, entities become unavailable.
FAIL_UNAVAILABLE_AFTER_SECONDS = 60 * 60  # 1 hour

# Default polling interval (seconds)
DEFAULT_UPDATE_INTERVAL_SECONDS = 300
