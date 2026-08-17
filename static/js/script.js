console.log("AgriVision AI Dashboard Loaded");
const MAX_POINTS = 20;
let labels = [];

let r1Temp = [];
let r1Hum = [];
let r1Soil = [];
let r1Air = [];

let r2Temp = [];
let r2Hum = [];
let r2Soil = [];
let r2Air = [];

let lastGraphTime = "";
let wasOffline = false;
let offlineNotificationShown = false;
let graphFrozen = false;
let offlinePointAdded = false;

function showOffline() {
  const box = document.getElementById("systemStatus");
  box.className = "status offline";
  box.innerHTML = "🔴 System Offline";
}

function showOnline() {
  const box = document.getElementById("systemStatus");
  box.className = "system-online";
  box.innerHTML = "🟢 System Online - Live Data";
}

function createChart(id, label, color) {
  const chartColor = color;
  const fillColor = chartColor + "22";

  return new Chart(document.getElementById(id), {
    type: "line",
    data: {
      labels: [],
      datasets: [
        {
          label: label,
          data: [],
          borderColor: chartColor,
          backgroundColor: (context) => {
            const chart = context.chart;
            const { ctx, chartArea } = chart;
            if (!chartArea) return fillColor;
            const gradient = ctx.createLinearGradient(
              0,
              chartArea.top,
              0,
              chartArea.bottom,
            );
            gradient.addColorStop(0, fillColor);
            gradient.addColorStop(1, "rgba(255,255,255,0)");
            return gradient;
          },
          borderWidth: 3,
          fill: true,
          tension: 0.45,
          cubicInterpolationMode: "monotone",
          pointRadius: 0,
          pointHoverRadius: 6,
          pointHoverBorderWidth: 2,
          pointHoverBackgroundColor: chartColor,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: {
        duration: 300,
        easing: "easeOutQuart",
      },
      interaction: {
        mode: "index",
        intersect: false,
      },
      plugins: {
        legend: {
          display: false,
        },
        tooltip: {
          backgroundColor: "rgba(7, 17, 31, 0.95)",
          titleColor: "#f8fbff",
          bodyColor: "#f8fbff",
          borderColor: chartColor,
          borderWidth: 1,
          callbacks: {
            label: function (context) {
              const unit = label.includes("Temperature")
                ? "°C"
                : label.includes("Humidity") ||
                    label.includes("Soil") ||
                    label.includes("Air") ||
                    label.includes("Light")
                  ? "%"
                  : "";
              return `${context.parsed.y.toFixed(1)} ${unit}`.trim();
            },
            title: function (items) {
              return items[0].label;
            },
          },
        },
        title: {
          display: true,
          text: label,
          color: "#10253f",
          font: {
            size: 14,
            weight: "600",
          },
          padding: {
            top: 12,
            bottom: 8,
          },
        },
      },
      scales: {
        y: {
          beginAtZero: true,
          max: 100,
          ticks: {
            stepSize: 10,
          },
          grid: {
            color: "rgba(16, 37, 63, 0.12)",
          },
        },
        x: {
          grid: {
            display: false,
          },
          ticks: {
            maxRotation: 0,
          },
        },
      },
      elements: {
        line: {
          hoverBorderWidth: 4,
        },
      },
    },
  });
}

const rack1TempChart = createChart(
  "r1TempChart",
  "🌡️ Temperature (°C)",
  "#ff5722",
);
const rack1HumChart = createChart("r1HumChart", "💧 Humidity (%)", "#2196f3");
const rack1SoilChart = createChart(
  "r1SoilChart",
  "🌱 Soil Moisture (%)",
  "#4caf50",
);
const rack1AirChart = createChart(
  "r1AirChart",
  "🍃 Air Quality (%)",
  "#9c27b0",
);

const rack2TempChart = createChart(
  "r2TempChart",
  "🌡️ Temperature (°C)",
  "#ff5722",
);
const rack2HumChart = createChart("r2HumChart", "💧 Humidity (%)", "#2196f3");
const rack2SoilChart = createChart(
  "r2SoilChart",
  "🌱 Soil Moisture (%)",
  "#4caf50",
);
const rack2AirChart = createChart(
  "r2AirChart",
  "🍃 Air Quality (%)",
  "#9c27b0",
);

function pushValue(array, value) {
  array.push(value);
  if (array.length > MAX_POINTS) {
    array.shift();
  }
}

function updateChart(chart, history) {
  chart.data.labels = labels;
  chart.data.datasets[0].data = history;
  chart.update();
}


  // Update Rack 1 UI
  function updateRack1(data) {
    // Temperature, Humidity, Soil, Air
    document.getElementById("r1Temperature").innerHTML = data.Temperature.toFixed(1) + " °C";
    document.getElementById("r1Humidity").innerHTML = data.Humidity.toFixed(1) + " %";
    document.getElementById("r1Soil").innerHTML = data.Soil_Moisture.toFixed(1) + " %";
    const r1AirPercent = normalizeAirChartValue(data.Air);
    document.getElementById("r1Air").innerHTML = r1AirPercent.toFixed(1) + " %";
    // Pump, Sprinkler, Fan, UV (Light_Output)
    document.getElementById("r1Pump").innerHTML = data.Pump ? "ON" : "OFF";
    document.getElementById("r1Sprinkler").innerHTML = data.Sprinkler ? "ON" : "OFF";
    document.getElementById("r1Fan").innerHTML = data.Fan ? "ON" : "OFF";
    document.getElementById("r1Grow").innerHTML = data.Light_Output ? "ON" : "OFF";
    // Common Water Tank (shared across racks)
    const commonWaterValue = data.Water_Level.toFixed(1) + " %";
    const cwElem = document.getElementById("commonWater");
    if (cwElem) cwElem.innerHTML = commonWaterValue;
    const cwElem2 = document.getElementById("commonWaterLevel");
    if (cwElem2) cwElem2.innerHTML = commonWaterValue;
    console.log("[Dashboard] Rack 1 assignments", {
      r1Soil: data.Soil_Moisture,
      commonWater: data.Water_Level,
    });
  }

function updateRack2(data) {
  document.getElementById("r2Temperature").innerHTML = data.Temperature.toFixed(1) + " °C";
  document.getElementById("r2Humidity").innerHTML = data.Humidity.toFixed(1) + " %";
  document.getElementById("r2Soil").innerHTML = data.Soil_Moisture.toFixed(1) + " %";
  // Air quality
  const r2AirPercent = normalizeAirChartValue(data.Air);
  document.getElementById("r2Air").innerHTML = r2AirPercent.toFixed(1) + " %";
  // Pump, Sprinkler, Fan, UV (Light_Output)
  document.getElementById("r2Pump").innerHTML = data.Pump ? "ON" : "OFF";
  document.getElementById("r2Sprinkler").innerHTML = data.Sprinkler ? "ON" : "OFF";
  document.getElementById("r2Fan").innerHTML = data.Fan ? "ON" : "OFF";
  document.getElementById("r2Grow").innerHTML = data.Light_Output ? "ON" : "OFF";
  // Common Water Tank shared – update placeholders in both Rack 1 and Rack 2
  const commonWaterValue = data.Water_Level.toFixed(1) + " %";
  const cwElem = document.getElementById("commonWater");
  if (cwElem) cwElem.innerHTML = commonWaterValue;
  const cwElem2 = document.getElementById("commonWaterLevel");
  if (cwElem2) cwElem2.innerHTML = commonWaterValue;
  console.log("[Dashboard] Rack 2 assignments", {
    r2Soil: data.Soil_Moisture,
    commonWater: data.Water_Level,
  });
}

function normalizeAirChartValue(value) {
  return Math.max(0, Math.min(100, 100 - value / 15));
}

function updateRack1Charts(data) {
  pushValue(r1Temp, data.Temperature);
  pushValue(r1Hum, data.Humidity);
  pushValue(r1Soil, data.Soil_Moisture);
  pushValue(r1Air, normalizeAirChartValue(data.Air));

  updateChart(rack1TempChart, r1Temp);
  updateChart(rack1HumChart, r1Hum);
  updateChart(rack1SoilChart, r1Soil);
  updateChart(rack1AirChart, r1Air);
}

function updateRack2Charts(data) {
  pushValue(r2Temp, data.Temperature);
  pushValue(r2Hum, data.Humidity);
  pushValue(r2Soil, data.Soil_Moisture);
  pushValue(r2Air, normalizeAirChartValue(data.Air));

  updateChart(rack2TempChart, r2Temp);
  updateChart(rack2HumChart, r2Hum);
  updateChart(rack2SoilChart, r2Soil);
  updateChart(rack2AirChart, r2Air);
}

function calculateHealth(data) {
  let score = 100;

  if (data.Temperature > 35) score -= 15;
  if (data.Humidity < 40) score -= 10;
  if (data.Soil_Moisture < 35) score -= 30;
  if (data.Water_Level < 20) score -= 20;
  if (data.Light < 30) score -= 10;
  if (data.Air > 1500) score -= 15;

  if (score < 0) score = 0;

  return score;
}

function updateHealth(zone, data) {
  const health = calculateHealth(data);
  document.getElementById(zone + "Health").innerHTML = health + " %";

  let txt = "Excellent";

  if (health < 90) txt = "Healthy";
  if (health < 75) txt = "Needs Attention";
  if (health < 55) txt = "Poor";

  document.getElementById(zone + "HealthStatus").innerHTML = txt;
}

function formatDateTime(now = new Date()) {
  return {
    date: now.toLocaleDateString("en-GB"),
    time: now.toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
      hour12: true,
    }),
    fullTime: now.toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: true,
    }),
  };
}

