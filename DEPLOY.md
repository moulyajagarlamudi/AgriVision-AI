# AgriVision AI — Final System Deployment Guide (10 Steps)

This guide walks through configuring and running the **AgriVision AI** system as a **100% standalone, autonomous deployment** where the hardware operates automatically without requiring any PC or local terminal command running.

---

## Architecture Overview

```
 ┌──────────────────────┐         ┌──────────────────────┐
 │    Zone 1 ESP32      │         │    Zone 2 ESP32      │
 │ (DHT22, Soil, MQ135) │         │ (DHT22, Soil, MQ135) │
 └──────────┬───────────┘         └──────────┬───────────┘
            │                                │
            │ agrivision/zone1/sensors       │ agrivision/zone2/sensors
            ▼                                ▼
 ┌────────────────────────────────────────────────────────┐
 │               HiveMQ Cloud (MQTT Broker)               │
 └──────────────┬─────────────────────────┬───────────────┘
                │                         ▲
                │ (Sensor Streams)        │ agrivision/config/crops (retained)
                ▼                         │
 ┌─────────────────────────────┐  ┌───────┴────────────────────┐
 │     Relay ESP32 (Node)      │  │     Cloud Backend / UI     │
 │  • Stage-Aware AI Logic     │  │  • Render: FastAPI Backend │
 │  • INPUT_PULLUP Active-LOW  │  │  • Vercel: Dashboard UI    │
 │  • NVS Flash Persistence    │  │  • MongoDB Atlas: Logs     │
 └──────────────┬──────────────┘  └────────────────────────────┘
                │
                ▼
 ┌────────────────────────────────────────────────────────┐
 │ 16-Channel Relay Board & Physical Actuators            │
 │ • Ch 1: Water Pump     • Ch 4: Zone 1 UV / Light       │
 │ • Ch 2: Sprinkler      • Ch 5: Zone 2 Fan              │
 │ • Ch 3: Zone 1 Fan     • Ch 6: Zone 2 UV / Light       │
 └────────────────────────────────────────────────────────┘
```

---

## 10-Step Deployment Roadmap

