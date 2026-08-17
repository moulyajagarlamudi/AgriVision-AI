import json
import os
import re
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

from ai_control import CropAutomationController, load_selected_crops
from mongo_logger import check_and_fire_notifications, insert_automation_event, insert_telemetry_snapshot


app = FastAPI()
controller = CropAutomationController()
print("Crop-aware rule-based AI controller loaded.")

DATA_TIMEOUT_SECONDS = 8.0

last_common_water_level = 0.0
latest_zone_data: Dict[str, Dict[str, Any]] = {}
device_last_seen: Dict[str, float] = {"zone1": 0.0, "zone2": 0.0, "relay": 0.0}
latest_relay_state: Dict[str, int] = {
    "Zone1Pump": 0,
    "Zone1Fan": 0,
    "Zone1UV": 0,
    "Zone2Pump": 0,
    "Zone2Fan": 0,
    "Zone2UV": 0,
}
prev_decision1 = {"pump": 0, "fan": 0, "uv": 0}
prev_decision2 = {"pump": 0, "fan": 0, "uv": 0}
first_cycle = True
system_online = False


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


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(float(value))
    except Exception:
        return default


def normalize_water_level(raw_value: Optional[float], fallback: float) -> float:
    if raw_value is None:
        return fallback
    try:
        value = float(raw_value)
    except Exception:
        return fallback
    if 0 <= value <= 100:
        return value
    if value > 100:
        return max(0.0, min(100.0, value / 40.95))
    return fallback


# Compatibility helpers for existing tests and local callers.
def resolve_port_candidates(port_env_name: str, defaults: Optional[List[str]] = None) -> List[str]:
    env_port = os.getenv(port_env_name, "").strip()
    candidates: List[str] = []
    if env_port:
        candidates.append(env_port)
    for port in (defaults or []) + ["COM6", "COM7", "COM11", "COM4", "COM5"]:
        if port and port not in candidates:
            candidates.append(port)
    return candidates


def _number(value: Any) -> float:
    match = re.search(r"[-+]?\d*\.?\d+", str(value))
    if not match:
        raise ValueError(f"No numeric value in {value!r}")
    return float(match.group())


def _parse_sensor_packet(line: str, expected_zone: str) -> Dict[str, Any]:
    line = line.strip()
    if not line:
        raise ValueError("empty packet")
    parts = [value.strip() for value in line.split(",")]
    if not parts:
        raise ValueError("empty packet")

    zone_field = parts[0]
    if " " in zone_field:
        zone_field = zone_field.split()[-1]

    if not zone_field.lower().startswith("zone"):
        raise ValueError(f"non-zone packet: {parts[0]!r}")

    if zone_field.lower() != expected_zone.lower():
        raise ValueError(f"zone mismatch: expected {expected_zone!r}, got {zone_field!r}")

    if len(parts) < 5:
        raise ValueError(f"unexpected field count: {len(parts)}")

    return {
        "Zone": expected_zone,
        "Temperature": _number(parts[1]),
        "Humidity": _number(parts[2]),
        "Soil_Moisture": _number(parts[3]),
        "Air": int(_number(parts[4])),
        "Soil_Raw": "N/A",
    }


def _parse_relay_packet(line: str) -> Any:
    line = line.strip()
    if not line:
        raise ValueError("empty relay packet")

    labelled_value = re.search(
        r"(?:water(?:\s*(?:level|tank))?|tank)\s*[:,=]\s*(\d{1,3}(?:\.\d+)?)\s*%?",
        line,
        re.IGNORECASE,
    )
    if labelled_value:
        return float(labelled_value.group(1))

    bare_value = re.fullmatch(r"\s*(\d{1,3}(?:\.\d+)?)\s*%?\s*", line)
    if not bare_value:
        raise ValueError(f"unrecognized relay packet: {line!r}")
    if line.strip() == "0":
        raise ValueError("ignored zero relay echo")
    return float(bare_value.group(1))