function addEvent(tableId, rack, device, action) {
  const body = document.getElementById(tableId);
  if (!body) return;

  const now = new Date();
  const { date, time } = formatDateTime(now);

  const row = body.insertRow(0);
  row.insertCell(0).innerHTML = date;
  row.insertCell(1).innerHTML = time;
  row.insertCell(2).innerHTML = rack;
  row.insertCell(3).innerHTML = device;
  row.insertCell(4).innerHTML = action;
  row.insertCell(5).innerHTML = "✔";

  while (body.rows.length > 10) body.deleteRow(10);
}

function addNotification(boxId, msg, type = "info", extra = "") {
  const box = document.getElementById(boxId);
  if (!box) return;

  const now = new Date();
  const { date, time, fullTime } = formatDateTime(now);
  const div = document.createElement("div");
  div.className = `notification ${type}`;
  div.innerHTML = `
    <div class="notificationTop">
      <span>${date}</span>
      <span>${time}</span>
    </div>
    <div class="notificationMessage">${msg}</div>
    <div class="notificationMeta">${extra || fullTime}</div>
  `;

  box.prepend(div);

  while (box.children.length > 20) box.removeChild(box.lastChild);
}

let alertHistory = [];
let lastCriticalAlertKey = "";

function playAlertTone() {
  if (typeof window === "undefined") return;
  const AudioContextClass = window.AudioContext || window.webkitAudioContext;
  if (!AudioContextClass) return;

  const audioContext = new AudioContextClass();
  const oscillator = audioContext.createOscillator();
  const gainNode = audioContext.createGain();

  oscillator.type = "triangle";
  oscillator.frequency.value = 880;
  gainNode.gain.value = 0.04;
  oscillator.connect(gainNode);
  gainNode.connect(audioContext.destination);
  oscillator.start();

  setTimeout(() => {
    gainNode.gain.exponentialRampToValueAtTime(
      0.0001,
      audioContext.currentTime + 0.25,
    );
    oscillator.stop(audioContext.currentTime + 0.25);
    setTimeout(() => audioContext.close(), 300);
  }, 120);
}

