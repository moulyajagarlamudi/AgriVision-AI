import json
import os
import re
import socket
import threading
import time

from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import FastAPI
from pydantic import BaseModel

from ai_control import (
    CropAutomationController,
    load_selected_crops,
    CROP_CONFIGURATIONS,
)

from mongo_logger import (
    check_and_fire_notifications,
    insert_automation_event,
    insert_telemetry_snapshot,
)


# =============================================================================
# FASTAPI APP
# =============================================================================

app = FastAPI(
    title="AgriVision AI - MQTT Telemetry Backend"
)


# =============================================================================
# CONTROLLER
# =============================================================================

controller = CropAutomationController()

print(
    "[INIT] Crop-aware AI controller loaded successfully."
)


# =============================================================================
# CONSTANTS
# =============================================================================

DATA_TIMEOUT_SECONDS = 8.0


# =============================================================================
# GLOBAL TELEMETRY STATE
# =============================================================================

last_common_water_level = 0.0

latest_zone_data: Dict[str, Dict[str, Any]] = {}

device_last_seen: Dict[str, float] = {
    "zone1": 0.0,
    "zone2": 0.0,
    "relay": 0.0,
}


latest_relay_state: Dict[str, int] = {
    "water_pump": 0,
    "sprinkler": 0,

    "zone1_fan": 0,
    "zone1_uv": 0,
    "zone1_light": 0,
    "zone1_sprinkler": 0,

    "zone2_fan": 0,
    "zone2_uv": 0,
    "zone2_light": 0,
    "zone2_sprinkler": 0,

    "Zone1Pump": 0,
    "Zone1Fan": 0,
    "Zone1UV": 0,
    "Zone1Sprinkler": 0,

    "Zone2Pump": 0,
    "Zone2Fan": 0,
    "Zone2UV": 0,
    "Zone2Sprinkler": 0,
}


prev_decision1 = {
    "pump": 0,
    "fan": 0,
    "uv": 0,
}


prev_decision2 = {
    "pump": 0,
    "fan": 0,
    "uv": 0,
}


first_cycle = True

system_online = False


# =============================================================================
# PAYLOAD MODELS
# =============================================================================

class SensorPayload(BaseModel):

    device: str

    temperature: Optional[float] = None

    humidity: Optional[float] = None

    soil: Optional[float] = None

    water: Optional[float] = None

    water_level: Optional[float] = None

    water_percent: Optional[float] = None

    ldr: Optional[float] = None

    air: Optional[float] = None


class RelayTelemetryPayload(BaseModel):

    water: Optional[float] = None

    water_level: Optional[float] = None

    water_percent: Optional[float] = None

    raw_adc: Optional[int] = None


# =============================================================================
# SAFE CONVERSION HELPERS
# =============================================================================

def safe_float(
    value: Any,
    default: float = 0.0
) -> float:

    try:

        if value is None:
            return default

        return float(value)

    except Exception:

        return default


def safe_int(
    value: Any,
    default: int = 0
) -> int:

    try:

        if value is None:
            return default

        return int(float(value))

    except Exception:

        return default


# =============================================================================
# WATER LEVEL NORMALIZATION
# =============================================================================

def normalize_water_level(
    raw_value: Optional[float],
    fallback: float
) -> float:

    if raw_value is None:
        return fallback

    try:

        value = float(raw_value)

    except Exception:

        return fallback

    if 0 <= value <= 100:

        return value

    if value > 100:

        return max(
            0.0,
            min(
                100.0,
                value / 40.95
            )
        )

    return fallback


# =============================================================================
# LOCAL IP
# =============================================================================

def get_local_ip() -> str:

    try:

        s = socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM
        )

        s.connect(
            ("8.8.8.8", 80)
        )

        ip = s.getsockname()[0]

        s.close()

        return ip

    except Exception:

        return "127.0.0.1"


# =============================================================================
# ZERO DASHBOARD
# =============================================================================

def build_zero_dashboard() -> Dict[str, Any]:

    return {

        "Zone1": {
            "Zone": "Zone1",
            "Temperature": 0.0,
            "Humidity": 0.0,
            "Soil_Moisture": 0.0,
            "Air": 0,
            "Water_Level": 0.0,
        },

        "Zone2": {
            "Zone": "Zone2",
            "Temperature": 0.0,
            "Humidity": 0.0,
            "Soil_Moisture": 0.0,
            "Air": 0,
            "Water_Level": 0.0,
        },

        "Relay": {
            "water_pump": 0,
            "sprinkler": 0,

            "Zone1Pump": 0,
            "Zone1Fan": 0,
            "Zone1UV": 0,
            "Zone1Sprinkler": 0,

            "Zone2Pump": 0,
            "Zone2Fan": 0,
            "Zone2UV": 0,
            "Zone2Sprinkler": 0,
        },

        "Common_Water_Level": 0.0,

        "Timestamp": datetime.now().strftime(
            "%H:%M:%S"
        ),

        "status": "offline",
    }


