/* ================================================================
   AgriVision AI - ESP32 Standalone Relay Controller
   ================================================================
   Autonomous operation – NO PC required.
   Internal Pull-Up Active-LOW Switching (Proven for 16-Ch Relay)
   Stage-Aware Crop Configuration with NVS Persistence
   ================================================================ */

#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <ArduinoOTA.h>
#include <Preferences.h>
#include <time.h>

/* ================================================================
   STRUCTURE DEFINITIONS (Must be at top for Arduino C++ compiler)
   ================================================================ */
struct CropConfig {
  float temperature;
  float humidity;
  float soil;
  const char* light;
};

struct ZoneData {
  float temperature = 0;
  float humidity    = 0;
  float soil        = 0;
  float air         = 0;
  unsigned long lastSeen = 0;
  bool received = false;
};

// Forward declarations
CropConfig getCropConfig(String crop, String stage);
void decideZone(ZoneData &zone, String crop, String stage, int &fan, int &uv);
void relayOFF(int pin);
void relayON(int pin);
void safeWrite(int pin, bool turnOn);
void allRelaysOff();
void applyRelays();

/* ================================================================
   RELAY PINS  (DO NOT CHANGE)
   ================================================================ */
#define WATER_SENSOR 34

const int RELAY_PINS[16] = {
  23, // Relay 1  - Central Water Pump
  5,  // Relay 2  - Shared Sprinkler
  19, // Relay 3  - Zone 1 Fan
  18, // Relay 4  - Zone 1 UV / Light
  17, // Relay 5  - Zone 2 Fan
  16, // Relay 6  - Zone 2 UV / Light
  4,  // Relay 7  - Unused
  13, // Relay 8  - Unused
  14, // Relay 9  - Unused
  27, // Relay 10 - Unused
  26, // Relay 11 - Unused
  25, // Relay 12 - Unused
  33, // Relay 13 - Unused
  32, // Relay 14 - Unused
  22, // Relay 15 - Unused
  21  // Relay 16 - Unused
};

/* ================================================================
   PROVEN INTERNAL PULL-UP ACTIVE-LOW RELAY SWITCHING
   relayOFF → INPUT_PULLUP   → Relay LED OFF (optocoupler released)
   relayON  → OUTPUT LOW     → Relay LED ON  (optocoupler triggered)
   ================================================================ */
void relayOFF(int pin) {
  pinMode(pin, INPUT_PULLUP);
}

void relayON(int pin) {
  pinMode(pin, OUTPUT);
  digitalWrite(pin, LOW);
}

void safeWrite(int pin, bool turnOn) {
  if (turnOn) relayON(pin);
  else        relayOFF(pin);
}

/* ================================================================
   WIFI / MQTT CREDENTIALS
   ================================================================ */
const char* WIFI_SSID     = "Moulya";
const char* WIFI_PASSWORD = "mouj1234";

#define MQTT_BROKER_HOST "67000403e5584b348d982f289c69b053.s1.eu.hivemq.cloud"
#define MQTT_BROKER_PORT 8883
#define MQTT_USERNAME    "Agrivision"
#define MQTT_PASSWORD    "mouls1234"
#define MQTT_CLIENT_ID   "AgriVision-Standalone-Relay"

/* ================================================================
   MQTT TOPICS  (DO NOT CHANGE — must match Python backend)
   ================================================================ */
#define TOPIC_ZONE1_SENSOR  "agrivision/zone1/sensors"
#define TOPIC_ZONE2_SENSOR  "agrivision/zone2/sensors"
#define TOPIC_RELAY_CMD     "agrivision/relay/commands"
#define TOPIC_RELAY_STATUS  "agrivision/relay/status"
#define TOPIC_CROP_CONFIG   "agrivision/config/crops"

/* ================================================================
   WATER SENSOR CALIBRATION
   ================================================================ */
const int WATER_EMPTY = 200;
const int WATER_FULL  = 4095;

/* ================================================================
   TIMING
   ================================================================ */
const unsigned long SENSOR_TIMEOUT_MS    = 45000; // 45s – prevents premature safety shutoff
const unsigned long WIFI_RETRY_INTERVAL  = 8000;
const unsigned long MQTT_RETRY_INTERVAL  = 4000;
const unsigned long DECISION_INTERVAL_MS = 2000;
const unsigned long TELEMETRY_INTERVAL_MS= 2000;

