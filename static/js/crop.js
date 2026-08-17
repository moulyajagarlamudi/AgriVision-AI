// ============================================================
// AI Crop Database -- 15 Indoor Crop Types
// Each crop contains base conditions + per-stage absolute values
// Sources: FAO, IRRI, ICAR, extension agronomic guidelines
// ============================================================
const aiCropDatabase = {

  // Paddy (Rice) - Tropical staple; warm, very moist throughout
  "Paddy": {
    name: "Paddy",
    icon: "🌾",
    Temperature: 28,
    Humidity: 82,
    Soil_Moisture: 88,
    Light: "High",
    Air: "Good",
    stages: {
      Seedling:   { Temperature: 26, Humidity: 85, Soil_Moisture: 75, Light: "Low" },
      Vegetative: { Temperature: 28, Humidity: 82, Soil_Moisture: 90, Light: "High" },
      Flowering:  { Temperature: 29, Humidity: 78, Soil_Moisture: 92, Light: "High" },
      Fruiting:   { Temperature: 28, Humidity: 75, Soil_Moisture: 90, Light: "High" },
      Harvest:    { Temperature: 27, Humidity: 65, Soil_Moisture: 68, Light: "Medium" }
    }
  },

  // Wheat - Cool-season cereal; moderate moisture, needs high light when flowering
  "Wheat": {
    name: "Wheat",
    icon: "🌾",
    Temperature: 18,
    Humidity: 60,
    Soil_Moisture: 55,
    Light: "Medium",
    Air: "Good",
    stages: {
      Seedling:   { Temperature: 15, Humidity: 70, Soil_Moisture: 48, Light: "Low" },
      Vegetative: { Temperature: 18, Humidity: 60, Soil_Moisture: 55, Light: "Medium" },
      Flowering:  { Temperature: 20, Humidity: 55, Soil_Moisture: 52, Light: "High" },
      Fruiting:   { Temperature: 22, Humidity: 50, Soil_Moisture: 48, Light: "High" },
      Harvest:    { Temperature: 20, Humidity: 45, Soil_Moisture: 35, Light: "Medium" }
    }
  },

  // Tomato - Warm-season fruit; high light and warmth during fruiting
  "Tomato": {
    name: "Tomato",
    icon: "🍅",
    Temperature: 24,
    Humidity: 65,
    Soil_Moisture: 65,
    Light: "High",
    Air: "Good",
    stages: {
      Seedling:   { Temperature: 22, Humidity: 78, Soil_Moisture: 55, Light: "Low" },
      Vegetative: { Temperature: 24, Humidity: 65, Soil_Moisture: 65, Light: "High" },
      Flowering:  { Temperature: 23, Humidity: 60, Soil_Moisture: 62, Light: "High" },
      Fruiting:   { Temperature: 26, Humidity: 58, Soil_Moisture: 72, Light: "High" },
      Harvest:    { Temperature: 24, Humidity: 52, Soil_Moisture: 58, Light: "Medium" }
    }
  },

  // Potato - Cool-season tuber; tuber set favors cooler temps
  "Potato": {
    name: "Potato",
    icon: "🥔",
    Temperature: 18,
    Humidity: 72,
    Soil_Moisture: 65,
    Light: "Medium",
    Air: "Good",
    stages: {
      Seedling:   { Temperature: 16, Humidity: 80, Soil_Moisture: 55, Light: "Low" },
      Vegetative: { Temperature: 18, Humidity: 72, Soil_Moisture: 65, Light: "Medium" },
      Flowering:  { Temperature: 20, Humidity: 68, Soil_Moisture: 70, Light: "Medium" },
      Fruiting:   { Temperature: 17, Humidity: 65, Soil_Moisture: 75, Light: "Medium" },
      Harvest:    { Temperature: 15, Humidity: 55, Soil_Moisture: 45, Light: "Low" }
    }
  },

  // Maize - Warm-season; low humidity during pollination is critical
  "Maize": {
    name: "Maize",
    icon: "🌽",
    Temperature: 27,
    Humidity: 70,
    Soil_Moisture: 72,
    Light: "High",
    Air: "Good",
    stages: {
      Seedling:   { Temperature: 24, Humidity: 78, Soil_Moisture: 62, Light: "Low" },
      Vegetative: { Temperature: 27, Humidity: 70, Soil_Moisture: 72, Light: "High" },
      Flowering:  { Temperature: 29, Humidity: 62, Soil_Moisture: 75, Light: "High" },
      Fruiting:   { Temperature: 28, Humidity: 65, Soil_Moisture: 78, Light: "High" },
      Harvest:    { Temperature: 26, Humidity: 55, Soil_Moisture: 55, Light: "Medium" }
    }
  },

  // Chilli - Hot-season fruit; highest temps during fruiting, dry harvest
  "Chilli": {
    name: "Chilli",
    icon: "🌶",
    Temperature: 27,
    Humidity: 72,
    Soil_Moisture: 68,
    Light: "High",
    Air: "Good",
    stages: {
      Seedling:   { Temperature: 26, Humidity: 80, Soil_Moisture: 55, Light: "Low" },
      Vegetative: { Temperature: 27, Humidity: 72, Soil_Moisture: 68, Light: "High" },
      Flowering:  { Temperature: 28, Humidity: 65, Soil_Moisture: 62, Light: "High" },
      Fruiting:   { Temperature: 30, Humidity: 60, Soil_Moisture: 72, Light: "High" },
      Harvest:    { Temperature: 27, Humidity: 55, Soil_Moisture: 58, Light: "Medium" }
    }
  },

  // Onion - Moderate-season bulb; very dry conditions at harvest
  "Onion": {
    name: "Onion",
    icon: "🧅",
    Temperature: 20,
    Humidity: 65,
    Soil_Moisture: 58,
    Light: "Medium",
    Air: "Good",
    stages: {
      Seedling:   { Temperature: 18, Humidity: 72, Soil_Moisture: 50, Light: "Low" },
      Vegetative: { Temperature: 20, Humidity: 65, Soil_Moisture: 58, Light: "Medium" },
      Flowering:  { Temperature: 22, Humidity: 60, Soil_Moisture: 52, Light: "Medium" },
      Fruiting:   { Temperature: 20, Humidity: 55, Soil_Moisture: 55, Light: "Medium" },
      Harvest:    { Temperature: 18, Humidity: 45, Soil_Moisture: 40, Light: "Low" }
    }
  },

  // Brinjal (Eggplant) - Tropical; high heat tolerance, strong light needed
  "Brinjal": {
    name: "Brinjal",
    icon: "🍆",
    Temperature: 26,
    Humidity: 70,
    Soil_Moisture: 70,
    Light: "High",
    Air: "Good",
    stages: {
      Seedling:   { Temperature: 24, Humidity: 80, Soil_Moisture: 58, Light: "Low" },
      Vegetative: { Temperature: 26, Humidity: 70, Soil_Moisture: 70, Light: "High" },
      Flowering:  { Temperature: 27, Humidity: 65, Soil_Moisture: 65, Light: "High" },
      Fruiting:   { Temperature: 28, Humidity: 62, Soil_Moisture: 75, Light: "High" },
      Harvest:    { Temperature: 26, Humidity: 58, Soil_Moisture: 62, Light: "Medium" }
    }
  },

  // Cabbage - Cool-season brassica; heading prefers cool and moist
  "Cabbage": {
    name: "Cabbage",
    icon: "🥬",
    Temperature: 17,
    Humidity: 75,
    Soil_Moisture: 68,
    Light: "Medium",
    Air: "Good",
    stages: {
      Seedling:   { Temperature: 15, Humidity: 80, Soil_Moisture: 58, Light: "Low" },
      Vegetative: { Temperature: 17, Humidity: 75, Soil_Moisture: 68, Light: "Medium" },
      Flowering:  { Temperature: 18, Humidity: 70, Soil_Moisture: 65, Light: "Medium" },
      Fruiting:   { Temperature: 16, Humidity: 68, Soil_Moisture: 72, Light: "Medium" },
      Harvest:    { Temperature: 14, Humidity: 60, Soil_Moisture: 55, Light: "Low" }
    }
  },

  // Spinach - Cool-season leafy; bolts in heat, harvest early
  "Spinach": {
    name: "Spinach",
    icon: "🍃",
    Temperature: 15,
    Humidity: 75,
    Soil_Moisture: 70,
    Light: "Medium",
    Air: "Good",
    stages: {
      Seedling:   { Temperature: 13, Humidity: 80, Soil_Moisture: 62, Light: "Low" },
      Vegetative: { Temperature: 15, Humidity: 75, Soil_Moisture: 70, Light: "Medium" },
      Flowering:  { Temperature: 18, Humidity: 68, Soil_Moisture: 65, Light: "Medium" },
      Fruiting:   { Temperature: 16, Humidity: 70, Soil_Moisture: 65, Light: "Medium" },
      Harvest:    { Temperature: 12, Humidity: 65, Soil_Moisture: 55, Light: "Low" }
    }
  },

  // Carrot - Root crop; cool temps promote root development and sweetness
  "Carrot": {
    name: "Carrot",
    icon: "🥕",
    Temperature: 18,
    Humidity: 68,
    Soil_Moisture: 65,
    Light: "Medium",
    Air: "Good",
    stages: {
      Seedling:   { Temperature: 16, Humidity: 75, Soil_Moisture: 70, Light: "Low" },
      Vegetative: { Temperature: 18, Humidity: 68, Soil_Moisture: 65, Light: "Medium" },
      Flowering:  { Temperature: 20, Humidity: 62, Soil_Moisture: 58, Light: "Medium" },
      Fruiting:   { Temperature: 16, Humidity: 65, Soil_Moisture: 75, Light: "Medium" },
      Harvest:    { Temperature: 14, Humidity: 55, Soil_Moisture: 45, Light: "Low" }
    }
  },

  // Groundnut (Peanut) - Legume; pods develop underground during pegging stage
  "Groundnut": {
    name: "Groundnut",
    icon: "🥜",
    Temperature: 28,
    Humidity: 65,
    Soil_Moisture: 62,
    Light: "High",
    Air: "Good",
    stages: {
      Seedling:   { Temperature: 25, Humidity: 72, Soil_Moisture: 55, Light: "Low" },
      Vegetative: { Temperature: 28, Humidity: 65, Soil_Moisture: 62, Light: "High" },
      Flowering:  { Temperature: 30, Humidity: 62, Soil_Moisture: 58, Light: "High" },
      Fruiting:   { Temperature: 29, Humidity: 60, Soil_Moisture: 72, Light: "High" },
      Harvest:    { Temperature: 27, Humidity: 52, Soil_Moisture: 48, Light: "Medium" }
    }
  },

  // Fenugreek - Cool-season legume-herb; drought-tolerant, low water needs
  "Fenugreek": {
    name: "Fenugreek",
    icon: "🌿",
    Temperature: 22,
    Humidity: 60,
    Soil_Moisture: 55,
    Light: "Medium",
    Air: "Good",
    stages: {
      Seedling:   { Temperature: 20, Humidity: 68, Soil_Moisture: 48, Light: "Low" },
      Vegetative: { Temperature: 22, Humidity: 60, Soil_Moisture: 55, Light: "Medium" },
      Flowering:  { Temperature: 24, Humidity: 55, Soil_Moisture: 48, Light: "Medium" },
      Fruiting:   { Temperature: 24, Humidity: 52, Soil_Moisture: 58, Light: "Medium" },
      Harvest:    { Temperature: 22, Humidity: 45, Soil_Moisture: 42, Light: "Low" }
    }
  },

  // Fennel - Cool-season herb; very low water, sensitive to waterlogging
  "Fennel": {
    name: "Fennel",
    icon: "🌱",
    Temperature: 19,
    Humidity: 55,
    Soil_Moisture: 50,
    Light: "Medium",
    Air: "Good",
    stages: {
      Seedling:   { Temperature: 17, Humidity: 62, Soil_Moisture: 45, Light: "Low" },
      Vegetative: { Temperature: 19, Humidity: 55, Soil_Moisture: 50, Light: "Medium" },
      Flowering:  { Temperature: 21, Humidity: 52, Soil_Moisture: 45, Light: "Medium" },
      Fruiting:   { Temperature: 20, Humidity: 50, Soil_Moisture: 55, Light: "Medium" },
      Harvest:    { Temperature: 18, Humidity: 45, Soil_Moisture: 38, Light: "Low" }
    }
  },

  // Coriander - Cool-season herb; bolts quickly in heat, manage carefully
  "Coriander": {
    name: "Coriander",
    icon: "🍀",
    Temperature: 21,
    Humidity: 65,
    Soil_Moisture: 55,
    Light: "Medium",
    Air: "Good",
    stages: {
      Seedling:   { Temperature: 19, Humidity: 72, Soil_Moisture: 50, Light: "Low" },
      Vegetative: { Temperature: 21, Humidity: 65, Soil_Moisture: 55, Light: "Medium" },
      Flowering:  { Temperature: 24, Humidity: 58, Soil_Moisture: 48, Light: "Medium" },
      Fruiting:   { Temperature: 23, Humidity: 52, Soil_Moisture: 45, Light: "Medium" },
      Harvest:    { Temperature: 21, Humidity: 48, Soil_Moisture: 40, Light: "Low" }
    }
  },

  // Amaranthus - Warm-season leafy grain; high light, heat-tolerant, moderate-high moisture
  // Sources: Burpee, NDA South Africa, IPP Farm agronomic guidelines
  "Amaranthus": {
    name: "Amaranthus",
    icon: "🌿",
    Temperature: 26,
    Humidity: 65,
    Soil_Moisture: 72,
    Light: "High",
    Air: "Good",
    stages: {
      // Germination/Seedling: warm soil (20-25°C), consistently moist, gentle light
      Seedling:   { Temperature: 22, Humidity: 75, Soil_Moisture: 65, Light: "Low" },
      // Vegetative: warm days (22-28°C), high light, moderate watering between drinks
      Vegetative: { Temperature: 25, Humidity: 68, Soil_Moisture: 72, Light: "High" },
      // Flowering: photoperiod-sensitive; keep warm, slightly drier to encourage flowering
      Flowering:  { Temperature: 27, Humidity: 62, Soil_Moisture: 68, Light: "High" },
      // Fruiting (grain/seed fill): peak warmth, maintain moisture for seed development
      Fruiting:   { Temperature: 28, Humidity: 60, Soil_Moisture: 75, Light: "High" },
      // Harvest: reduce irrigation to tighten grain; slight cooling acceptable
      Harvest:    { Temperature: 25, Humidity: 55, Soil_Moisture: 58, Light: "Medium" }
    }
  }
};