def read_sensor_data(port: Any, expected_zone: str, fallback: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    deadline = time.time() + 0.15
    while time.time() < deadline:
        if getattr(port, "in_waiting", 0) > 0:
            buffered_lines: List[str] = []
            while getattr(port, "in_waiting", 0) > 0:
                line = port.readline()
                if isinstance(line, bytes):
                    line = line.decode(errors="ignore").strip()
                else:
                    line = str(line).strip()
                if line:
                    buffered_lines.append(line)
            for line in reversed(buffered_lines):
                try:
                    return _parse_sensor_packet(line, expected_zone)
                except ValueError:
                    continue
        if fallback is not None:
            return fallback
        time.sleep(0.005)

    if fallback is not None:
        return fallback
    raise Exception(f"Sensor {expected_zone} Disconnected")


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
            "Zone1Pump": 0,
            "Zone1Fan": 0,
            "Zone1UV": 0,
            "Zone2Pump": 0,
            "Zone2Fan": 0,
            "Zone2UV": 0,
        },
        "Common_Water_Level": 0.0,
        "Timestamp": datetime.now().strftime("%H:%M:%S"),
        "status": "offline",
    }


def write_state_files(dashboard: Dict[str, Any], status: str = "online") -> None:
    payload = dict(dashboard)
    payload["status"] = status

    with open("system_status.json", "w", encoding="utf-8") as f:
        json.dump({"status": status}, f, indent=4)

    tmp_path = "latest_data.tmp"
    target_path = "latest_data.json"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=4)

    try:
        os.replace(tmp_path, target_path)
    except PermissionError:
        try:
            with open(target_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=4)
        except Exception:
            pass


def publish_dashboard_payload(zone1_data: Dict[str, Any], zone2_data: Dict[str, Any], relay_state: Dict[str, int], common_water_level: float, status: str = "online") -> Dict[str, Any]:
    dashboard = {
        "Zone1": zone1_data,
        "Zone2": zone2_data,
        "Relay": relay_state,
        "Common_Water_Level": common_water_level,
        "Timestamp": datetime.now().strftime("%H:%M:%S"),
        "status": status,
    }
    write_state_files(dashboard, status=status)
    return dashboard


def update_offline_state() -> None:
    global system_online
    if system_online:
        system_online = False
    write_state_files(build_zero_dashboard(), status="offline")


def process_sensor_payload(payload: SensorPayload) -> Dict[str, Any]:
    global latest_zone_data, last_common_water_level, latest_relay_state, prev_decision1, prev_decision2, first_cycle, system_online

    device_key = payload.device.lower().strip()
    if device_key not in {"zone1", "zone2"}:
        raise HTTPException(status_code=400, detail="Unsupported device")

    zone_name = "Zone1" if device_key == "zone1" else "Zone2"
    device_last_seen[device_key] = time.time()
    system_online = True

    zone_data = {
        "Zone": zone_name,
        "Temperature": safe_float(payload.temperature, 0.0),
        "Humidity": safe_float(payload.humidity, 0.0),
        "Soil_Moisture": safe_float(payload.soil, 0.0),
        "Air": safe_int(payload.air, 0),
        "Water_Level": 0.0,
    }

    raw_water = payload.water_level if payload.water_level is not None else payload.water
    if payload.water_percent is not None:
        raw_water = payload.water_percent

    if raw_water is not None:
        last_common_water_level = normalize_water_level(raw_water, last_common_water_level)

    zone_data["Water_Level"] = last_common_water_level
    latest_zone_data[zone_name] = zone_data

    zone1_data = latest_zone_data.get("Zone1", {
        "Zone": "Zone1",
        "Temperature": 0.0,
        "Humidity": 0.0,
        "Soil_Moisture": 0.0,
        "Air": 0,
        "Water_Level": last_common_water_level,
    })
    zone2_data = latest_zone_data.get("Zone2", {
        "Zone": "Zone2",
        "Temperature": 0.0,
        "Humidity": 0.0,
        "Soil_Moisture": 0.0,
        "Air": 0,
        "Water_Level": last_common_water_level,
    })

    zone1_data["Water_Level"] = last_common_water_level
    zone2_data["Water_Level"] = last_common_water_level

    selected_crops = load_selected_crops()
    if first_cycle:
        decision1 = {"pump": 0, "fan": 0, "uv": 0}
        decision2 = {"pump": 0, "fan": 0, "uv": 0}
        first_cycle = False
        print("[HTTP] First cycle – all relays held OFF (safe state).")
    else:
        decision1 = controller.decide_for_zone(zone1_data, selected_crops.get("Zone1", "Tomato"))
        decision2 = controller.decide_for_zone(zone2_data, selected_crops.get("Zone2", "Tomato"))

        for zone_label, curr, prev in [("Zone1", decision1, prev_decision1), ("Zone2", decision2, prev_decision2)]:
            for actuator in ["pump", "fan", "uv"]:
                cur_state = curr.get(actuator, 0)
                prev_state = prev.get(actuator, 0)
                if cur_state != prev_state:
                    action_str = "ON" if cur_state else "OFF"
                    reason = f"AI decision changed {actuator.upper()} to {action_str} based on crop requirements"
                    sensor_vals = zone1_data if zone_label == "Zone1" else zone2_data
                    insert_automation_event(
                        zone=zone_label,
                        actuator=actuator.capitalize(),
                        action=action_str,
                        reason=reason,
                        sensor_values={
                            "temperature": sensor_vals.get("Temperature"),
                            "humidity": sensor_vals.get("Humidity"),
                            "soil": sensor_vals.get("Soil_Moisture"),
                            "air": sensor_vals.get("Air"),
                        },
                        crop=selected_crops.get(zone_label, "Unknown"),
                    )

        prev_decision1 = decision1.copy()
        prev_decision2 = decision2.copy()

    latest_relay_state = {
        "Zone1Pump": int(decision1.get("pump", 0)),
        "Zone1Fan": int(decision1.get("fan", 0)),
        "Zone1UV": int(decision1.get("uv", 0)),
        "Zone2Pump": int(decision2.get("pump", 0)),
        "Zone2Fan": int(decision2.get("fan", 0)),
        "Zone2UV": int(decision2.get("uv", 0)),
    }

    dashboard = publish_dashboard_payload(zone1_data, zone2_data, latest_relay_state, last_common_water_level, status="online")
    check_and_fire_notifications(dashboard, selected_crops)
    insert_telemetry_snapshot(dashboard, selected_crops)
    return {
        "status": "ok",
        "device": zone_name,
        "relay_states": latest_relay_state,
        "common_water_level": last_common_water_level,
        "timestamp": dashboard.get("Timestamp"),
    }


