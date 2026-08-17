import os

# =============================================================================
# AgriVision AI - HiveMQ Cloud MQTT Configuration
# =============================================================================

# Load .env if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# =============================================================================
# HIVE MQ CLOUD
# =============================================================================

BROKER_HOST = os.getenv(
    "MQTT_BROKER_HOST",
    "67000403e5584b348d982f289c69b053.s1.eu.hivemq.cloud"
)

BROKER_PORT = int(
    os.getenv("MQTT_BROKER_PORT", "8883")
)

BROKER_USERNAME = os.getenv(
    "MQTT_BROKER_USERNAME",
    "Agrivision"
)

BROKER_PASSWORD = os.getenv(
    "MQTT_BROKER_PASSWORD",
    "mouls1234"
)

# HiveMQ Cloud port 8883 requires TLS
MQTT_TLS = True

# MQTT keepalive
MQTT_KEEPALIVE = int(
    os.getenv("MQTT_KEEPALIVE", "60")
)

# Backend reconnect delay
MQTT_RECONNECT_DELAY = int(
    os.getenv("MQTT_RECONNECT_DELAY", "5")
)


# =============================================================================
# MQTT TOPICS
# =============================================================================

# ----------------------------- Sensor Data ----------------------------------

TOPIC_ZONE1_SENSORS = "agrivision/zone1/sensors"
TOPIC_ZONE2_SENSORS = "agrivision/zone2/sensors"

# ----------------------------- Device Status --------------------------------

TOPIC_ZONE1_STATUS = "agrivision/zone1/status"
TOPIC_ZONE2_STATUS = "agrivision/zone2/status"
TOPIC_RELAY_STATUS = "agrivision/relay/status"

# ----------------------------- Relay Commands & Config ----------------------

TOPIC_RELAY_CMD = "agrivision/relay/commands"
TOPIC_CROP_CONFIG = "agrivision/config/crops"


# =============================================================================
# MQTT QoS
# =============================================================================

QOS_SENSOR = 0
QOS_STATUS = 1
QOS_COMMAND = 1


# =============================================================================
# OFFLINE DETECTION
# =============================================================================

# ESP32 is considered stale after this many seconds without telemetry/status.
OFFLINE_TIMEOUT = 8.0


# =============================================================================
# MQTT CLIENT
# =============================================================================

CLIENT_ID = os.getenv(
    "MQTT_CLIENT_ID",
    "agrivision-backend"
)

# Do not retain relay commands.
# A newly connected relay should not execute an old command.
RETAIN_COMMANDS = False

# Sensor data should not be retained.
RETAIN_SENSOR_DATA = False

# Status messages can be retained.
RETAIN_STATUS = True