/* ================================================================
   GLOBAL OBJECTS
   ================================================================ */
WiFiClientSecure espClient;
PubSubClient     mqtt(espClient);
Preferences      prefs;

ZoneData zone1;
ZoneData zone2;

/* ================================================================
   CROP + STAGE SELECTION  (persisted in NVS flash)
   ================================================================ */
String zone1Crop  = "Paddy";
String zone1Stage = "Vegetative";
String zone2Crop  = "Tomato";
String zone2Stage = "Vegetative";

/* ================================================================
   RELAY STATES  (0 = OFF, 1 = ON)
   ================================================================ */
int water_pump = 0;
int sprinkler  = 0;
int zone1_fan  = 0;
int zone1_uv   = 0;
int zone2_fan  = 0;
int zone2_uv   = 0;

/* ================================================================
   WATER LEVEL
   ================================================================ */
int waterRaw     = 0;
int waterPercent = 0;

/* ================================================================
   TIMESTAMPS
   ================================================================ */
unsigned long lastDecisionTime  = 0;
unsigned long lastTelemetryTime = 0;
unsigned long lastWiFiRetry     = 0;
unsigned long lastMQTTRetry     = 0;

/* ================================================================
   STAGE-AWARE CROP CONFIGURATION TABLE
   Matches the aiCropDatabase in crop.js exactly.
   ================================================================ */