# =============================================================================
# STATE FILES
# =============================================================================

def write_state_files(
    dashboard: Dict[str, Any],
    status: str = "online"
) -> None:

    payload = dict(dashboard)

    payload["status"] = status

    try:

        with open(
            "system_status.json",
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                {
                    "status": status
                },
                f,
                indent=4
            )

    except Exception as exc:

        print(
            f"[STATE] system_status.json error: {exc}"
        )

    tmp_path = "latest_data.tmp"

    target_path = "latest_data.json"

    try:

        with open(
            tmp_path,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                payload,
                f,
                indent=4
            )

        try:

            os.replace(
                tmp_path,
                target_path
            )

        except PermissionError:

            with open(
                target_path,
                "w",
                encoding="utf-8"
            ) as f:

                json.dump(
                    payload,
                    f,
                    indent=4
                )

    except Exception as exc:

        print(
            f"[STATE] latest_data.json error: {exc}"
        )


# =============================================================================
# DASHBOARD PAYLOAD
# =============================================================================

def publish_dashboard_payload(
    zone1_data: Dict[str, Any],
    zone2_data: Dict[str, Any],
    relay_state: Dict[str, int],
    common_water_level: float,
    status: str = "online",
) -> Dict[str, Any]:

    dashboard = {

        "Zone1": dict(zone1_data),

        "Zone2": dict(zone2_data),

        "Relay": dict(relay_state),

        "Common_Water_Level":
            common_water_level,

        "Timestamp":
            datetime.now().strftime("%H:%M:%S"),

        "status":
            status,
    }

    write_state_files(
        dashboard,
        status=status
    )

    return dashboard


# =============================================================================
# OFFLINE STATE
# =============================================================================

def update_offline_state() -> None:

    global system_online
    global latest_relay_state

    if system_online:

        system_online = False

        print(
            "[MONITOR] All ESP32 devices timed out "
            "→ SYSTEM OFFLINE"
        )

    # Force dashboard relays OFF
    for key in latest_relay_state:

        latest_relay_state[key] = 0

    # IMPORTANT:
    # Also publish OFF command to relay ESP32.
    try:

        import mqtt_client

        mqtt_client.publish_relay_commands(
            latest_relay_state
        )

        print(
            "[MONITOR] Emergency relay OFF command published."
        )

    except Exception as exc:

        print(
            f"[MONITOR] Unable to publish emergency OFF: {exc}"
        )

    write_state_files(
        build_zero_dashboard(),
        status="offline"
    )


# =============================================================================
# SENSOR PROCESSING
# =============================================================================

