"""
AgriVision AI - HiveMQ MQTT Client
==================================

Responsibilities:

1. Connect backend to HiveMQ Cloud using TLS.
2. Subscribe to:
      - Zone 1 sensor data
      - Zone 2 sensor data
      - Zone 1 status
      - Zone 2 status
      - Relay status
3. Forward MQTT sensor data to live_prediction.process_sensor_payload().
4. Receive relay status from ESP32.
5. Publish AI-generated relay commands.
6. Automatically reconnect if HiveMQ connection is lost.
"""

from __future__ import annotations

import json
import ssl
import threading
import time
from typing import Any, Dict, Optional

import paho.mqtt.client as mqtt

import config


# =============================================================================
# GLOBAL STATE
# =============================================================================

_client: Optional[mqtt.Client] = None

_client_lock = threading.Lock()

_started = False

_connected = False

_last_error = ""

_last_publish_time = 0.0


# =============================================================================
# DEBUG
# =============================================================================

def _log(message: str) -> None:
    print(f"[MQTT] {message}")


# =============================================================================
# MQTT CALLBACKS
# =============================================================================

def on_connect(client, userdata, flags, rc, properties=None):
    """
    Called whenever the backend connects/reconnects to HiveMQ.
    """

    global _connected

    if rc == 0:
        _connected = True

        _log(
            f"CONNECTED to HiveMQ Cloud "
            f"{config.BROKER_HOST}:{config.BROKER_PORT}"
        )

        subscriptions = [
            (config.TOPIC_ZONE1_SENSORS, config.QOS_SENSOR),
            (config.TOPIC_ZONE2_SENSORS, config.QOS_SENSOR),
            (config.TOPIC_ZONE1_STATUS, config.QOS_STATUS),
            (config.TOPIC_ZONE2_STATUS, config.QOS_STATUS),
            (config.TOPIC_RELAY_STATUS, config.QOS_STATUS),
        ]

        for topic, qos in subscriptions:
            result, mid = client.subscribe(topic, qos=qos)

            if result == mqtt.MQTT_ERR_SUCCESS:
                _log(f"SUBSCRIBED → {topic}")
            else:
                _log(
                    f"SUBSCRIBE FAILED → {topic} "
                    f"(error={result})"
                )

        # Publish retained crop & stage config on connection
        try:
            from ai_control import load_selected_crops
            selected = load_selected_crops()
            publish_crop_config(
                zone1_crop=selected.get("Zone1", "Paddy"),
                zone1_stage=selected.get("Zone1_stage", "Vegetative"),
                zone2_crop=selected.get("Zone2", "Tomato"),
                zone2_stage=selected.get("Zone2_stage", "Vegetative"),
            )
        except Exception as e:
            _log(f"Failed to publish initial crop config: {e}")

    else:
        _connected = False

        _log(
            f"CONNECTION FAILED | rc={rc}"
        )


def on_disconnect(client, userdata, disconnect_flags=None, rc=None, properties=None):
    """
    Called when connection to HiveMQ is lost.
    """

    global _connected

    _connected = False

    _log(
        f"DISCONNECTED from HiveMQ | rc={rc}"
    )


def on_message(client, userdata, msg):
    """
    Central MQTT message handler.
    """

    topic = msg.topic

    try:
        raw_payload = msg.payload.decode("utf-8").strip()
    except Exception:
        _log(
            f"Unable to decode MQTT payload from {topic}"
        )
        return

    if not raw_payload:
        return

    _log(
        f"RECEIVED ← {topic} | {raw_payload}"
    )

    # -------------------------------------------------------------------------
    # JSON payload
    # -------------------------------------------------------------------------

    try:
        payload = json.loads(raw_payload)

        if not isinstance(payload, dict):
            payload = {}

    except json.JSONDecodeError:
        _log(
            f"Invalid JSON received from {topic}"
        )
        return

    # -------------------------------------------------------------------------
    # Zone 1 sensor data
    # -------------------------------------------------------------------------

    if topic == config.TOPIC_ZONE1_SENSORS:
        _process_sensor_message(
            payload,
            default_device="zone1"
        )
        return

    # -------------------------------------------------------------------------
    # Zone 2 sensor data
    # -------------------------------------------------------------------------

    if topic == config.TOPIC_ZONE2_SENSORS:
        _process_sensor_message(
            payload,
            default_device="zone2"
        )
        return

    # -------------------------------------------------------------------------
    # Device status
    # -------------------------------------------------------------------------

    if topic in (
        config.TOPIC_ZONE1_STATUS,
        config.TOPIC_ZONE2_STATUS,
    ):
        _process_status_message(
            topic,
            payload
        )
        return

    # -------------------------------------------------------------------------
    # Relay status
    # -------------------------------------------------------------------------

    if topic == config.TOPIC_RELAY_STATUS:
        _process_relay_status(
            payload
        )
        return


