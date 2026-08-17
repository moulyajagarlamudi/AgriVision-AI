import urllib.request, json, time

payload = {'device': 'zone1', 'temperature': 25.5, 'humidity': 60.0, 'soil': 50.0, 'air': 400}
url = 'http://127.0.0.1:8001/api/esp32/zone1'

print("Mock ESP32 started. Sending POST to", url, "every 2 seconds...")
while True:
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={'Content-Type':'application/json'}, method='POST')
        resp = urllib.request.urlopen(req)
        print("Success! Dashboard should now say ONLINE.")
    except Exception as e:
        print("Failed to send POST:", e)
    time.sleep(2)
