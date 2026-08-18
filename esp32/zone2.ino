/*
  AgriVision AI - ESP32 Zone 2 Sensor Node
  =========================================

  Sensors:
    DHT22       -> GPIO 4
    Soil        -> GPIO 35
    MQ135       -> GPIO 34

  Communication:
    HiveMQ Cloud MQTT + TLS
*/

#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <DHT.h>
#include <ArduinoOTA.h>

// ============================================================
// PINS
// ============================================================

#define DHTPIN       4
#define DHTTYPE      DHT22
#define MQ135_PIN    34
#define SOIL_PIN     35

DHT dht(DHTPIN, DHTTYPE);

// ============================================================
// WIFI
// ============================================================

const char* WIFI_SSID     = "Your WIFI_SSID";
const char* WIFI_PASSWORD = "Your WIFI_PASSWORD";

// ============================================================
// HIVEMQ CLOUD
// ============================================================

#define MQTT_BROKER_HOST "YOUR_HIVEMQ_BROKER_HOST"
#define MQTT_BROKER_PORT YOUR_HIVEMQ_BROKER_PORT

#define MQTT_CLIENT_ID "AgriVision-Zone2"

#define MQTT_USERNAME "YOUR_HIVEMQ_USERNAME"
#define MQTT_PASSWORD "YOUR_HIVEMQ_PASSWORD"

// ============================================================
// TOPICS
// ============================================================

#define TOPIC_SENSORS "agrivision/zone2/sensors"
#define TOPIC_STATUS  "agrivision/zone2/status"

// ============================================================
// TIMING
// ============================================================

const unsigned long PUBLISH_INTERVAL_MS = 2000;
const unsigned long MQTT_RETRY_INTERVAL  = 5000;

unsigned long lastPublish = 0;
unsigned long lastMqttRetry = 0;

// ============================================================
// MQTT
// ============================================================

WiFiClientSecure espClient;
PubSubClient mqtt(espClient);

// ============================================================
// WIFI
// ============================================================

void connectWiFi() {

  if (WiFi.status() == WL_CONNECTED)
    return;

  Serial.print("[WiFi] Connecting to ");
  Serial.println(WIFI_SSID);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  unsigned long start = millis();

  while (
    WiFi.status() != WL_CONNECTED &&
    millis() - start < 15000
  ) {

    delay(500);
    Serial.print(".");
  }

  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {

    WiFi.setSleep(false);
    WiFi.setTxPower(WIFI_POWER_19_5dBm);

    Serial.println("[WiFi] Connected");

    Serial.print("[WiFi] IP: ");
    Serial.println(WiFi.localIP());

  } else {

    Serial.println("[WiFi] Connection failed");
  }
}

// ============================================================
// MQTT CONNECTION
// ============================================================

void tryConnectMQTT() {

  if (mqtt.connected())
    return;

  Serial.println("[MQTT] Connecting to HiveMQ Cloud...");

  bool connected = mqtt.connect(
    MQTT_CLIENT_ID,
    MQTT_USERNAME,
    MQTT_PASSWORD,
    TOPIC_STATUS,
    1,
    true,
    "offline"
  );

  if (connected) {

    Serial.println("[MQTT] Connected");

    mqtt.publish(
      TOPIC_STATUS,
      "online",
      true
    );

  } else {

    Serial.print("[MQTT] Connection failed rc=");
    Serial.println(mqtt.state());
  }
}

// ============================================================
// SOIL
// ============================================================

float readSoilPercent() {

  long soilSum = 0;
  const int sampleCount = 10;

  for (int i = 0; i < sampleCount; i++) {
    soilSum += analogRead(SOIL_PIN);
    delay(5);
  }

  int soilRaw = soilSum / sampleCount;

  // Typical Soil Sensors (Capacitive & Resistive):
  // In Air (Dry): ~3200 - 4095 -> 0%
  // In Water (Wet): ~1200 - 1500 -> 100%
  const int DRY_ADC = 3300;
  const int WET_ADC = 1400;

  float soilPercent = 0.0;

  if (soilRaw <= 100) {
    // Disconnected or 0V dry sensor
    soilPercent = 0.0;
  } else if (soilRaw >= DRY_ADC) {
    soilPercent = 0.0;
  } else if (soilRaw <= WET_ADC) {
    soilPercent = 100.0;
  } else {
    soilPercent = (float)(DRY_ADC - soilRaw) * 100.0 / (float)(DRY_ADC - WET_ADC);
  }

  soilPercent = constrain(soilPercent, 0.0f, 100.0f);
  Serial.printf("[SOIL] Zone 2 Raw ADC: %d -> %.1f%%\n", soilRaw, soilPercent);

  return soilPercent;
}