def process_sensor_payload(
    payload: SensorPayload
) -> Dict[str, Any]:

    global latest_zone_data
    global last_common_water_level
    global latest_relay_state
    global prev_decision1
    global prev_decision2
    global first_cycle
    global system_online

    # -------------------------------------------------------------------------
    # Identify zone
    # -------------------------------------------------------------------------

    dev_raw = (
        payload.device
        .lower()
        .strip()
        .replace(" ", "")
        .replace("_", "")
    )

    if (
        "zone2" in dev_raw
        or "rack2" in dev_raw
        or dev_raw == "2"
    ):

        device_key = "zone2"

        zone_name = "Zone2"

    else:

        device_key = "zone1"

        zone_name = "Zone1"

    # -------------------------------------------------------------------------
    # Update device heartbeat
    # -------------------------------------------------------------------------

    device_last_seen[
        device_key
    ] = time.time()

    system_online = True

    # -------------------------------------------------------------------------
    # Build sensor data
    # -------------------------------------------------------------------------

    zone_data = {

        "Zone":
            zone_name,

        "Temperature":
            safe_float(
                payload.temperature
            ),

        "Humidity":
            safe_float(
                payload.humidity
            ),

        "Soil_Moisture":
            safe_float(
                payload.soil
            ),

        "Air":
            safe_int(
                payload.air
            ),

        "Water_Level":
            0.0,
    }

    # -------------------------------------------------------------------------
    # Water level
    # -------------------------------------------------------------------------

    raw_water = (
        payload.water_level
        if payload.water_level is not None
        else payload.water
    )

    if payload.water_percent is not None:

        raw_water = payload.water_percent

    if raw_water is not None:

        last_common_water_level = (
            normalize_water_level(
                raw_water,
                last_common_water_level
            )
        )

    zone_data[
        "Water_Level"
    ] = last_common_water_level

    latest_zone_data[
        zone_name
    ] = zone_data

    print(
        f"[MQTT SENSOR] {zone_name} | "
        f"Temp={zone_data['Temperature']:.2f}°C | "
        f"Humidity={zone_data['Humidity']:.2f}% | "
        f"Soil={zone_data['Soil_Moisture']:.2f}% | "
        f"Air={zone_data['Air']} | "
        f"Tank={last_common_water_level:.2f}%"
    )

    # -------------------------------------------------------------------------
    # Prepare both zones
    # -------------------------------------------------------------------------

    zone1_data = latest_zone_data.get(
        "Zone1",
        {
            "Zone": "Zone1",
            "Temperature": 0.0,
            "Humidity": 0.0,
            "Soil_Moisture": 0.0,
            "Air": 0,
            "Water_Level":
                last_common_water_level,
        }
    )

    zone2_data = latest_zone_data.get(
        "Zone2",
        {
            "Zone": "Zone2",
            "Temperature": 0.0,
            "Humidity": 0.0,
            "Soil_Moisture": 0.0,
            "Air": 0,
            "Water_Level":
                last_common_water_level,
        }
    )

    zone1_data[
        "Water_Level"
    ] = last_common_water_level

    zone2_data[
        "Water_Level"
    ] = last_common_water_level

    zone1_ready = "Zone1" in latest_zone_data
    zone2_ready = "Zone2" in latest_zone_data

    selected_crops = load_selected_crops()

    # =========================================================================
    # FIRST CYCLE SAFE STATE
    # =========================================================================

    if first_cycle:

        decision1 = {
            "pump": 0,
            "fan": 0,
            "uv": 0
        }

        decision2 = {
            "pump": 0,
            "fan": 0,
            "uv": 0
        }

        water_pump = 0

        sprinkler = 0

        zone1_sprinkler = 0

        zone2_sprinkler = 0

        first_cycle = False

        print(
            "[AI] First sensor cycle → "
            "ALL ACTUATORS OFF"
        )

    else:

        # =====================================================================
        # AI FAN / UV DECISIONS
        # =====================================================================

        decision1 = (

            controller.decide_for_zone(
                zone1_data,
                selected_crops.get(
                    "Zone1",
                    "Tomato"
                )
            )

            if zone1_ready

            else {
                "pump": 0,
                "fan": 0,
                "uv": 0
            }
        )

        decision2 = (

            controller.decide_for_zone(
                zone2_data,
                selected_crops.get(
                    "Zone2",
                    "Tomato"
                )
            )

            if zone2_ready

            else {
                "pump": 0,
                "fan": 0,
                "uv": 0
            }
        )

        # =====================================================================
        # CENTRAL WATER PUMP
        # =====================================================================

        # Pump ON when tank < 30%.
        # Pump OFF when tank >= 30%.

        water_pump = int(
            last_common_water_level < 30.0
        )

        # =====================================================================
        # SHARED SPRINKLER
        # =====================================================================

        crop1 = selected_crops.get(
            "Zone1",
            "Tomato"
        )

        crop2 = selected_crops.get(
            "Zone2",
            "Tomato"
        )

        c1 = CROP_CONFIGURATIONS.get(
            crop1,
            CROP_CONFIGURATIONS["Tomato"]
        )

        c2 = CROP_CONFIGURATIONS.get(
            crop2,
            CROP_CONFIGURATIONS["Tomato"]
        )

        z1_soil = safe_float(
            zone1_data.get(
                "Soil_Moisture"
            )
        )

        z2_soil = safe_float(
            zone2_data.get(
                "Soil_Moisture"
            )
        )

        z1_target = safe_float(
            c1.get(
                "soil_moisture",
                60
            )
        )

        z2_target = safe_float(
            c2.get(
                "soil_moisture",
                60
            )
        )

        z1_overwatered = (
            zone1_ready
            and z1_soil >= z1_target
        )

        z2_overwatered = (
            zone2_ready
            and z2_soil >= z2_target
        )

        # ---------------------------------------------------------------------
        # Shared sprinkler safety
        # ---------------------------------------------------------------------

        if (
            z1_overwatered
            or z2_overwatered
        ):

            zone1_sprinkler = 0
            zone2_sprinkler = 0
            sprinkler = 0

            print(
                "[AI] OVERWATER GUARD → "
                "SHARED SPRINKLER OFF"
            )

        else:

            zone1_sprinkler = int(
                zone1_ready
                and z1_soil < z1_target
            )

            zone2_sprinkler = int(
                zone2_ready
                and z2_soil < z2_target
            )

            sprinkler = int(
                zone1_sprinkler
                or zone2_sprinkler
            )

        print(
            f"[AI] Tank={last_common_water_level:.1f}% → "
            f"Central Pump="
            f"{'ON' if water_pump else 'OFF'} | "

            f"Z1 Soil={z1_soil:.1f}%/"
            f"{z1_target}% → "
            f"Sprinkler="
            f"{'ON' if zone1_sprinkler else 'OFF'} | "

            f"Z2 Soil={z2_soil:.1f}%/"
            f"{z2_target}% → "
            f"Sprinkler="
            f"{'ON' if zone2_sprinkler else 'OFF'}"
        )

        # =====================================================================
        # AUTOMATION EVENT LOGGING
        # =====================================================================

        for zone_label, curr, prev in [

            (
                "Zone1",
                decision1,
                prev_decision1
            ),

            (
                "Zone2",
                decision2,
                prev_decision2
            ),

        ]:

            for actuator in [
                "pump",
                "fan",
                "uv"
            ]:

                cur_state = int(
                    curr.get(
                        actuator,
                        0
                    )
                )

                prev_state = int(
                    prev.get(
                        actuator,
                        0
                    )
                )

                if cur_state != prev_state:

                    action = (
                        "ON"
                        if cur_state
                        else "OFF"
                    )

                    sensor_values = (
                        zone1_data
                        if zone_label == "Zone1"
                        else zone2_data
                    )

                    insert_automation_event(

                        zone=zone_label,

                        actuator=actuator.capitalize(),

                        action=action,

                        reason=(
                            f"AI decision changed "
                            f"{actuator.upper()} "
                            f"to {action}"
                        ),

                        sensor_values={

                            "temperature":
                                sensor_values.get(
                                    "Temperature"
                                ),

                            "humidity":
                                sensor_values.get(
                                    "Humidity"
                                ),

                            "soil":
                                sensor_values.get(
                                    "Soil_Moisture"
                                ),

                            "air":
                                sensor_values.get(
                                    "Air"
                                ),
                        },

                        crop=selected_crops.get(
                            zone_label,
                            "Unknown"
                        )
                    )

        prev_decision1 = decision1.copy()

        prev_decision2 = decision2.copy()

    # =========================================================================
    # BUILD FINAL RELAY STATE
    # =========================================================================

    latest_relay_state = {

        "water_pump":
            int(water_pump),

        "sprinkler":
            int(sprinkler),

        "zone1_fan":
            int(
                decision1.get(
                    "fan",
                    0
                )
            ),

        "zone1_uv":
            int(
                decision1.get(
                    "uv",
                    0
                )
            ),

        "zone1_light":
            int(
                decision1.get(
                    "uv",
                    0
                )
            ),

        "zone1_sprinkler":
            int(zone1_sprinkler),

        "zone2_fan":
            int(
                decision2.get(
                    "fan",
                    0
                )
            ),

        "zone2_uv":
            int(
                decision2.get(
                    "uv",
                    0
                )
            ),

        "zone2_light":
            int(
                decision2.get(
                    "uv",
                    0
                )
            ),

        "zone2_sprinkler":
            int(zone2_sprinkler),

        # ---------------------------------------------------------------------
        # Existing dashboard-compatible names
        # ---------------------------------------------------------------------

        "Zone1Pump":
            int(water_pump),

        "Zone1Fan":
            int(
                decision1.get(
                    "fan",
                    0
                )
            ),

        "Zone1UV":
            int(
                decision1.get(
                    "uv",
                    0
                )
            ),

        "Zone1Sprinkler":
            int(zone1_sprinkler),

        "Zone2Pump":
            int(water_pump),

        "Zone2Fan":
            int(
                decision2.get(
                    "fan",
                    0
                )
            ),

        "Zone2UV":
            int(
                decision2.get(
                    "uv",
                    0
                )
            ),

        "Zone2Sprinkler":
            int(zone2_sprinkler),
    }

    # =========================================================================
    # MQTT RELAY COMMAND
    # =========================================================================

    try:

        import mqtt_client

        success = (
            mqtt_client.publish_relay_commands(
                latest_relay_state
            )
        )

        if not success:

            print(
                "[MQTT] Relay command could not be sent."
            )

    except Exception as exc:

        print(
            f"[MQTT] Relay command error: {exc}"
        )

    # =========================================================================
    # DASHBOARD
    # =========================================================================

    dashboard = publish_dashboard_payload(

        zone1_data,

        zone2_data,

        latest_relay_state,

        last_common_water_level,

        status="online"
    )

    # =========================================================================
    # NOTIFICATIONS
    # =========================================================================

    check_and_fire_notifications(
        dashboard,
        selected_crops
    )

    # =========================================================================
    # MONGODB HISTORY
    # =========================================================================

    insert_telemetry_snapshot(
        dashboard,
        selected_crops
    )

    return {

        "status":
            "ok",

        "device":
            zone_name,

        "relay_states":
            latest_relay_state,

        "common_water_level":
            last_common_water_level,

        "timestamp":
            dashboard.get(
                "Timestamp"
            ),
    }