// ============================================================
// Store current live telemetry for each rack
// ============================================================
window.latestTwinTelemetry = {
  r1: { Temperature: 0, Humidity: 0, Soil_Moisture: 0, Air: 0, Light_Output: false },
  r2: { Temperature: 0, Humidity: 0, Soil_Moisture: 0, Air: 0, Light_Output: false }
};

// ============================================================
// updateTwinRack -- reads per-crop, per-stage target values
// ============================================================
function updateTwinRack(rackPrefix) {
  const cropSelect  = document.getElementById(rackPrefix + "CropSelect");
  const stageSelect = document.getElementById(rackPrefix + "StageSelect");
  if (!cropSelect) return;

  const cropName  = cropSelect.value;
  const stageName = stageSelect ? stageSelect.value : "Vegetative";
  const crop      = aiCropDatabase[cropName] || aiCropDatabase["Paddy"];

  // Use per-crop stage absolute values if available, else fall back to base
  const stageData = (crop.stages && crop.stages[stageName]) ? crop.stages[stageName] : {
    Temperature:   crop.Temperature,
    Humidity:      crop.Humidity,
    Soil_Moisture: crop.Soil_Moisture,
    Light:         crop.Light
  };

  const telemetry = window.latestTwinTelemetry[rackPrefix] || {
    Temperature: 0, Humidity: 0, Soil_Moisture: 0, Air: 0, Light_Output: false
  };

  // Update crop header visuals
  const cropIcon = document.getElementById(rackPrefix + "CropIcon");
  if (cropIcon) cropIcon.textContent = crop.icon;

  const cropNameElem = document.getElementById(rackPrefix + "CropName");
  if (cropNameElem) cropNameElem.textContent = crop.name;

  const botanicalElem = document.getElementById(rackPrefix + "CropBotanical");
  if (botanicalElem) botanicalElem.textContent = stageName + " Stage";

  // Resolve live readings
  const liveTemp = Number(telemetry.Temperature  || 0);
  const liveHum  = Number(telemetry.Humidity     || 0);
  const liveSoil = Number(telemetry.Soil_Moisture || 0);

  let liveAirPercent = Number(telemetry.Air || 0);
  if (liveAirPercent > 100) {
    liveAirPercent = Math.max(0, Math.min(100, 100 - liveAirPercent / 15));
  }

  // Target values from per-crop-per-stage data
  const targetTemp  = stageData.Temperature;
  const targetHum   = stageData.Humidity;
  const targetSoil  = stageData.Soil_Moisture;
  const targetLight = stageData.Light;

  // Update live + target labels
  const liveTempElem = document.getElementById(rackPrefix + "LiveTemp");
  if (liveTempElem) liveTempElem.textContent = liveTemp.toFixed(1) + " °C";

  const targetTempElem = document.getElementById(rackPrefix + "TargetTemp");
  if (targetTempElem) targetTempElem.textContent = "Target: " + targetTemp + "°C";

  const liveHumElem = document.getElementById(rackPrefix + "LiveHum");
  if (liveHumElem) liveHumElem.textContent = liveHum.toFixed(1) + " %";

  const targetHumElem = document.getElementById(rackPrefix + "TargetHum");
  if (targetHumElem) targetHumElem.textContent = "Target: " + targetHum + "%";

  const liveSoilElem = document.getElementById(rackPrefix + "LiveSoil");
  if (liveSoilElem) liveSoilElem.textContent = liveSoil.toFixed(1) + " %";

  const targetSoilElem = document.getElementById(rackPrefix + "TargetSoil");
  if (targetSoilElem) targetSoilElem.textContent = "Target: " + targetSoil + "%";

  const liveLightElem = document.getElementById(rackPrefix + "LiveLight");
  if (liveLightElem) liveLightElem.textContent = telemetry.Light_Output ? "ON" : "OFF";

  const targetLightElem = document.getElementById(rackPrefix + "TargetLight");
  if (targetLightElem) targetLightElem.textContent = "Target: " + targetLight;

  const liveAirElem = document.getElementById(rackPrefix + "LiveAir");
  if (liveAirElem) liveAirElem.textContent = liveAirPercent.toFixed(1) + " %";

  const targetAirElem = document.getElementById(rackPrefix + "TargetAir");
  if (targetAirElem) targetAirElem.textContent = "Target: Good";

  // Comparisons & Pill Badges
  let healthScore = 100;
  let recs = [];

  // Temperature
  const tempDiff = liveTemp - targetTemp;
  const tempPill = document.getElementById(rackPrefix + "TempPill");
  if (tempPill) {
    if (Math.abs(tempDiff) <= 2) {
      tempPill.className = "twinPill optimal";
      tempPill.textContent = "🟢 Optimal";
    } else if (tempDiff > 2) {
      tempPill.className = "twinPill warning";
      tempPill.textContent = "\uD83D\uDFE1 +" + tempDiff.toFixed(1) + "°C High";
      healthScore -= Math.min(25, Math.abs(tempDiff) * 4);
      recs.push("Temperature is " + tempDiff.toFixed(1) + "°C above optimal (" + targetTemp + "°C). Enable cooling fan.");
    } else {
      tempPill.className = "twinPill warning";
      tempPill.textContent = "\uD83D\uDFE1 " + tempDiff.toFixed(1) + "°C Low";
      healthScore -= Math.min(25, Math.abs(tempDiff) * 4);
      recs.push("Temperature is " + Math.abs(tempDiff).toFixed(1) + "°C below target (" + targetTemp + "°C). Adjust indoor heating.");
    }
  }

  // Humidity
  const humDiff = liveHum - targetHum;
  const humPill = document.getElementById(rackPrefix + "HumPill");
  if (humPill) {
    if (Math.abs(humDiff) <= 5) {
      humPill.className = "twinPill optimal";
      humPill.textContent = "🟢 Optimal";
    } else if (humDiff < -5) {
      humPill.className = "twinPill danger";
      humPill.textContent = "🟠 Needs Humidification";
      healthScore -= Math.min(30, Math.abs(humDiff) * 1.5);
      recs.push("Humidity is " + Math.abs(humDiff).toFixed(1) + "% below ideal (" + targetHum + "%). Increase humidification.");
    } else {
      humPill.className = "twinPill warning";
      humPill.textContent = "🟡 High Humidity";
      healthScore -= Math.min(20, humDiff * 1.2);
      recs.push("Humidity exceeds target by " + humDiff.toFixed(1) + "%. Improve ventilation.");
    }
  }

  // Soil Moisture
  const soilDiff = liveSoil - targetSoil;
  const soilPill = document.getElementById(rackPrefix + "SoilPill");
  if (soilPill) {
    if (Math.abs(soilDiff) <= 10) {
      soilPill.className = "twinPill optimal";
      soilPill.textContent = "🟢 Optimal";
    } else if (soilDiff < -10) {
      soilPill.className = "twinPill danger";
      soilPill.textContent = "🔴 Irrigation Required";
      healthScore -= Math.min(40, Math.abs(soilDiff) * 1.8);
      recs.push("Soil moisture low (" + liveSoil.toFixed(1) + "% vs " + targetSoil + "% target). Increase irrigation.");
    } else {
      soilPill.className = "twinPill warning";
      soilPill.textContent = "🟡 Overwatered";
      healthScore -= Math.min(20, soilDiff * 1.0);
      recs.push("Soil moisture is above target. Pause watering.");
    }
  }

  // Light
  const lightPill = document.getElementById(rackPrefix + "LightPill");
  if (lightPill) {
    if (telemetry.Light_Output) {
      lightPill.className = "twinPill optimal";
      lightPill.textContent = "🟢 Optimal (UV ON)";
    } else {
      lightPill.className = "twinPill info";
      lightPill.textContent = "ℹ Night Mode (UV OFF)";
    }
  }

  // Air Quality
  const airPill = document.getElementById(rackPrefix + "AirPill");
  if (airPill) {
    if (liveAirPercent >= 70) {
      airPill.className = "twinPill optimal";
      airPill.textContent = "🟢 Good";
    } else if (liveAirPercent >= 45) {
      airPill.className = "twinPill warning";
      airPill.textContent = "🟡 Moderate";
      healthScore -= 10;
      recs.push("Air quality is moderate. Increase airflow.");
    } else {
      airPill.className = "twinPill danger";
      airPill.textContent = "🔴 Poor Air Quality";
      healthScore -= 20;
      recs.push("Air quality is poor. Air purification recommended.");
    }
  }

  healthScore = Math.max(0, Math.min(100, Math.round(healthScore)));

  // Health Circle & Ring
  const healthNum = document.getElementById(rackPrefix + "HealthScoreNum");
  if (healthNum) healthNum.textContent = healthScore + "%";

  const ring = document.getElementById(rackPrefix + "ProgressRing");
  if (ring) {
    const circumference = 251.2;
    const offset = circumference - (healthScore / 100) * circumference;
    ring.style.strokeDashoffset = offset;
    if      (healthScore >= 90) ring.style.stroke = "#22c55e";
    else if (healthScore >= 75) ring.style.stroke = "#eab308";
    else if (healthScore >= 55) ring.style.stroke = "#f97316";
    else                        ring.style.stroke = "#ef4444";
  }

  // AI Status Badge
  const badge = document.getElementById(rackPrefix + "AiStatusBadge");
  if (badge) {
    if      (healthScore >= 90) { badge.className = "twinStatusBadge perfect";    badge.textContent = "🟢 Perfect Conditions"; }
    else if (healthScore >= 75) { badge.className = "twinStatusBadge optimizing"; badge.textContent = "🟡 Optimizing"; }
    else if (healthScore >= 55) { badge.className = "twinStatusBadge monitoring"; badge.textContent = "🟠 Monitoring"; }
    else                        { badge.className = "twinStatusBadge critical";   badge.textContent = "🔴 Critical"; }
  }

  // AI Recommendation Text
  const recTextElem = document.getElementById(rackPrefix + "AiRecText");
  if (recTextElem) {
    recTextElem.textContent = recs.length === 0
      ? "Optimal growing conditions detected for " + crop.name + " (" + stageName + " stage). All parameters align with target requirements."
      : recs.join(" ");
  }
}