function addSystemAlert(title, rack, device, severity, message = "") {
  const box = document.getElementById("systemAlerts");
  if (!box) return;

  const alertKey = `${severity}-${rack}-${device}-${title}`;
  if (alertHistory.includes(alertKey)) return;
  alertHistory.push(alertKey);
  if (alertHistory.length > 30) alertHistory.shift();

  const now = new Date();
  const { date, time } = formatDateTime(now);
  const severityClass = severity.toLowerCase();
  const item = document.createElement("div");
  item.className = `alertItem ${severityClass}`;
  item.innerHTML = `
    <div class="alertSeverity">${severity}</div>
    <div class="alertTitle">${title}</div>
    <div class="alertMeta">${date} · ${time}</div>
    <div class="alertMeta">Rack: ${rack} · Device: ${device}</div>
    ${message ? `<div class="alertMeta">${message}</div>` : ""}
  `;

  box.prepend(item);
  while (box.children.length > 20) box.removeChild(box.lastChild);

  if (
    severity.toLowerCase() === "critical" &&
    alertKey !== lastCriticalAlertKey
  ) {
    lastCriticalAlertKey = alertKey;
    playAlertTone();
    showAlertPopup(title, rack, device, severity, time);
  }
}

function detectSystemFaults(zoneKey, data) {
  const rackLabel = zoneKey === "r1" ? "Rack 1" : "Rack 2";
  const sensorNum = zoneKey === "r1" ? 1 : 2;

  const checkSensor = (
    label,
    value,
    min,
    max,
    deviceBaseName,
    severity = "Warning",
  ) => {
    const deviceName = `${deviceBaseName} ${sensorNum}`;
    const numericValue = Number(value);
    if (
      value === null ||
      value === undefined ||
      value === "" ||
      !Number.isFinite(numericValue)
    ) {
      addSystemAlert(
        `${deviceName} Failure`,
        rackLabel,
        deviceName,
        severity,
        `${label} sensor ${sensorNum} disconnected or invalid`,
      );
      return;
    }

    if (numericValue < min || numericValue > max) {
      addSystemAlert(
        `${deviceName} Failure`,
        rackLabel,
        deviceName,
        severity,
        `${label} reading for sensor ${sensorNum} is outside expected range`,
      );
    }
  };

  checkSensor(
    "Temperature",
    data.Temperature,
    -30,
    80,
    "Temperature Sensor",
    "Warning",
  );
  checkSensor("Humidity", data.Humidity, 0, 100, "Humidity Sensor", "Warning");
  checkSensor(
    "Soil Moisture",
    data.Soil_Moisture,
    0,
    100,
    "Soil Sensor",
    "Warning",
  );
  checkSensor(
    "Water Level",
    data.Water_Level,
    0,
    100,
    "Water Level Sensor",
    "Critical",
  );
  checkSensor(
    "Air Quality",
    data.Air,
    0,
    5000,
    "Air Quality Sensor",
    "Warning",
  );
  checkSensor("Light", data.Light, 0, 100, "Light Sensor", "Warning");

  if (typeof data.Pump !== "boolean") {
    addSystemAlert(
      `Pump ${sensorNum} Not Responding`,
      rackLabel,
      `Pump ${sensorNum}`,
      "Critical",
      `Pump ${sensorNum} state is invalid or unavailable`,
    );
  }

  if (typeof data.Fan !== "boolean") {
    addSystemAlert(
      `Cooling Fan ${sensorNum} Failure`,
      rackLabel,
      `Cooling Fan ${sensorNum}`,
      "Critical",
      `Cooling Fan ${sensorNum} state is invalid or unavailable`,
    );
  }
}

