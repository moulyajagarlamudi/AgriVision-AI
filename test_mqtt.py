"""
Quick MQTT test script - simulates Zone1 and Zone2 ESP32 sending data.
Run this WHILE main.py is running to see the dashboard go Online.

Usage:
    python test_mqtt.py
"""
import json
import time
import paho.mqtt.client as mqtt

BROKER = "localhost"
PORT   = 1883

client = mqtt.Client()
client.connect(BROKER, PORT)
client.loop_start()

zone1 = {
    "device": "zone1",
    "temperature": 26.5,
    "humidity": 60.0,
    "soil": 72.0,
    "air": 420
}

zone2 = {
    "device": "zone2",
    "temperature": 25.0,
    "humidity": 65.0,
    "soil": 68.0,
    "air": 380
}

print("Sending MQTT messages... open http://localhost:8000 to see the dashboard go Online.")
print("Press Ctrl+C to stop.\n")

try:
    while True:
        client.publish("agrivision/zone1/sensors", json.dumps(zone1))
        client.publish("agrivision/zone2/sensors", json.dumps(zone2))
        print(f"[TEST] Published Zone1 + Zone2 data")
        time.sleep(2)
except KeyboardInterrupt:
    print("\nStopped.")
    client.loop_stop()
    client.disconnect()