// ============================================================
// Global hook to update Digital Twin from telemetry
// ============================================================
window.updateDigitalTwin = function(rackId, zoneData) {
  window.latestTwinTelemetry[rackId] = zoneData;
  updateTwinRack(rackId);
};

async function persistCropSelection(rackPrefix) {
  const cropSelect  = document.getElementById(rackPrefix + "CropSelect");
  const stageSelect = document.getElementById(rackPrefix + "StageSelect");
  if (!cropSelect) return;
  const zone = rackPrefix === "r1" ? "Zone1" : "Zone2";
  const apiBase = (typeof window.API_BASE_URL === "string" ? window.API_BASE_URL : "").replace(/\/+$/, "");
  try {
    await fetch(apiBase + "/api/crops/" + zone, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        crop: cropSelect.value,
        stage: stageSelect ? stageSelect.value : "Vegetative"
      })
    });
  } catch (error) {
    // No UI change or interruption if the optional controller API is unavailable.
    console.warn("Unable to save crop selection for automation", error);
  }
}

async function restoreCropSelections() {
  const apiBase = (typeof window.API_BASE_URL === "string" ? window.API_BASE_URL : "").replace(/\/+$/, "");
  try {
    const response = await fetch(apiBase + "/api/crops");
    if (!response.ok) return;
    const selected = await response.json();
    [
      ["r1", selected.Zone1, selected.Zone1_stage],
      ["r2", selected.Zone2, selected.Zone2_stage]
    ].forEach(([rackPrefix, crop, stage]) => {
      const cropSelect  = document.getElementById(rackPrefix + "CropSelect");
      const stageSelect = document.getElementById(rackPrefix + "StageSelect");
      if (cropSelect && crop && aiCropDatabase[crop]) {
        cropSelect.value = crop;
      }
      if (stageSelect && stage) {
        stageSelect.value = stage;
      }
      updateTwinRack(rackPrefix);
    });
  } catch (error) {
    console.warn("Unable to restore crop selections for automation", error);
  }
}

// ============================================================
// Init -- wire up dropdowns on page load
// ============================================================
document.addEventListener("DOMContentLoaded", () => {
  ["r1", "r2"].forEach(rackPrefix => {
    const cropSel  = document.getElementById(rackPrefix + "CropSelect");
    const stageSel = document.getElementById(rackPrefix + "StageSelect");
    if (cropSel)  cropSel.addEventListener("change",  () => {
      updateTwinRack(rackPrefix);
      persistCropSelection(rackPrefix);
    });
    if (stageSel) stageSel.addEventListener("change", () => {
      updateTwinRack(rackPrefix);
      persistCropSelection(rackPrefix);
    });
    updateTwinRack(rackPrefix);
  });
  restoreCropSelections();
});
