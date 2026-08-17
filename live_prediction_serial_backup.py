import os
import serial
import json
import re
import time
from datetime import datetime
from typing import Optional, Dict, Tuple, List, Any

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from ai_control import CropAutomationController, load_selected_crops
from mongo_logger import insert_telemetry_snapshot, insert_automation_event, check_and_fire_notifications


class RelayPacketResult(tuple):
    """Tuple-like relay parse result that remains backward-compatible with legacy numeric checks."""

    def __new__(cls, level, raw_adc="N/A"):
        return super().__new__(cls, (float(level), str(raw_adc)))

    def __float__(self):
        return float(self[0])

    def __eq__(self, other):
        if isinstance(other, (int, float)):
            return float(self[0]) == float(other)
        return super().__eq__(other)


# ==========================
# SETTINGS
# ==========================
BAUD = 115200


def get_available_system_ports() -> List[str]:
    """Get list of active physical/hardware serial ports present on the system."""
    try:
        from serial.tools import list_ports
        detected = []
        for p in list_ports.comports():
            dev = getattr(p, "device", None)
            if dev:
                desc = getattr(p, "description", "").lower()
                # Skip standard bluetooth serial links unless explicitly requested
                if "bluetooth" in desc:
                    continue
                detected.append(dev)
        return detected
    except Exception:
        return []


def safe_open_port(port_name: str, baud: int = BAUD):
    """
    Safely attempt to open a single serial port with clear error classification.
    Returns (serial_instance, status_or_error_string).
    """
    try:
        device = serial.Serial(port_name, baud, timeout=0.15)
        return device, "OPENED"
    except PermissionError:
        return None, f"BUSY: Port {port_name} is in use by another application (e.g. Arduino IDE or Serial Monitor)."
    except FileNotFoundError:
        return None, f"NOT FOUND: Port {port_name} is not connected to the system."
    except serial.SerialException as exc:
        err_str = str(exc)
        if "Access is denied" in err_str or "PermissionError" in err_str:
            return None, f"BUSY: Port {port_name} is in use by another application (e.g. Arduino IDE or Serial Monitor)."
        if "Semaphore" in err_str or "timeout" in err_str.lower():
            return None, f"TIMEOUT: Port {port_name} hardware response timeout."
        return None, f"FAILED: Port {port_name} serial error ({err_str})."
    except Exception as exc:
        return None, f"ERROR: Port {port_name} ({exc})."


def resolve_port_candidates(port_env_name: str, defaults: Optional[List[str]] = None) -> List[str]:
    """Build a deterministic port candidate list using env overrides first."""
    env_port = os.getenv(port_env_name, "").strip()
    candidates: List[str] = []
    if env_port:
        candidates.append(env_port)

    fallback_ports = list(defaults or [])
    active_ports = get_available_system_ports()
    for port in fallback_ports + active_ports + ["COM6", "COM7", "COM11", "COM4", "COM5"]:
        if port and port not in candidates:
            candidates.append(port)
    return candidates