# =============================================================================
# BACKWARD-COMPATIBLE HTTP ENDPOINTS
# =============================================================================

@app.post("/api/esp32/zone1")
def receive_zone1(
    payload: SensorPayload
) -> Dict[str, Any]:

    return process_sensor_payload(
        payload
    )


@app.post("/api/esp32/zone2")
def receive_zone2(
    payload: SensorPayload
) -> Dict[str, Any]:

    return process_sensor_payload(
        payload
    )


@app.post("/api/esp32/relay/telemetry")
def receive_relay_telemetry(
    payload: RelayTelemetryPayload
) -> Dict[str, Any]:

    global last_common_water_level
    global system_online

    device_last_seen[
        "relay"
    ] = time.time()

    system_online = True

    raw_water = (
        payload.water_level
        if payload.water_level is not None
        else payload.water
    )

    if payload.water_percent is not None:

        raw_water = payload.water_percent

    if raw_water is not None:

        last_common_water_level = (
            normalize_water_level(
                raw_water,
                last_common_water_level
            )
        )

    for zone_data in latest_zone_data.values():

        zone_data[
            "Water_Level"
        ] = last_common_water_level

    zone1_data = latest_zone_data.get(
        "Zone1",
        {
            "Zone": "Zone1",
            "Temperature": 0.0,
            "Humidity": 0.0,
            "Soil_Moisture": 0.0,
            "Air": 0,
            "Water_Level":
                last_common_water_level
        }
    )

    zone2_data = latest_zone_data.get(
        "Zone2",
        {
            "Zone": "Zone2",
            "Temperature": 0.0,
            "Humidity": 0.0,
            "Soil_Moisture": 0.0,
            "Air": 0,
            "Water_Level":
                last_common_water_level
        }
    )

    publish_dashboard_payload(

        zone1_data,

        zone2_data,

        latest_relay_state,

        last_common_water_level,

        status="online"
    )

    print(
        f"[RELAY TELEMETRY] "
        f"Tank={last_common_water_level:.1f}%"
    )

    return {

        "status":
            "ok",

        "common_water_level":
            last_common_water_level,

        "raw_adc":
            payload.raw_adc,
    }