CropConfig getCropConfig(String crop, String stage) {

  // ---------- PADDY ----------
  if (crop == "Paddy") {
    if (stage == "Seedling")   return {26, 85, 75,  "Low"};
    if (stage == "Flowering")  return {29, 78, 92,  "High"};
    if (stage == "Fruiting")   return {28, 75, 90,  "High"};
    if (stage == "Harvest")    return {27, 65, 68,  "Medium"};
    /* Vegetative (default) */ return {28, 82, 90,  "High"};
  }

  // ---------- WHEAT ----------
  if (crop == "Wheat") {
    if (stage == "Seedling")   return {15, 70, 48,  "Low"};
    if (stage == "Flowering")  return {20, 55, 52,  "High"};
    if (stage == "Fruiting")   return {22, 50, 48,  "High"};
    if (stage == "Harvest")    return {20, 45, 35,  "Medium"};
    /* Vegetative (default) */ return {18, 60, 55,  "Medium"};
  }

  // ---------- TOMATO ----------
  if (crop == "Tomato") {
    if (stage == "Seedling")   return {22, 78, 55,  "Low"};
    if (stage == "Flowering")  return {23, 60, 62,  "High"};
    if (stage == "Fruiting")   return {26, 58, 72,  "High"};
    if (stage == "Harvest")    return {24, 52, 58,  "Medium"};
    /* Vegetative (default) */ return {24, 65, 65,  "High"};
  }

  // ---------- POTATO ----------
  if (crop == "Potato") {
    if (stage == "Seedling")   return {16, 80, 55,  "Low"};
    if (stage == "Flowering")  return {20, 68, 70,  "Medium"};
    if (stage == "Fruiting")   return {17, 65, 75,  "Medium"};
    if (stage == "Harvest")    return {15, 55, 45,  "Low"};
    /* Vegetative (default) */ return {18, 72, 65,  "Medium"};
  }

  // ---------- MAIZE ----------
  if (crop == "Maize") {
    if (stage == "Seedling")   return {24, 78, 62,  "Low"};
    if (stage == "Flowering")  return {29, 62, 75,  "High"};
    if (stage == "Fruiting")   return {28, 65, 78,  "High"};
    if (stage == "Harvest")    return {26, 55, 55,  "Medium"};
    /* Vegetative (default) */ return {27, 70, 72,  "High"};
  }

  // ---------- CHILLI ----------
  if (crop == "Chilli") {
    if (stage == "Seedling")   return {26, 80, 55,  "Low"};
    if (stage == "Flowering")  return {28, 65, 62,  "High"};
    if (stage == "Fruiting")   return {30, 60, 72,  "High"};
    if (stage == "Harvest")    return {27, 55, 58,  "Medium"};
    /* Vegetative (default) */ return {27, 72, 68,  "High"};
  }

  // ---------- ONION ----------
  if (crop == "Onion") {
    if (stage == "Seedling")   return {18, 72, 50,  "Low"};
    if (stage == "Flowering")  return {22, 60, 52,  "Medium"};
    if (stage == "Fruiting")   return {20, 55, 55,  "Medium"};
    if (stage == "Harvest")    return {18, 45, 40,  "Low"};
    /* Vegetative (default) */ return {20, 65, 58,  "Medium"};
  }

  // ---------- BRINJAL ----------
  if (crop == "Brinjal") {
    if (stage == "Seedling")   return {24, 80, 58,  "Low"};
    if (stage == "Flowering")  return {27, 65, 65,  "High"};
    if (stage == "Fruiting")   return {28, 62, 75,  "High"};
    if (stage == "Harvest")    return {26, 58, 62,  "Medium"};
    /* Vegetative (default) */ return {26, 70, 70,  "High"};
  }

  // ---------- CABBAGE ----------
  if (crop == "Cabbage") {
    if (stage == "Seedling")   return {15, 80, 58,  "Low"};
    if (stage == "Flowering")  return {18, 70, 65,  "Medium"};
    if (stage == "Fruiting")   return {16, 68, 72,  "Medium"};
    if (stage == "Harvest")    return {14, 60, 55,  "Low"};
    /* Vegetative (default) */ return {17, 75, 68,  "Medium"};
  }

  // ---------- SPINACH ----------
  if (crop == "Spinach") {
    if (stage == "Seedling")   return {13, 80, 62,  "Low"};
    if (stage == "Flowering")  return {18, 68, 65,  "Medium"};
    if (stage == "Fruiting")   return {16, 70, 65,  "Medium"};
    if (stage == "Harvest")    return {12, 65, 55,  "Low"};
    /* Vegetative (default) */ return {15, 75, 70,  "Medium"};
  }

  // ---------- CARROT ----------
  if (crop == "Carrot") {
    if (stage == "Seedling")   return {16, 75, 70,  "Low"};
    if (stage == "Flowering")  return {20, 62, 58,  "Medium"};
    if (stage == "Fruiting")   return {16, 65, 75,  "Medium"};
    if (stage == "Harvest")    return {14, 55, 45,  "Low"};
    /* Vegetative (default) */ return {18, 68, 65,  "Medium"};
  }

  // ---------- GROUNDNUT ----------
  if (crop == "Groundnut") {
    if (stage == "Seedling")   return {25, 72, 55,  "Low"};
    if (stage == "Flowering")  return {30, 62, 58,  "High"};
    if (stage == "Fruiting")   return {29, 60, 72,  "High"};
    if (stage == "Harvest")    return {27, 52, 48,  "Medium"};
    /* Vegetative (default) */ return {28, 65, 62,  "High"};
  }

  // ---------- FENUGREEK ----------
  if (crop == "Fenugreek") {
    if (stage == "Seedling")   return {20, 68, 48,  "Low"};
    if (stage == "Flowering")  return {24, 55, 48,  "Medium"};
    if (stage == "Fruiting")   return {24, 52, 58,  "Medium"};
    if (stage == "Harvest")    return {22, 45, 42,  "Low"};
    /* Vegetative (default) */ return {22, 60, 55,  "Medium"};
  }

  // ---------- FENNEL ----------
  if (crop == "Fennel") {
    if (stage == "Seedling")   return {17, 62, 45,  "Low"};
    if (stage == "Flowering")  return {21, 52, 45,  "Medium"};
    if (stage == "Fruiting")   return {20, 50, 55,  "Medium"};
    if (stage == "Harvest")    return {18, 45, 38,  "Low"};
    /* Vegetative (default) */ return {19, 55, 50,  "Medium"};
  }

  // ---------- CORIANDER ----------
  if (crop == "Coriander") {
    if (stage == "Seedling")   return {19, 72, 50,  "Low"};
    if (stage == "Flowering")  return {24, 58, 48,  "Medium"};
    if (stage == "Fruiting")   return {23, 52, 45,  "Medium"};
    if (stage == "Harvest")    return {21, 48, 40,  "Low"};
    /* Vegetative (default) */ return {21, 65, 55,  "Medium"};
  }

  // ---------- AMARANTHUS ----------
  if (crop == "Amaranthus") {
    if (stage == "Seedling")   return {22, 75, 65,  "Low"};
    if (stage == "Flowering")  return {27, 62, 68,  "High"};
    if (stage == "Fruiting")   return {28, 60, 75,  "High"};
    if (stage == "Harvest")    return {25, 55, 58,  "Medium"};
    /* Vegetative (default) */ return {25, 68, 72,  "High"};
  }

  // Fallback default
  return {24, 65, 60, "Medium"};
}