# =============================================================================
# SENSOR PROCESSING
# =============================================================================

def _first_value(
    payload: Dict[str, Any],
    keys: list[str],
    default: Any = None
) -> Any:

    for key in keys:
        if key in payload:
            return payload[key]

    return default


def _process_sensor_message(
    payload: Dict[str, Any],
    default_device: str
) -> None:

    try:
        from live_prediction import (
            SensorPayload,
            process_sensor_payload,
        )

        device = str(
            _first_value(
                payload,
                ["device", "Device", "zone", "Zone"],
                default_device
            )
        )

        temperature = _first_value(
            payload,
            [
                "temperature",
                "Temperature",
                "temp",
                "Temp"
            ]
        )

        humidity = _first_value(
            payload,
            [
                "humidity",
                "Humidity",
                "hum",
                "Hum"
            ]
        )

        soil = _first_value(
            payload,
            [
                "soil",
                "Soil",
                "soil_moisture",
                "Soil_Moisture",
                "soilMoisture"
            ]
        )

        air = _first_value(
            payload,
            [
                "air",
                "Air",
                "air_quality",
                "Air_Quality",
                "mq135"
            ]
        )

        water = _first_value(
            payload,
            [
                "water",
                "Water",
                "water_level",
                "Water_Level",
                "water_percent",
                "waterPercent"
            ]
        )

        water_level = _first_value(
            payload,
            [
                "water_level",
                "Water_Level",
                "waterLevel"
            ]
        )

        water_percent = _first_value(
            payload,
            [
                "water_percent",
                "Water_Percent",
                "waterPercent"
            ]
        )

        ldr = _first_value(
            payload,
            [
                "ldr",
                "LDR",
                "light",
                "Light"
            ]
        )

        sensor_payload = SensorPayload(
            device=device,
            temperature=temperature,
            humidity=humidity,
            soil=soil,
            water=water,
            water_level=water_level,
            water_percent=water_percent,
            ldr=ldr,
            air=air,
        )

        result = process_sensor_payload(
            sensor_payload
        )

        _log(
            f"{default_device.upper()} sensor processed successfully"
        )

        if isinstance(result, dict):
            _log(
                f"AI relay result → "
                f"{result.get('relay_states', {})}"
            )

    except Exception as exc:
        _log(
            f"Sensor processing error ({default_device}): {exc}"
        )


# =============================================================================
# STATUS PROCESSING
# =============================================================================

def _process_status_message(
    topic: str,
    payload: Dict[str, Any]
) -> None:

    try:
        import live_prediction

        if "zone1" in topic:
            device = "zone1"
        elif "zone2" in topic:
            device = "zone2"
        else:
            device = None

        if not device:
            return

        status = str(
            _first_value(
                payload,
                ["status", "Status"],
                "online"
            )
        ).lower()

        if status in (
            "online",
            "connected",
            "up",
            "1"
        ):
            live_prediction.device_last_seen[
                device
            ] = time.time()

            live_prediction.system_online = True

            _log(
                f"{device.upper()} STATUS → ONLINE"
            )

        elif status in (
            "offline",
            "disconnected",
            "down",
            "0"
        ):
            live_prediction.device_last_seen[
                device
            ] = time.time()

            _log(
                f"{device.upper()} STATUS → OFFLINE"
            )

    except Exception as exc:
        _log(
            f"Status processing error: {exc}"
        )


# =============================================================================
# RELAY STATUS PROCESSING
# =============================================================================

def _process_relay_status(
    payload: Dict[str, Any]
) -> None:

    try:
        import live_prediction

        live_prediction.device_last_seen[
            "relay"
        ] = time.time()

        live_prediction.system_online = True

        relay_state = payload.get(
            "relay_states",
            payload
        )

        if isinstance(relay_state, dict):

            for key, value in relay_state.items():

                try:
                    live_prediction.latest_relay_state[
                        key
                    ] = int(float(value))
                except Exception:
                    pass

        _log(
            f"RELAY STATUS updated → "
            f"{live_prediction.latest_relay_state}"
        )

    except Exception as exc:
        _log(
            f"Relay status processing error: {exc}"
        )


# =============================================================================
# PUBLISH RELAY COMMANDS
# =============================================================================