def discover_and_connect_esp32s():
    """
    Scans present system COM ports, auto-identifies Zone1, Zone2, and Relay ESP32s,
    and returns (zone1_dev, zone2_dev, relay_dev).
    Respects .env overrides ZONE1_PORT, ZONE2_PORT, RELAY_PORT if specified.
    Handles PermissionError, FileNotFoundError, and timeouts gracefully.
    """
    env_z1 = os.getenv("ZONE1_PORT", "").strip()
    env_z2 = os.getenv("ZONE2_PORT", "").strip()
    env_relay = os.getenv("RELAY_PORT", "").strip()

    candidates: List[str] = []
    for port_name in ["ZONE1_PORT", "ZONE2_PORT", "RELAY_PORT"]:
        candidates.extend(resolve_port_candidates(port_name, []))

    if env_z1:
        candidates.insert(0, env_z1)
    if env_z2 and env_z2 not in candidates:
        candidates.insert(0, env_z2)
    if env_relay and env_relay not in candidates:
        candidates.insert(0, env_relay)

    port_candidates: List[str] = []
    seen = set()
    for p in candidates:
        if p and p not in seen:
            port_candidates.append(p)
            seen.add(p)

    for role, env_value in [("Zone1", env_z1), ("Zone2", env_z2), ("Relay", env_relay)]:
        if env_value and env_value not in port_candidates:
            port_candidates.insert(0, env_value)

    devices: Dict[str, serial.Serial] = {}
    port_status: Dict[str, str] = {}
    identified: Dict[str, Optional[Tuple[str, serial.Serial]]] = {
        "Zone1": None,
        "Zone2": None,
        "Relay": None,
    }

    print("\n" + "=" * 70)
    print("[SERIAL DISCOVERY] Scanning COM ports for AgriVision ESP32s...")

    for p in port_candidates:
        dev, msg = safe_open_port(p)
        if dev is not None:
            devices[p] = dev
            port_status[p] = "OPENED"
        else:
            port_status[p] = msg

    # Print log status of checked ports
    for p in port_candidates:
        st = port_status.get(p, "UNKNOWN")
        if st == "OPENED":
            print(f"  [CHECK] {p}: Successfully Opened")
        elif st.startswith("NOT FOUND"):
            # Suppress noisy logs for non-existent ports
            pass
        else:
            print(f"  [CHECK] {p}: {st}")

    # 1. Match environment variable overrides if configured
    if env_z1 and env_z1 in devices:
        identified["Zone1"] = (env_z1, devices[env_z1])
    if env_z2 and env_z2 in devices:
        identified["Zone2"] = (env_z2, devices[env_z2])
    if env_relay and env_relay in devices:
        identified["Relay"] = (env_relay, devices[env_relay])

    # 2. Auto-identify unassigned open ports by listening to incoming packet header
    unassigned = [p for p in devices if p not in [val[0] for val in identified.values() if val]]

    for p in unassigned:
        dev = devices[p]
        time.sleep(0.05)
        sample_line = ""
        try:
            deadline = time.time() + 0.3
            while time.time() < deadline:
                if dev.in_waiting > 0:
                    line = dev.readline().decode(errors="ignore").strip()
                    if line:
                        sample_line = line
                        break
                time.sleep(0.01)
        except Exception:
            pass

        line_lower = sample_line.lower()
        if "zone1" in line_lower or "zone 1" in line_lower:
            if not identified["Zone1"]:
                identified["Zone1"] = (p, dev)
        elif "zone2" in line_lower or "zone 2" in line_lower:
            if not identified["Zone2"]:
                identified["Zone2"] = (p, dev)
        elif "water" in line_lower or "status" in line_lower or "relay" in line_lower:
            if not identified["Relay"]:
                identified["Relay"] = (p, dev)

    # 3. Fallback position matching if packets didn't arrive during 0.3s window
    remaining = [p for p in devices if p not in [val[0] for val in identified.values() if val]]
    for role in ["Zone1", "Zone2", "Relay"]:
        if not identified[role] and remaining:
            p = remaining.pop(0)
            identified[role] = (p, devices[p])

    missing = [role for role in ["Zone1", "Zone2", "Relay"] if not identified[role]]

    if missing:
        # Close open devices so next scan cycle can try cleanly
        for p, dev in devices.items():
            try:
                dev.close()
            except Exception:
                pass
        print(f"[SERIAL DISCOVERY WARNING] Missing devices: {', '.join(missing)}.")
        print("=" * 70 + "\n")
        return None, None, None

    z1_port, z1_dev = identified["Zone1"]  # type: ignore
    z2_port, z2_dev = identified["Zone2"]  # type: ignore
    relay_port, relay_dev = identified["Relay"]  # type: ignore

    # Close any extra unused open ports
    for p, dev in devices.items():
        if p not in (z1_port, z2_port, relay_port):
            try:
                dev.close()
            except Exception:
                pass

    print(f"  [CONNECTED] Zone1 ESP32  -> Port {z1_port}")
    print(f"  [CONNECTED] Zone2 ESP32  -> Port {z2_port}")
    print(f"  [CONNECTED] Relay ESP32  -> Port {relay_port}")
    print("=" * 70 + "\n")

    # Immediate fail-safe: Send 0,0,0,0,0,0 to ensure ALL relays remain strictly OFF
    try:
        relay_dev.write(b"0,0,0,0,0,0\n")
        relay_dev.flush()
        print("[RELAY HARDWARE INITIALIZATION] Safe state command (0,0,0,0,0,0) sent to Relay ESP32.")
    except Exception as exc:
        print(f"[RELAY HARDWARE INITIALIZATION WARNING] Failed to send safe state command: {exc}")

    return z1_dev, z2_dev, relay_dev