### STEP 1: Flash Relay ESP32 Firmware
1. Open Arduino IDE.
2. Select **ESP32 Dev Module** and the correct COM Port.
3. Open [`esp32/relay_controller.ino`](file:///C:/Users/acer/Downloads/AgriVision_AI/esp32/relay_controller.ino).
4. Verify the WiFi credentials in the sketch:
   - `WIFI_SSID = "Moulya"`
   - `WIFI_PASSWORD = "mouj1234"`
5. Click **Upload**.
6. When uploaded, open **Serial Monitor** at `115200 baud`.
7. You should see:
   ```text
   [NVS] Loaded → Z1:Paddy/Vegetative  Z2:Tomato/Vegetative
   [WiFi] Connected → 192.168.x.x
   [MQTT] Connected
   [SYSTEM] Ready. Autonomous control active.
   ```

---

### STEP 2: Flash Zone 1 and Zone 2 Sensor Nodes
1. Open [`esp32/zone1.ino`](file:///C:/Users/acer/Downloads/AgriVision_AI/esp32/zone1.ino) and upload to your Zone 1 ESP32.
2. Open [`esp32/zone2.ino`](file:///C:/Users/acer/Downloads/AgriVision_AI/esp32/zone2.ino) and upload to your Zone 2 ESP32.
3. In Serial Monitor for each node, verify sensor values are read and transmitted:
   ```text
   [MQTT] Zone 1 TX: {"device":"zone1","temperature":28.4,"humidity":65.0,"soil":45.2,"air":120}
   ```

---

### STEP 3: Verify Autonomous Control with PC OFF
1. Power all 3 ESP32 boards using USB wall adapters (or a 5V power supply).
2. Ensure no Python scripts (`main.py`) are running on your PC.
3. Observe the Relay LEDs:
   - **Zone 1 Fan (Ch 3)** turns **ON** if Zone 1 temperature exceeds the stage target (e.g. > 28°C for Paddy Vegetative).
   - **Sprinkler (Ch 2)** turns **ON** when soil moisture is below the stage target (e.g. < 90% for Paddy Vegetative) and turns **OFF** immediately when soil moisture reaches target or both zones are satisfied.
   - **UV Lights (Ch 4 & Ch 6)** stay **ON** between 06:00 and 23:00 for crops requiring medium/high light.
   - **Water Pump (Ch 1)** runs only if the tank is between 1% and 29% capacity (never runs dry).

---

### STEP 4: (Cloud Deployment) Push Repository to GitHub
1. Initialize git in your project folder (if not already done):
   ```bash
   git init
   git add .
   git commit -m "AgriVision AI production deployment"
   ```
2. Push to your GitHub account repository (public or private).

---

### STEP 5: Deploy Backend to Render (Free Tier)
1. Go to [https://render.com](https://render.com) and create a free account.
2. Click **New +** → **Web Service**.
3. Connect your GitHub repository.
4. Set the following settings:
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. In **Environment Variables**, add:
   - `MONGODB_URI`: `mongodb+srv://moulyajagarlamudi93_db_user:mouls1234@cluster0.pvodhao.mongodb.net/?appName=Cluster0`
   - `MQTT_BROKER_HOST`: `67000403e5584b348d982f289c69b053.s1.eu.hivemq.cloud`
   - `MQTT_BROKER_PORT`: `8883`
   - `MQTT_BROKER_USERNAME`: `Agrivision`
   - `MQTT_BROKER_PASSWORD`: `mouls1234`
6. Click **Deploy Web Service**.
7. Copy your assigned Render URL (e.g., `https://agrivision-ai.onrender.com`).

---

### STEP 6: Point Frontend to Render Backend
1. Open [`static/js/config.js`](file:///C:/Users/acer/Downloads/AgriVision_AI/static/js/config.js).
2. Set your Render URL:
   ```javascript
   window.API_BASE_URL = "https://agrivision-ai.onrender.com";
   ```
3. Commit and push this change to GitHub.

---

### STEP 7: Deploy Dashboard to Vercel
1. Go to [https://vercel.com](https://vercel.com) and log in.
2. Click **Add New...** → **Project**.
3. Import your GitHub repository.
4. Deploy the frontend.
5. Once deployed, open your Vercel URL in any browser on your phone, tablet, or PC.

---

### STEP 8: Test Crop & Stage Selection
1. Open the deployed dashboard.
2. Under **Zone 1 (Rack 1)**, change the crop to **Chilli** and stage to **Flowering**.
3. Under **Zone 2 (Rack 2)**, change the crop to **Tomato** and stage to **Fruiting**.
4. The dashboard makes a `PUT /api/crops/Zone1` and `PUT /api/crops/Zone2` call to Render.
5. Render immediately broadcasts a **retained MQTT message** on `agrivision/config/crops`.
6. The Relay ESP32 receives this update and saves it to **NVS Flash**.

---

### STEP 9: Power-Cycle the Relay ESP32 (Persistence Test)
1. Unplug the power cable from the Relay ESP32 for 10 seconds.
2. Plug it back in.
3. Observe that it boots up and immediately loads:
   - Zone 1: Chilli (Flowering)
   - Zone 2: Tomato (Fruiting)
   without needing any command or connection from your PC!

---

### STEP 10: Final Physical Farm Automation Verification
1. Verify physical behavior:
   - Place soil moisture probe in dry air → Sprinkler turns ON.
   - Place soil moisture probe in wet soil / water cup → Sprinkler turns OFF.
   - Blow hot air on DHT22 sensor → Fan turns ON.
2. Shut down your PC completely.
3. Check the dashboard on your phone — all telemetry, automated logs, and historical data continue streaming live 24/7!