// ============================================================
// OTA
// ============================================================

void initOTA() {

  ArduinoOTA.setHostname(MQTT_CLIENT_ID);

  ArduinoOTA.onStart([]() {
    Serial.println("[OTA] Starting...");
  });

  ArduinoOTA.onEnd([]() {
    Serial.println("\n[OTA] Done!");
  });

  ArduinoOTA.onProgress([](unsigned int progress, unsigned int total) {

    Serial.printf(
      "[OTA] %u%%\r",
      (progress * 100) / total
    );
  });

  ArduinoOTA.onError([](ota_error_t error) {

    Serial.printf(
      "[OTA] Error[%u]\n",
      error
    );
  });

  ArduinoOTA.begin();

  Serial.println(
    "[OTA] Ready. Hostname: " MQTT_CLIENT_ID
  );
}

// ============================================================
// SETUP
// ============================================================

void setup() {

  Serial.begin(115200);

  delay(500);

  dht.begin();

  analogReadResolution(12);
  analogSetAttenuation(ADC_11db);

  connectWiFi();

  espClient.setInsecure();

  mqtt.setServer(
    MQTT_BROKER_HOST,
    MQTT_BROKER_PORT
  );

  mqtt.setKeepAlive(60);
  mqtt.setBufferSize(512);

  if (WiFi.status() == WL_CONNECTED) {

    initOTA();
    tryConnectMQTT();
  }

  Serial.println("[SYSTEM] Zone 2 ready");
}

// ============================================================
// LOOP
// ============================================================

void loop() {

  // OTA
  if (WiFi.status() == WL_CONNECTED) {
    ArduinoOTA.handle();
  }

  // Wi-Fi
  if (WiFi.status() != WL_CONNECTED) {

    connectWiFi();

    delay(10);
    return;
  }

  // MQTT
  if (!mqtt.connected()) {

    unsigned long now = millis();

    if (now - lastMqttRetry >= MQTT_RETRY_INTERVAL) {

      lastMqttRetry = now;

      tryConnectMQTT();
    }

    delay(10);
    return;
  }

  mqtt.loop();

  // Sensor publishing
  unsigned long now = millis();

  if (now - lastPublish < PUBLISH_INTERVAL_MS)
    return;

  lastPublish = now;

  // ----------------------------------------------------------
  // DHT22 (With Fallback for reliable MQTT transmission)
  // ----------------------------------------------------------
  static float lastValidTemp = 25.0;
  static float lastValidHum  = 60.0;

  float temperature = dht.readTemperature();
  float humidity    = dht.readHumidity();

  if (!isnan(temperature) && !isnan(humidity)) {
    lastValidTemp = temperature;
    lastValidHum  = humidity;
  } else {
    Serial.println("[DHT] Read jitter -> using last valid values");
    temperature = lastValidTemp;
    humidity    = lastValidHum;
  }

  // ----------------------------------------------------------
  // Soil + air
  // ----------------------------------------------------------
  float soilPercent = readSoilPercent();
  int airValue = analogRead(MQ135_PIN);

  // ----------------------------------------------------------
  // JSON
  // ----------------------------------------------------------
  char payload[200];
  snprintf(
    payload,
    sizeof(payload),
    "{\"device\":\"zone2\","
    "\"temperature\":%.1f,"
    "\"humidity\":%.1f,"
    "\"soil\":%.1f,"
    "\"air\":%d}",
    temperature,
    humidity,
    soilPercent,
    airValue
  );

  Serial.printf("[MQTT] Zone 2 TX: %s\n", payload);

  if (mqtt.publish(TOPIC_SENSORS, payload, true)) {
    Serial.println("[MQTT] Published OK");
  } else {
    Serial.println("[MQTT] Publish FAILED");
  }
}