/* ================================================================
   ALL RELAYS OFF (safe state)
   ================================================================ */
void allRelaysOff() {
  water_pump = 0; sprinkler = 0;
  zone1_fan  = 0; zone1_uv  = 0;
  zone2_fan  = 0; zone2_uv  = 0;
  for (int i = 0; i < 16; i++) relayOFF(RELAY_PINS[i]);
}

/* ================================================================
   APPLY RELAY STATES → PHYSICAL PINS
   ================================================================ */
void applyRelays() {
  safeWrite(RELAY_PINS[0], water_pump == 1); // Relay 1 - Pump
  safeWrite(RELAY_PINS[1], sprinkler  == 1); // Relay 2 - Sprinkler
  safeWrite(RELAY_PINS[2], zone1_fan  == 1); // Relay 3 - Zone 1 Fan
  safeWrite(RELAY_PINS[3], zone1_uv   == 1); // Relay 4 - Zone 1 UV
  safeWrite(RELAY_PINS[4], zone2_fan  == 1); // Relay 5 - Zone 2 Fan
  safeWrite(RELAY_PINS[5], zone2_uv   == 1); // Relay 6 - Zone 2 UV
  for (int i = 6; i < 16; i++) relayOFF(RELAY_PINS[i]); // Unused OFF
}

/* ================================================================
   WATER LEVEL READ
   ================================================================ */
void readWaterLevel() {
  waterRaw     = analogRead(WATER_SENSOR);
  waterPercent = constrain(map(waterRaw, WATER_EMPTY, WATER_FULL, 0, 100), 0, 100);
}

/* ================================================================
   SENSOR MESSAGE PROCESSING
   ================================================================ */
void processSensorMessage(char* topic, byte* message, unsigned int length) {
  StaticJsonDocument<512> doc;
  if (deserializeJson(doc, message, length)) return;

  float temperature = doc["temperature"] | 0.0f;
  float humidity    = doc["humidity"]    | 0.0f;
  float soil        = doc["soil"]        | 0.0f;
  float air         = doc["air"]         | 0.0f;

  String topicStr = String(topic);

  if (topicStr == TOPIC_ZONE1_SENSOR) {
    zone1 = {temperature, humidity, soil, air, millis(), true};
    Serial.printf("[MQTT] Zone1 ← Temp:%.1fC Hum:%.1f%% Soil:%.1f%% Air:%.0f\n",
                  temperature, humidity, soil, air);
  }
  else if (topicStr == TOPIC_ZONE2_SENSOR) {
    zone2 = {temperature, humidity, soil, air, millis(), true};
    Serial.printf("[MQTT] Zone2 ← Temp:%.1fC Hum:%.1f%% Soil:%.1f%% Air:%.0f\n",
                  temperature, humidity, soil, air);
  }
}

/* ================================================================
   SAVE CROP + STAGE TO NVS
   ================================================================ */
void saveCropsToNVS() {
  prefs.begin("agri", false);
  prefs.putString("z1crop",  zone1Crop);
  prefs.putString("z1stage", zone1Stage);
  prefs.putString("z2crop",  zone2Crop);
  prefs.putString("z2stage", zone2Stage);
  prefs.end();
  Serial.printf("[NVS] Saved → Z1:%s/%s  Z2:%s/%s\n",
                zone1Crop.c_str(), zone1Stage.c_str(),
                zone2Crop.c_str(), zone2Stage.c_str());
}

/* ================================================================
   MQTT CALLBACK
   ================================================================ */