function showAlertPopup(title, rack, device, severity, time) {
  const container = document.getElementById("alertPopupContainer");
  if (!container) return;

  const popup = document.createElement("div");
  popup.className = `alertPopup ${severity.toLowerCase()}`;
  popup.innerHTML = `
    <strong>🚨 ${severity} ALERT</strong><br/>
    <div>${title}</div>
    <div>${rack}</div>
    <div>${time}</div>
  `;

  container.appendChild(popup);
  setTimeout(() => {
    popup.remove();
  }, 5000);
}

const lastAutomationState = {};

function automation(zone, data) {
  const signature = `${data.Pump ? 1 : 0}${data.Fan ? 1 : 0}${data.Light_Output ? 1 : 0}${data.Soil_Moisture < 30 ? 1 : 0}${data.Water_Level < 20 ? 1 : 0}${data.Temperature > 35 ? 1 : 0}${data.Light < 30 ? 1 : 0}`;

  if (lastAutomationState[zone] === signature) return;
  lastAutomationState[zone] = signature;

  const rackLabel = zone === "r1" ? "Rack 1" : "Rack 2";
  const sensorNum = zone === "r1" ? 1 : 2;

  if (data.Pump)
    addEvent("automationEvents", rackLabel, `Pump ${sensorNum}`, "Started");
  if (data.Fan)
    addEvent("automationEvents", rackLabel, `Fan ${sensorNum}`, "Started");
  if (data.Light_Output)
    addEvent("automationEvents", rackLabel, `UV Light ${sensorNum}`, "ON");

  if (data.Soil_Moisture < 30) {
    addNotification(
      "allNotifications",
      `${rackLabel} 🌱 Soil Moisture ${sensorNum} Low`,
      "warning",
      "Rack Alert",
    );
    addSystemAlert(
      "Soil Moisture Low",
      rackLabel,
      `Soil Sensor ${sensorNum}`,
      "Warning",
      `Low soil moisture detected on sensor ${sensorNum}`,
    );
  }
  if (data.Water_Level < 20) {
    addNotification(
      "allNotifications",
      `${rackLabel} 🚰 Water Tank Low`,
      "danger",
      "Critical Water Alert",
    );
    addSystemAlert(
      "Water Tank Low",
      rackLabel,
      `Water Level Sensor ${sensorNum}`,
      "Critical",
      `Tank water level is below threshold on sensor ${sensorNum}`,
    );
  }
  if (data.Temperature > 35) {
    addNotification(
      "allNotifications",
      `${rackLabel} 🔥 High Temperature ${sensorNum}`,
      "danger",
      "Critical Thermal Alert",
    );
    addSystemAlert(
      "High Temperature",
      rackLabel,
      `Temperature Sensor ${sensorNum}`,
      "Warning",
      `Temperature exceeded safe operating range on sensor ${sensorNum}`,
    );
  }
  if (data.Light < 30) {
    addNotification(
      "allNotifications",
      `${rackLabel} 💡 UV Light ${sensorNum} Activated`,
      "info",
      "Lighting Status",
    );
    addSystemAlert(
      "UV Light Activated",
      rackLabel,
      `UV Light ${sensorNum}`,
      "Info",
      `Lighting automation engaged for ${sensorNum}`,
    );
  }
}