# =============================================================================
# RELAY COMMAND HTTP FALLBACK
# =============================================================================

@app.get("/api/esp32/relay/commands")
def relay_commands() -> Dict[str, Any]:

    return {

        "status":
            "ok",

        "relay_states":
            latest_relay_state,

        "common_water_level":
            last_common_water_level,

        "timestamp":
            datetime.now().strftime(
                "%H:%M:%S"
            ),
    }


# =============================================================================
# CONNECTION MONITOR
# =============================================================================

def monitor_connection_health() -> None:

    global system_online

    while True:

        try:

            now = time.time()

            active_devices = {

                device: timestamp

                for device, timestamp
                in device_last_seen.items()

                if timestamp > 0
            }

            if active_devices:

                any_fresh = any(

                    (
                        now - timestamp
                    )
                    <= DATA_TIMEOUT_SECONDS

                    for timestamp
                    in active_devices.values()
                )

                if any_fresh:

                    if not system_online:

                        system_online = True

                        print(
                            "[MONITOR] Device "
                            "reconnected → ONLINE"
                        )

                else:

                    if system_online:

                        update_offline_state()

            time.sleep(2.0)

        except Exception as exc:

            print(
                f"[MONITOR] Error: {exc}"
            )

            time.sleep(2.0)


# =============================================================================
# DIRECT EXECUTION
# =============================================================================

def main() -> None:

    import uvicorn

    local_ip = get_local_ip()

    print(
        "\n"
        + "=" * 75
    )

    print(
        " AgriVision AI - MQTT Backend"
    )

    print(
        f" Dashboard: "
        f"http://{local_ip}:8000"
    )

    print(
        f" HTTP fallback: "
        f"http://{local_ip}:8001"
    )

    print(
        "=" * 75
        + "\n"
    )

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        reload=False,
        log_level="info"
    )


if __name__ == "__main__":
    main()