void onMqttMessage(char* topic, byte* message, unsigned int length) {
  String topicStr = String(topic);

  // Zone sensor data
  if (topicStr == TOPIC_ZONE1_SENSOR || topicStr == TOPIC_ZONE2_SENSOR) {
    processSensorMessage(topic, message, length);
    return;
  }

  // Crop + Stage configuration (from dashboard or retained message)
  if (topicStr == TOPIC_CROP_CONFIG || topicStr == TOPIC_RELAY_CMD) {
    StaticJsonDocument<512> doc;
    if (deserializeJson(doc, message, length)) return;

    bool changed = false;

    // Accept both "zone1_crop" and "Zone1" keys for compatibility
    if (doc["zone1_crop"].is<const char*>()) {
      zone1Crop  = doc["zone1_crop"].as<String>();
      changed = true;
    }
    if (doc["zone1_stage"].is<const char*>()) {
      zone1Stage = doc["zone1_stage"].as<String>();
    }
    if (doc["zone2_crop"].is<const char*>()) {
      zone2Crop  = doc["zone2_crop"].as<String>();
      changed = true;
    }
    if (doc["zone2_stage"].is<const char*>()) {
      zone2Stage = doc["zone2_stage"].as<String>();
    }

    if (changed) {
      saveCropsToNVS();
      Serial.printf("[CONFIG] Updated → Z1:%s/%s  Z2:%s/%s\n",
                    zone1Crop.c_str(), zone1Stage.c_str(),
                    zone2Crop.c_str(), zone2Stage.c_str());
    }
    return;
  }
}

/* ================================================================
   DECIDE FAN + UV FOR A SINGLE ZONE (stage-aware)
   ================================================================ */
void decideZone(ZoneData &zone, String crop, String stage, int &fan, int &uv) {
  CropConfig config = getCropConfig(crop, stage);

  // Fan: ON when actual temperature exceeds target
  fan = (zone.temperature > config.temperature) ? 1 : 0;

  // UV: ON between 06:00–23:00 for Medium/High light crops
  struct tm timeinfo;
  int hour = 12; // safe default (daytime) if NTP not yet synced
  if (getLocalTime(&timeinfo, 10)) hour = timeinfo.tm_hour;
  bool daylight = (hour >= 6 && hour <= 23);
  bool needsLight = (String(config.light) == "Medium" || String(config.light) == "High");
  uv = (daylight && needsLight) ? 1 : 0;
}

/* ================================================================
   AUTONOMOUS HARDWARE ENGINE (runs every 2 seconds)
   ================================================================ */