# ==========================
# CROP-AWARE AI CONTROL
# ==========================
controller = CropAutomationController()
print("Crop-aware rule-based AI controller loaded.")

last_common_water_level = 0.0
first_cycle = True
last_zone1_data = None
last_zone2_data = None


# ==========================
# READ SENSOR PACKET (5 fields)
# ==========================
def _number(value):
    """Extract a numeric field, including labelled values such as Soil:62%."""
    match = re.search(r"[-+]?\d*\.?\d+", str(value))
    if not match:
        raise ValueError(f"No numeric value in {value!r}")
    return float(match.group())


def _parse_sensor_packet(line, expected_zone):
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

    soil_raw = "N/A"
    if len(parts) == 5:
        soil_value, air_value = parts[3], parts[4]
    elif len(parts) == 6:
        soil_value, air_value = parts[3], parts[4]
        soil_raw = parts[5]
    else:
        raise ValueError(f"unexpected field count: {len(parts)}")

    return {
        "Zone": expected_zone,
        "Temperature": _number(parts[1]),
        "Humidity": _number(parts[2]),
        "Soil_Moisture": _number(soil_value),
        "Air": int(_number(air_value)),
        "Soil_Raw": soil_raw
    }


def _drain_and_read_latest(port, timeout_seconds=0.05, expected_zone=None):
    """Drain stale input buffer and return the newest valid sensor packet for instant real-time updates."""
    buffered_lines = []
    try:
        while port.in_waiting > 0:
            line = port.readline().decode(errors="ignore").strip()
            if line:
                buffered_lines.append(line)
    except Exception:
        pass

    if buffered_lines:
        if expected_zone is not None:
            for line in reversed(buffered_lines):
                try:
                    _parse_sensor_packet(line, expected_zone)
                    return line
                except ValueError:
                    continue
        return buffered_lines[-1]

    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            line = port.readline().decode(errors="ignore").strip()
            if line:
                if expected_zone is not None:
                    try:
                        _parse_sensor_packet(line, expected_zone)
                        return line
                    except ValueError:
                        continue
                return line
        except Exception:
            pass
        time.sleep(0.005)
    return None


def read_sensor_data(port, expected_zone, fallback=None):
    deadline = time.time() + 0.15
    while time.time() < deadline:
        line = _drain_and_read_latest(port, 0.05, expected_zone=expected_zone)
        if line is None:
            if fallback is not None:
                return fallback
            continue
        try:
            sensor_data = _parse_sensor_packet(line, expected_zone)
            return sensor_data
        except ValueError:
            continue

    if fallback is not None:
        return fallback
    raise Exception(f"Sensor {expected_zone} Disconnected")