def publish_relay_commands(
    relay_states: Dict[str, Any]
) -> bool:

    global _last_publish_time

    if not _connected or _client is None:
        _log(
            "Relay command NOT published - MQTT disconnected"
        )
        return False

    try:

        # Normalize values to 0/1
        normalized = {}

        for key, value in relay_states.items():

            try:
                normalized[key] = 1 if int(float(value)) else 0
            except Exception:
                normalized[key] = 0

        payload = {
            "type": "relay_command",
            "timestamp": int(time.time()),
            "relay_states": normalized,

            # Compatibility fields
            "water_pump": normalized.get(
                "water_pump",
                normalized.get("Zone1Pump", 0)
            ),

            "sprinkler": normalized.get(
                "sprinkler",
                0
            ),

            "zone1_fan": normalized.get(
                "zone1_fan",
                normalized.get("Zone1Fan", 0)
            ),

            "zone1_uv": normalized.get(
                "zone1_uv",
                normalized.get("Zone1UV", 0)
            ),

            "zone2_fan": normalized.get(
                "zone2_fan",
                normalized.get("Zone2Fan", 0)
            ),

            "zone2_uv": normalized.get(
                "zone2_uv",
                normalized.get("Zone2UV", 0)
            ),
        }

        encoded = json.dumps(
            payload,
            separators=(",", ":")
        )

        result = _client.publish(
            config.TOPIC_RELAY_CMD,
            encoded,
            qos=config.QOS_COMMAND,
            retain=config.RETAIN_COMMANDS
        )

        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            _log(
                f"Relay command publish FAILED | rc={result.rc}"
            )
            return False

        _last_publish_time = time.time()

        _log(
            f"PUBLISHED → {config.TOPIC_RELAY_CMD} | "
            f"{encoded}"
        )

        return True

    except Exception as exc:

        _log(
            f"Relay command publish error: {exc}"
        )

        return False


# =============================================================================
# PUBLISH CROP CONFIGURATION (RETAINED)
# =============================================================================

def publish_crop_config(
    zone1_crop: str = "Paddy",
    zone1_stage: str = "Vegetative",
    zone2_crop: str = "Tomato",
    zone2_stage: str = "Vegetative",
) -> bool:
    """
    Publishes crop and stage configuration for Zone 1 and Zone 2 to HiveMQ.
    Uses retain=True so any newly connected or rebooted ESP32 receives it instantly.
    """
    global _client, _connected

    if not _connected or _client is None:
        _log("Crop config NOT published - MQTT disconnected")
        return False

    try:
        payload = {
            "zone1_crop": str(zone1_crop),
            "zone1_stage": str(zone1_stage),
            "zone2_crop": str(zone2_crop),
            "zone2_stage": str(zone2_stage),
            "timestamp": int(time.time()),
        }

        encoded = json.dumps(payload, separators=(",", ":"))

        result = _client.publish(
            config.TOPIC_CROP_CONFIG,
            encoded,
            qos=config.QOS_STATUS,
            retain=True,
        )

        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            _log(f"Crop config publish FAILED | rc={result.rc}")
            return False

        _log(f"PUBLISHED (RETAINED) → {config.TOPIC_CROP_CONFIG} | {encoded}")
        return True

    except Exception as exc:
        _log(f"Crop config publish error: {exc}")
        return False


# =============================================================================
# MQTT CONNECTION
# =============================================================================

def create_client() -> mqtt.Client:

    global _client

    try:
        # Compatible with modern Paho versions
        client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=config.CLIENT_ID
        )

    except Exception:
        # Compatibility with older Paho versions
        client = mqtt.Client(
            client_id=config.CLIENT_ID
        )

    client.username_pw_set(
        config.BROKER_USERNAME,
        config.BROKER_PASSWORD
    )

    if config.MQTT_TLS:

        client.tls_set(
            cert_reqs=ssl.CERT_REQUIRED,
            tls_version=ssl.PROTOCOL_TLS_CLIENT
        )

        client.tls_insecure_set(False)

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    client.reconnect_delay_set(
        min_delay=1,
        max_delay=config.MQTT_RECONNECT_DELAY
    )

    _client = client

    return client


# =============================================================================
# START MQTT
# =============================================================================

def start() -> None:

    global _started

    with _client_lock:

        if _started:
            _log(
                "MQTT client already running."
            )
            return

        _started = True

    _log(
        "Starting HiveMQ MQTT client..."
    )

    while True:

        try:

            client = create_client()

            _log(
                f"Connecting to "
                f"{config.BROKER_HOST}:{config.BROKER_PORT}..."
            )

            client.connect(
                config.BROKER_HOST,
                config.BROKER_PORT,
                config.MQTT_KEEPALIVE
            )

            # Blocking loop with automatic reconnect
            client.loop_forever()

        except Exception as exc:

            global _connected

            _connected = False

            _log(
                f"MQTT connection error: {exc}"
            )

            _log(
                f"Retrying in "
                f"{config.MQTT_RECONNECT_DELAY}s..."
            )

            time.sleep(
                config.MQTT_RECONNECT_DELAY
            )


# =============================================================================
# UTILITY
# =============================================================================

def is_connected() -> bool:
    return _connected


def get_client() -> Optional[mqtt.Client]:
    return _client