void runAIController() {
  unsigned long now = millis();

  bool z1Fresh = zone1.received && ((now - zone1.lastSeen) <= SENSOR_TIMEOUT_MS);
  bool z2Fresh = zone2.received && ((now - zone2.lastSeen) <= SENSOR_TIMEOUT_MS);

  // Nothing received yet → keep everything OFF
  if (!z1Fresh && !z2Fresh) {
    allRelaysOff();
    Serial.println("[ENGINE] No sensor data yet. All relays OFF.");
    return;
  }

  // ── Zone 1 Fan + UV ───────────────────────────────────────────
  if (z1Fresh) {
    decideZone(zone1, zone1Crop, zone1Stage, zone1_fan, zone1_uv);
  } else {
    zone1_fan = 0; zone1_uv = 0;
  }

  // ── Zone 2 Fan + UV ───────────────────────────────────────────
  if (z2Fresh) {
    decideZone(zone2, zone2Crop, zone2Stage, zone2_fan, zone2_uv);
  } else {
    zone2_fan = 0; zone2_uv = 0;
  }

  // ── Shared Sprinkler  (stage-aware soil targets) ──────────────
  CropConfig c1 = getCropConfig(zone1Crop, zone1Stage);
  CropConfig c2 = getCropConfig(zone2Crop, zone2Stage);

  bool z1Dry       = z1Fresh && (zone1.soil < c1.soil);
  bool z2Dry       = z2Fresh && (zone2.soil < c2.soil);
  bool z1Satisfied = z1Fresh && (zone1.soil >= c1.soil);
  bool z2Satisfied = z2Fresh && (zone2.soil >= c2.soil);

  // OVERWATER GUARD: If any active zone already hit its target → Sprinkler OFF
  // Only irrigate if a zone is genuinely dry and no zone is overwatered
  if (z1Satisfied || z2Satisfied) {
    sprinkler = 0;   // At least one zone satisfied → stop watering
  } else if (z1Dry || z2Dry) {
    sprinkler = 1;   // At least one zone is dry → water
  } else {
    sprinkler = 0;
  }

  // ── Central Water Pump  (tank-level safety) ───────────────────
  readWaterLevel();
  if (waterPercent == 0 || waterRaw < 100) {
    water_pump = 0;  // Empty tank or disconnected sensor → NEVER run pump dry
  } else if (waterPercent < 30) {
    water_pump = 1;  // Refill when low (1%–29%)
  } else {
    water_pump = 0;  // Tank is adequately full
  }

  // Apply decisions to physical relay pins
  applyRelays();

  // ── Serial Debug ──────────────────────────────────────────────
  Serial.println("---------- [AUTONOMOUS ENGINE] ----------");
  if (z1Fresh) {
    Serial.printf("Z1 [%s/%s] Temp=%.1fC>%.0f→Fan=%s | Soil=%.1f%%vs%.0f%%→Spr=%s\n",
      zone1Crop.c_str(), zone1Stage.c_str(),
      zone1.temperature, c1.temperature, zone1_fan ? "ON" : "OFF",
      zone1.soil, c1.soil, sprinkler ? "ON" : "OFF");
  } else { Serial.println("Z1: OFFLINE/STALE"); }

  if (z2Fresh) {
    Serial.printf("Z2 [%s/%s] Temp=%.1fC>%.0f→Fan=%s | Soil=%.1f%%vs%.0f%%\n",
      zone2Crop.c_str(), zone2Stage.c_str(),
      zone2.temperature, c2.temperature, zone2_fan ? "ON" : "OFF",
      zone2.soil, c2.soil);
  } else { Serial.println("Z2: OFFLINE/STALE"); }

  Serial.printf("Pump:%s Spr:%s Z1Fan:%s Z1UV:%s Z2Fan:%s Z2UV:%s Water:%d%%\n",
    water_pump?"ON":"OFF", sprinkler?"ON":"OFF",
    zone1_fan?"ON":"OFF",  zone1_uv?"ON":"OFF",
    zone2_fan?"ON":"OFF",  zone2_uv?"ON":"OFF",
    waterPercent);
  Serial.println("-----------------------------------------");
}

/* ================================================================
   PUBLISH RELAY STATUS → MQTT (for dashboard)
   ================================================================ */
void publishStatus() {
  StaticJsonDocument<1024> doc;
  doc["device"]     = "relay";
  doc["status"]     = "online";
  doc["water_level"]= waterPercent;
  doc["raw_adc"]    = waterRaw;
  doc["water_pump"] = water_pump;
  doc["sprinkler"]  = sprinkler;
  doc["zone1_fan"]  = zone1_fan;
  doc["zone1_uv"]   = zone1_uv;
  doc["zone2_fan"]  = zone2_fan;
  doc["zone2_uv"]   = zone2_uv;
  doc["zone1_crop"] = zone1Crop;
  doc["zone1_stage"]= zone1Stage;
  doc["zone2_crop"] = zone2Crop;
  doc["zone2_stage"]= zone2Stage;
  // Mirror zone sensor data for dashboard
  doc["zone1_temperature"] = zone1.temperature;
  doc["zone1_humidity"]    = zone1.humidity;
  doc["zone1_soil"]        = zone1.soil;
  doc["zone1_air"]         = zone1.air;
  doc["zone2_temperature"] = zone2.temperature;
  doc["zone2_humidity"]    = zone2.humidity;
  doc["zone2_soil"]        = zone2.soil;
  doc["zone2_air"]         = zone2.air;

  String out;
  serializeJson(doc, out);
  mqtt.publish(TOPIC_RELAY_STATUS, out.c_str(), true);
}

/* ================================================================
   WIFI
   ================================================================ */
void connectWiFi() {
  if (WiFi.status() == WL_CONNECTED) return;
  Serial.printf("[WiFi] Connecting to %s", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  unsigned long t = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - t < 15000) {
    delay(500); Serial.print(".");
  }
  Serial.println();
  if (WiFi.status() == WL_CONNECTED) {
    WiFi.setSleep(false);
    Serial.printf("[WiFi] Connected → %s\n", WiFi.localIP().toString().c_str());
  } else {
    Serial.println("[WiFi] Failed");
  }
}

/* ================================================================
   MQTT
   ================================================================ */