# ==========================
# READ RELAY WATER LEVEL (percentage)
# ==========================
def _parse_relay_packet(line):
    line = line.strip()
    if not line:
        raise ValueError("empty relay packet")

    raw_adc = "N/A"
    level = None

    if line.lower().startswith("water,"):
        parts = [value.strip() for value in line.split(",")]
        if len(parts) >= 2:
            level = float(parts[1])
            if len(parts) >= 3:
                raw_adc = parts[2]
            if not 0 <= level <= 100:
                raise ValueError(f"relay level out of range: {level}")
            return RelayPacketResult(level, raw_adc)

    if line.lower().startswith("status,"):
        parts = [value.strip() for value in line.split(",")]
        if len(parts) >= 8:
            level = float(parts[7])
            if len(parts) >= 9:
                raw_adc = parts[8]
            if not 0 <= level <= 100:
                raise ValueError(f"relay level out of range: {level}")
            return RelayPacketResult(level, raw_adc)

    labelled_value = re.search(
        r"(?:water(?:\s*(?:level|tank))?|tank)\s*[:,=]\s*(\d{1,3}(?:\.\d+)?)\s*%?",
        line,
        re.IGNORECASE,
    )
    if labelled_value:
        level = float(labelled_value.group(1))
    else:
        bare_value = re.fullmatch(r"\s*(\d{1,3}(?:\.\d+)?)\s*%?\s*", line)
        if not bare_value:
            raise ValueError(f"unrecognized relay packet: {line!r}")
        if line.strip() == "0":
            raise ValueError("ignored zero relay echo")
        level = float(bare_value.group(1))

    if not 0 <= level <= 100:
        raise ValueError(f"relay level out of range: {level}")
    return RelayPacketResult(level, raw_adc)


def read_relay_data(port, fallback=None):
    """Read tank percentage and raw ADC from relay ESP32."""
    deadline = time.time() + 0.15
    last_raw = "N/A"
    latest_level = None

    while time.time() < deadline:
        if port.in_waiting == 0:
            time.sleep(0.01)
            continue

        while port.in_waiting > 0:
            line = port.readline().decode(errors="ignore").strip()
            if not line:
                continue

            print(f"[RELAY ESP32 SERIAL] {line}")

            try:
                level, raw_adc = _parse_relay_packet(line)
                latest_level = level
                last_raw = raw_adc
            except ValueError:
                pass

        if latest_level is not None:
            return latest_level, last_raw

    if fallback is not None:
        return fallback, last_raw
    return None, "N/A"


