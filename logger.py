import serial
import csv
import os
import threading
from datetime import datetime

# ==========================
# SETTINGS
# ==========================

PORT_ZONE1 = os.getenv("ZONE1_PORT", "COM6")      # Change if needed
PORT_ZONE2 = os.getenv("ZONE2_PORT", "COM7")      # Change if needed
PORT_RELAY = os.getenv("RELAY_PORT", "COM11")     # Relay/water-level ESP32

BAUD = 115200

filename = "dataset/AgriVision_training.csv"

os.makedirs("dataset", exist_ok=True)

# Shared water level updated by the relay thread
common_water_level = 0.0
water_lock = threading.Lock()

# ==========================
# CREATE CSV
# ==========================

# Schema matches dataset/AgriVision_training.csv used by train_multi_output.py
HEADER = [
    "timeStamp",
    "Zone",
    "Temperature",
    "Humidity",
    "Light",
    "Soil_Moisture",
    "Water_Level",
    "Air",
    "Pump",
    "Fan",
    "Light_Output"
]

if not os.path.exists(filename):
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(HEADER)

lock = threading.Lock()

# ==========================
# RELAY / WATER LEVEL THREAD
# ==========================

def collect_water_level(port):
    """Continuously read the common water tank percentage from the relay ESP32."""
    global common_water_level
    try:
        ser = serial.Serial(port, BAUD, timeout=1)
        print(f"Relay/Water Connected ({port})")
        while True:
            line = ser.readline().decode("utf-8", errors="ignore").strip()
            if not line:
                continue
            # Accept "WATER,<percent>" or "STATUS,...,<percent>"
            parts = [p.strip() for p in line.split(",")]
            try:
                if parts[0].lower() == "water" and len(parts) >= 2:
                    level = float(parts[1])
                elif parts[0].lower() == "status" and len(parts) >= 8:
                    level = float(parts[-1])
                else:
                    continue
                if 0 <= level <= 100:
                    with water_lock:
                        common_water_level = level
            except ValueError:
                continue
    except Exception as e:
        print(f"Relay/Water Error: {e}")

# ==========================
# DATA COLLECTION
# ==========================

def collect_data(port, zone_name):

    try:

        ser = serial.Serial(port, BAUD, timeout=1)

        print(f"{zone_name} Connected ({port})")

        while True:

            line = ser.readline().decode("utf-8", errors="ignore").strip()

            if line == "":
                continue

            values = line.split(",")

            # Ignore boot/debug messages; expect 5 fields:
            # Zone,Temperature,Humidity,Soil_Moisture,Air
            if len(values) != 5:
                continue

            try:

                zone = values[0]
                temperature = float(values[1])
                humidity = float(values[2])
                soil = float(values[3])
                air = int(values[4])

                with water_lock:
                    water = common_water_level

                # ==========================
                # TEMPORARY LABELS
                # ==========================

                pump = 1 if soil < 35 else 0
                fan = 1 if temperature > 32 else 0
                # UV/light output scheduled by system time (12 AM-6 AM off)
                hour = datetime.now().hour
                light_output = 1 if 6 <= hour <= 23 else 0
                # Light sensor placeholder (0-100); logged for schema compatibility
                light = 0.0

                row = [
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    zone,
                    temperature,
                    humidity,
                    light,
                    soil,
                    water,
                    air,
                    pump,
                    fan,
                    light_output
                ]

                with lock:

                    with open(filename, "a", newline="") as f:

                        writer = csv.writer(f)
                        writer.writerow(row)

                        f.flush()
                        os.fsync(f.fileno())

                print(row)

            except Exception as e:
                print("Data Error:", e)

    except Exception as e:
        print(f"{zone_name} Error:", e)


# ==========================
# START THREADS
# ==========================

threading.Thread(
    target=collect_water_level,
    args=(PORT_RELAY,),
    daemon=True
).start()

threading.Thread(
    target=collect_data,
    args=(PORT_ZONE1, "Zone1"),
    daemon=True
).start()

threading.Thread(
    target=collect_data,
    args=(PORT_ZONE2, "Zone2"),
    daemon=True
).start()

print("\nCollecting AgriVision Dataset...\n")

# ==========================
# KEEP PROGRAM RUNNING
# ==========================

try:
    import time

    while True:
        time.sleep(1)

except KeyboardInterrupt:
    print("\nDataset collection stopped.")