void connectMQTT() {
  if (mqtt.connected()) return;
  Serial.println("[MQTT] Connecting to HiveMQ...");
  bool ok = mqtt.connect(
    MQTT_CLIENT_ID, MQTT_USERNAME, MQTT_PASSWORD,
    TOPIC_RELAY_STATUS, 1, true,
    "{\"device\":\"relay\",\"status\":\"offline\"}"
  );
  if (ok) {
    Serial.println("[MQTT] Connected");
    mqtt.subscribe(TOPIC_ZONE1_SENSOR,  1);
    mqtt.subscribe(TOPIC_ZONE2_SENSOR,  1);
    mqtt.subscribe(TOPIC_RELAY_CMD,     1);
    mqtt.subscribe(TOPIC_CROP_CONFIG,   1); // Retained crop+stage from dashboard
    mqtt.publish(TOPIC_RELAY_STATUS, "{\"device\":\"relay\",\"status\":\"online\"}", true);
  } else {
    Serial.printf("[MQTT] Failed rc=%d\n", mqtt.state());
  }
}

/* ================================================================
   SETUP
   ================================================================ */
void setup() {
  Serial.begin(115200);
  delay(500);

  // CRITICAL: Set all 16 relay pins to INPUT_PULLUP immediately on boot
  // This ensures all relay LEDs are OFF before any WiFi/MQTT connection
  allRelaysOff();

  pinMode(WATER_SENSOR, INPUT);

  Serial.println("\n==========================================");
  Serial.println("  AgriVision AI - Autonomous Relay Node  ");
  Serial.println("  Stage-Aware Crop Config | INPUT_PULLUP  ");
  Serial.println("==========================================");

  // Load crop + stage from NVS flash (survives power cuts)
  prefs.begin("agri", true);
  zone1Crop  = prefs.getString("z1crop",  "Paddy");
  zone1Stage = prefs.getString("z1stage", "Vegetative");
  zone2Crop  = prefs.getString("z2crop",  "Tomato");
  zone2Stage = prefs.getString("z2stage", "Vegetative");
  prefs.end();
  Serial.printf("[NVS] Loaded → Z1:%s/%s  Z2:%s/%s\n",
                zone1Crop.c_str(), zone1Stage.c_str(),
                zone2Crop.c_str(), zone2Stage.c_str());

  // WiFi
  connectWiFi();

  if (WiFi.status() == WL_CONNECTED) {
    // NTP time (for UV schedule — IST = UTC+5:30)
    configTime(19800, 0, "pool.ntp.org", "time.nist.gov");
    // OTA
    ArduinoOTA.setHostname(MQTT_CLIENT_ID);
    ArduinoOTA.begin();
  }

  // MQTT
  espClient.setInsecure();
  mqtt.setServer(MQTT_BROKER_HOST, MQTT_BROKER_PORT);
  mqtt.setCallback(onMqttMessage);
  mqtt.setBufferSize(1024);
  mqtt.setKeepAlive(60);

  if (WiFi.status() == WL_CONNECTED) connectMQTT();

  Serial.println("[SYSTEM] Ready. Autonomous control active.");
}

/* ================================================================
   MAIN LOOP
   ================================================================ */
void loop() {
  unsigned long now = millis();

  if (WiFi.status() == WL_CONNECTED) ArduinoOTA.handle();

  // WiFi reconnect
  if (WiFi.status() != WL_CONNECTED) {
    allRelaysOff();
    if (now - lastWiFiRetry >= WIFI_RETRY_INTERVAL) {
      lastWiFiRetry = now;
      connectWiFi();
    }
    delay(10);
    return;
  }

  // MQTT reconnect
  if (!mqtt.connected()) {
    allRelaysOff();
    if (now - lastMQTTRetry >= MQTT_RETRY_INTERVAL) {
      lastMQTTRetry = now;
      connectMQTT();
    }
    delay(10);
    return;
  }

  mqtt.loop();

  // Autonomous decision every 2s
  if (now - lastDecisionTime >= DECISION_INTERVAL_MS) {
    lastDecisionTime = now;
    runAIController();
  }

  // Publish status for dashboard every 2s
  if (now - lastTelemetryTime >= TELEMETRY_INTERVAL_MS) {
    lastTelemetryTime = now;
    publishStatus();
  }

  delay(5);
}