function normalizeZoneData(zoneData, zoneName, relayData) {
  const normalized = { ...zoneData };

  normalized.Temperature = Number(normalized.Temperature || 0);
  normalized.Humidity = Number(normalized.Humidity || 0);
  normalized.Soil_Moisture = Number(normalized.Soil_Moisture || 0);
  normalized.Air = Number(normalized.Air || 0);
  normalized.Water_Level = Number(normalized.Water_Level || 0);

  const relayPrefix = zoneName;
  normalized.Pump = Boolean(relayData ? relayData[relayPrefix + "Pump"] : 0);
  normalized.Sprinkler = Boolean(relayData ? relayData.sprinkler : 0);
  normalized.Fan = Boolean(relayData ? relayData[relayPrefix + "Fan"] : 0);
  normalized.SharedPump = Boolean(relayData ? relayData.water_pump : 0);

  // The backend controller applies the existing 12 AM–6 AM night-mode cutoff
  // and returns the actual relay state for the selected crop.
  const relayUV = Boolean(relayData ? relayData[relayPrefix + "UV"] : 0);

  normalized.Light_Output = relayUV;

  // The live system has no standalone LDR sensor, so derive a synthetic Light
  // reading from the UV relay state so existing health/automation logic that
  // references data.Light keeps working. UV ON -> bright, UV OFF -> dark.
  if (!Number.isFinite(Number(normalized.Light))) {
    normalized.Light = relayUV ? 80 : 10;
  }

  return normalized;
}

let refreshInterval;

function seedInitialNotifications() {
  const box = document.getElementById("allNotifications");
  if (!box) return;
  box.innerHTML = "";
  addNotification(
    "allNotifications",
    "System ready",
    "info",
    "Dashboard online",
  );
  addSystemAlert(
    "System online",
    "All Racks",
    "Dashboard",
    "Info",
    "Monitoring service is running",
  );
}

async function loadAutomationHistory() {
  const apiBase = (typeof window.API_BASE_URL === "string" ? window.API_BASE_URL : "").replace(/\/+$/, "");
  try {
    const response = await fetch(apiBase + "/api/automation-events?limit=10");
    if (!response.ok) return;
    const data = await response.json();
    const body = document.getElementById("automationEvents");
    if (!body || !Array.isArray(data.data)) return;

    body.innerHTML = "";
    data.data.forEach((event) => {
      const row = body.insertRow(0);
      row.insertCell(0).innerHTML = event.date || "--";
      row.insertCell(1).innerHTML = event.time || "--";
      row.insertCell(2).innerHTML = event.rack || "--";
      row.insertCell(3).innerHTML = event.actuator || "--";
      row.insertCell(4).innerHTML = event.action || "--";
      row.insertCell(5).innerHTML = "✔";
    });
  } catch (error) {
    console.warn("Unable to load automation history", error);
  }
}