# ==========================
# MAIN EXECUTION LOOP
# ==========================
def main():
    global first_cycle, last_zone1_data, last_zone2_data, last_common_water_level

    # 1. Connect to ESP32 devices
    while True:
        zone1, zone2, relay = discover_and_connect_esp32s()
        if zone1 is not None and zone2 is not None and relay is not None:
            status = {"status": "online"}
            with open("system_status.json", "w", encoding="utf-8") as f:
                json.dump(status, f, indent=4)
            break
        else:
            status = {"status": "offline", "message": "Waiting for ESP32 serial connections"}
            with open("system_status.json", "w", encoding="utf-8") as f:
                json.dump(status, f, indent=4)
            time.sleep(2.0)

    try:
        zone1.reset_input_buffer()
        zone2.reset_input_buffer()
        relay.reset_input_buffer()
    except Exception:
        pass

    # Ensure initial fail-safe OFF command is sent to relay ESP32
    try:
        relay.write(b"0,0,0,0,0,0\n")
        relay.flush()
    except Exception:
        pass

    first_cycle = True
    prev_decision1 = {"pump": 0, "fan": 0, "uv": 0}
    prev_decision2 = {"pump": 0, "fan": 0, "uv": 0}

    print("\n[AgriVision AI] Live prediction loop started.")

    # 2. Main sensor read and AI decision loop
    while True:
        try:
            zone1_data = read_sensor_data(zone1, "Zone1")
            zone2_data = read_sensor_data(zone2, "Zone2")
            last_zone1_data = zone1_data
            last_zone2_data = zone2_data

            received_water_level, tank_raw = read_relay_data(relay)
            if received_water_level is None:
                raise RuntimeError("Relay/Water level data unavailable")
            last_common_water_level = received_water_level
            common_water_level = last_common_water_level

            zone1_data["Water_Level"] = common_water_level
            zone2_data["Water_Level"] = common_water_level

            selected_crops = load_selected_crops()

            if first_cycle:
                decision1 = {"pump": 0, "fan": 0, "uv": 0}
                decision2 = {"pump": 0, "fan": 0, "uv": 0}
                first_cycle = False
                print("[STARTUP] First cycle – all relays held OFF (safe state).")
            else:
                decision1 = controller.decide_for_zone(zone1_data, selected_crops["Zone1"])
                decision2 = controller.decide_for_zone(zone2_data, selected_crops["Zone2"])

                # Automation Event Detection
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
                                    "air": sensor_vals.get("Air")
                                },
                                crop=selected_crops.get(zone_label, "Unknown")
                            )

                prev_decision1 = decision1.copy()
                prev_decision2 = decision2.copy()

            # Build dashboard JSON payload
            dashboard = {
                "Zone1": zone1_data,
                "Zone2": zone2_data,
                "Relay": {
                    "Zone1Pump": decision1["pump"],
                    "Zone1Fan": decision1["fan"],
                    "Zone1UV": decision1["uv"],
                    "Zone2Pump": decision2["pump"],
                    "Zone2Fan": decision2["fan"],
                    "Zone2UV": decision2["uv"]
                },
                "Common_Water_Level": common_water_level,
                "Timestamp": datetime.now().strftime("%H:%M:%S")
            }

            # Send commands to Relay ESP32 (Pump, Fan, UV for Zone1 & Zone2)
            relay_msg = (
                f"{decision1['pump']},{decision1['fan']},{decision1['uv']},"
                f"{decision2['pump']},{decision2['fan']},{decision2['uv']}\n"
            )
            relay.write(relay_msg.encode())
            relay.flush()

            # Console Debug Output
            print("\n---------------- DEBUG METRICS ----------------")
            print(f"Zone1 Soil Raw:      {zone1_data.get('Soil_Raw', 'N/A')}")
            print(f"Zone1 Soil Parsed:   {zone1_data['Soil_Moisture']:.1f}%")
            print(f"Zone2 Soil Raw:      {zone2_data.get('Soil_Raw', 'N/A')}")
            print(f"Zone2 Soil Parsed:   {zone2_data['Soil_Moisture']:.1f}%")
            print(f"Tank Raw:            {tank_raw}")
            print(f"Tank Parsed:         {common_water_level:.1f}%")
            print("AI Decision:")
            print(f"  Zone1 ({selected_crops['Zone1']}): Pump={decision1['pump']} Fan={decision1['fan']} UV={decision1['uv']}")
            print(f"  Zone2 ({selected_crops['Zone2']}): Pump={decision2['pump']} Fan={decision2['fan']} UV={decision2['uv']}")
            print(f"Relay Command Sent:  {relay_msg.strip()}")
            print("-----------------------------------------------\n")

            # Fire threshold notifications if sensors exceed limits
            check_and_fire_notifications(dashboard, selected_crops)

            # Persist latest_data.json
            with open("system_status.json", "w", encoding="utf-8") as f:
                json.dump({"status": "online"}, f, indent=4)

            tmp_path = "latest_data.tmp"
            target_path = "latest_data.json"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(dashboard, f, indent=4)

            for attempt in range(5):
                try:
                    os.replace(tmp_path, target_path)
                    break
                except PermissionError:
                    time.sleep(0.02)
            else:
                try:
                    with open(target_path, "w", encoding="utf-8") as f:
                        json.dump(dashboard, f, indent=4)
                except Exception:
                    pass

            print("JSON Updated")

            # Store telemetry snapshot to MongoDB Atlas
            try:
                insert_telemetry_snapshot(dashboard, selected_crops)
            except Exception as mongo_err:
                print(f"[MongoDB Insert Exception] {mongo_err}")

        except Exception as e:
            print("ERROR:", e)
            with open("system_status.json", "w", encoding="utf-8") as f:
                json.dump({"status": "offline", "message": str(e)}, f, indent=4)

        time.sleep(0.05)


if __name__ == "__main__":
    main()