@app.post("/api/esp32/zone1")
def receive_zone1(payload: SensorPayload) -> Dict[str, Any]:
    return process_sensor_payload(payload)


@app.post("/api/esp32/zone2")
def receive_zone2(payload: SensorPayload) -> Dict[str, Any]:
    return process_sensor_payload(payload)


@app.post("/api/esp32/relay/telemetry")
def receive_relay_telemetry(payload: RelayTelemetryPayload) -> Dict[str, Any]:
    global last_common_water_level, system_online
    device_last_seen["relay"] = time.time()
    system_online = True

    raw_water = payload.water_level if payload.water_level is not None else payload.water
    if payload.water_percent is not None:
        raw_water = payload.water_percent

    if raw_water is not None:
        last_common_water_level = normalize_water_level(raw_water, last_common_water_level)

    for zone_data in latest_zone_data.values():
        zone_data["Water_Level"] = last_common_water_level

    return {
        "status": "ok",
        "common_water_level": last_common_water_level,
        "raw_adc": payload.raw_adc,
    }


@app.get("/api/esp32/relay/commands")
def relay_commands() -> Dict[str, Any]:
    return {
        "status": "ok",
        "relay_states": latest_relay_state,
        "common_water_level": last_common_water_level,
        "timestamp": datetime.now().strftime("%H:%M:%S"),
    }


def monitor_connection_health() -> None:
    global system_online
    while True:
        now = time.time()

        # Only consider devices that have EVER sent data (last_seen > 0).
        # A device that never reported must NOT count as stale.
        active = {dev: ts for dev, ts in device_last_seen.items() if ts > 0}

        if active:
            # System is ONLINE if at least ONE device sent data recently.
            any_fresh = any((now - ts) <= DATA_TIMEOUT_SECONDS for ts in active.values())
            if any_fresh:
                if not system_online:
                    system_online = True
                    print("[MONITOR] ESP32 reconnected – system ONLINE")
            else:
                # ALL previously-seen devices are now stale → go OFFLINE
                if system_online:
                    update_offline_state()
                    print("[MONITOR] All ESP32s timed out – system OFFLINE")
        # If no device has ever reported, remain offline (initial startup state)

        time.sleep(2.0)


def main() -> None:
    threading.Thread(target=monitor_connection_health, daemon=True).start()
    print("\n[AgriVision AI] HTTP backend started. ESP32s should POST to /api/esp32/zone1 and /api/esp32/zone2")
    uvicorn.run(app, host="0.0.0.0", port=8002, log_level="warning")


if __name__ == "__main__":
    main()