async function loadNotificationHistory() {
  const apiBase = (typeof window.API_BASE_URL === "string" ? window.API_BASE_URL : "").replace(/\/+$/, "");
  try {
    const response = await fetch(apiBase + "/api/notifications?limit=10");
    if (!response.ok) return;
    const data = await response.json();
    const box = document.getElementById("allNotifications");
    if (!box || !Array.isArray(data.data)) return;

    box.innerHTML = "";
    data.data.forEach((notification) => {
      const type = notification.severity === "critical" ? "danger" : notification.severity === "warning" ? "warning" : "info";
      addNotification(
        "allNotifications",
        notification.title || notification.message || "Notification",
        type,
        notification.severity || "system",
      );
    });
  } catch (error) {
    console.warn("Unable to load notification history", error);
  }
}

let systemOnline = false;

function updateSystemStatus(online) {
  const badge = document.getElementById("systemStatus");

  if (!badge) return;

  if (online) {
    badge.innerHTML = "🟢 System Online";
    badge.className = "status online";
  } else {
    badge.innerHTML = "🔴 System Offline";
    badge.className = "status offline";
  }
}

function handleOffline() {
  updateSystemStatus(false);

  if (!offlineNotificationShown) {
    addNotification(
      "allNotifications",
      "🔴 ESP32 Disconnected",
      "danger",
      "Dashboard switched to Offline Mode",
    );
    addSystemAlert(
      "ESP32 Disconnected",
      "All Racks",
      "ESP32",
      "Critical",
      "Connection to ESP32 has been lost.",
    );
    offlineNotificationShown = true;
  }

  // Immediately set all sensor readings to 0 for both racks
  document.getElementById("r1Temperature").innerHTML = "0 °C";
  document.getElementById("r1Humidity").innerHTML = "0 %";
  document.getElementById("r1Soil").innerHTML = "0 %";
  document.getElementById("r1Air").innerHTML = "0 %";
  document.getElementById("r1Pump").innerHTML = "OFF";
  document.getElementById("r1Sprinkler").innerHTML = "OFF";
  document.getElementById("r1Fan").innerHTML = "OFF";
  document.getElementById("r1Grow").innerHTML = "OFF";

  document.getElementById("r2Temperature").innerHTML = "0 °C";
  document.getElementById("r2Humidity").innerHTML = "0 %";
  document.getElementById("r2Soil").innerHTML = "0 %";
  document.getElementById("r2Air").innerHTML = "0 %";
  document.getElementById("r2Pump").innerHTML = "OFF";
  document.getElementById("r2Sprinkler").innerHTML = "OFF";
  document.getElementById("r2Fan").innerHTML = "OFF";
  document.getElementById("r2Grow").innerHTML = "OFF";

  // Common Water Tank 0% in both cards
  const cw1 = document.getElementById("commonWater");
  if (cw1) cw1.innerHTML = "0 %";
  const cw2 = document.getElementById("commonWaterLevel");
  if (cw2) cw2.innerHTML = "0 %";

  // Set Plant Health to 0% and status to Offline
  document.getElementById("r1Health").innerHTML = "0 %";
  document.getElementById("r1HealthStatus").innerHTML = "Offline";
  document.getElementById("r2Health").innerHTML = "0 %";
  document.getElementById("r2HealthStatus").innerHTML = "Offline";

  if (typeof window.updateDigitalTwin === "function") {
    window.updateDigitalTwin("r1", { Temperature: 0, Humidity: 0, Soil_Moisture: 0, Air: 0, Light_Output: false });
    window.updateDigitalTwin("r2", { Temperature: 0, Humidity: 0, Soil_Moisture: 0, Air: 0, Light_Output: false });
  }

  // Add one final graph point with value 0 to every graph, then freeze the graphs.
  // Do not continue adding zeros every second.
  if (!offlinePointAdded) {
    offlinePointAdded = true;

    const time = new Date().toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });

    labels.push(time);
    if (labels.length > MAX_POINTS) labels.shift();

    pushValue(r1Temp, 0);
    pushValue(r1Hum, 0);
    pushValue(r1Soil, 0);
    pushValue(r1Air, 0);

    pushValue(r2Temp, 0);
    pushValue(r2Hum, 0);
    pushValue(r2Soil, 0);
    pushValue(r2Air, 0);

    updateChart(rack1TempChart, r1Temp);
    updateChart(rack1HumChart, r1Hum);
    updateChart(rack1SoilChart, r1Soil);
    updateChart(rack1AirChart, r1Air);

    updateChart(rack2TempChart, r2Temp);
    updateChart(rack2HumChart, r2Hum);
    updateChart(rack2SoilChart, r2Soil);
    updateChart(rack2AirChart, r2Air);
  }
}

async function loadData() {
  const apiBase = (typeof window.API_BASE_URL === "string" ? window.API_BASE_URL : "").replace(/\/+$/, "");
  try {
    const response = await fetch(apiBase + "/data?t=" + Date.now());
    if (!response.ok) throw new Error("Cannot load data");

    const json = await response.json();
    console.log("[/data] JSON received", {
      zone1Soil: json.Zone1 && json.Zone1.Soil_Moisture,
      zone2Soil: json.Zone2 && json.Zone2.Soil_Moisture,
      commonWater: json.Common_Water_Level,
      status: json.status,
    });

    if (json.status === "offline") {
      handleOffline();
      return;
    }

    // System is ONLINE
    updateSystemStatus(true);

    if (offlineNotificationShown) {
      addNotification(
        "allNotifications",
        "🟢 ESP32 Reconnected",
        "info",
        "Live monitoring resumed",
      );
      addSystemAlert(
        "ESP32 Reconnected",
        "All Racks",
        "ESP32",
        "Info",
        "Live communication restored.",
      );
      offlineNotificationShown = false;
    }

    offlinePointAdded = false;

    // Map the live backend tank percentage to both racks. Do not replace a
    // received value with a fallback zero during the dashboard refresh.
    const commonWaterLevel = Number(json.Common_Water_Level);
    if (Number.isFinite(commonWaterLevel)) {
      json.Zone1.Water_Level = commonWaterLevel;
      json.Zone2.Water_Level = commonWaterLevel;
    }

    const zone1 = normalizeZoneData(json.Zone1, "Zone1", json.Relay);
    const zone2 = normalizeZoneData(json.Zone2, "Zone2", json.Relay);

    // Update Dashboard UI
    updateRack1(zone1);
    updateRack2(zone2);

    updateHealth("r1", zone1);
    updateHealth("r2", zone2);

    if (typeof window.updateDigitalTwin === "function") {
      window.updateDigitalTwin("r1", zone1);
      window.updateDigitalTwin("r2", zone2);
    }

    detectSystemFaults("r1", zone1);
    detectSystemFaults("r2", zone2);

    automation("r1", zone1);
    automation("r2", zone2);

    if (json.Timestamp) {
      document.getElementById("lastUpdate").innerHTML = json.Timestamp;
    }

    // Update Graphs
    const currentTime = new Date().toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });

    if (currentTime !== lastGraphTime) {
      lastGraphTime = currentTime;

      labels.push(currentTime);
      if (labels.length > MAX_POINTS) labels.shift();

      updateRack1Charts(zone1);
      updateRack2Charts(zone2);
    }
  } catch (e) {
    console.log(e);
    handleOffline();
  }
}

seedInitialNotifications();
loadAutomationHistory();
loadNotificationHistory();
loadData();
refreshInterval = setInterval(loadData, 1000);

function downloadEventLogPDF() {
  const { jsPDF } = window.jspdf;
  const doc = new jsPDF({ unit: "pt", format: "a4" });
  const headers = [["Date", "Time", "Rack", "Device", "Action", "Status"]];
  const rows = [];

  document.querySelectorAll("#automationEvents tr").forEach((row) => {
    const cells = Array.from(row.querySelectorAll("td")).map((cell) =>
      cell.textContent.trim(),
    );
    if (cells.length) rows.push(cells);
  });

  doc.setFontSize(18);
  doc.text("Automation Event Log", 40, 40);
  doc.setFontSize(11);
  doc.setTextColor(80);
  doc.text("Generated: " + new Date().toLocaleString(), 40, 60);

  doc.autoTable({
    startY: 80,
    head: headers,
    body: rows,
    headStyles: { fillColor: [16, 37, 63], textColor: 255 },
    styles: { fontSize: 10, cellPadding: 6 },
    theme: "grid",
  });

  doc.save("automation-event-log.pdf");
}

document.addEventListener("DOMContentLoaded", () => {
  const button = document.getElementById("downloadLogBtn");
  if (button) {
    button.addEventListener("click", downloadEventLogPDF);
  }
});
