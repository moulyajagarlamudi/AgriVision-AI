"""Crop-aware actuator control, isolated from dashboard and serial transport."""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict


# Crop-level targets used by the controller.
# Base (Vegetative) values — stage-specific values are in getCropConfig() in relay_controller.ino.
CROP_CONFIGURATIONS: Dict[str, Dict[str, Any]] = {
    "Tomato":    {"temperature": 24, "humidity": 65, "soil_moisture": 65, "light": "High"},
    "Paddy":     {"temperature": 28, "humidity": 82, "soil_moisture": 90, "light": "High"},
    "Wheat":     {"temperature": 18, "humidity": 60, "soil_moisture": 55, "light": "Medium"},
    "Potato":    {"temperature": 18, "humidity": 72, "soil_moisture": 65, "light": "Medium"},
    "Maize":     {"temperature": 27, "humidity": 70, "soil_moisture": 72, "light": "High"},
    "Chilli":    {"temperature": 27, "humidity": 72, "soil_moisture": 68, "light": "High"},
    "Onion":     {"temperature": 20, "humidity": 65, "soil_moisture": 58, "light": "Medium"},
    "Brinjal":   {"temperature": 26, "humidity": 70, "soil_moisture": 70, "light": "High"},
    "Cabbage":   {"temperature": 17, "humidity": 75, "soil_moisture": 68, "light": "Medium"},
    "Spinach":   {"temperature": 15, "humidity": 75, "soil_moisture": 70, "light": "Medium"},
    "Carrot":    {"temperature": 18, "humidity": 68, "soil_moisture": 65, "light": "Medium"},
    "Groundnut": {"temperature": 28, "humidity": 65, "soil_moisture": 62, "light": "High"},
    "Fenugreek": {"temperature": 22, "humidity": 60, "soil_moisture": 55, "light": "Medium"},
    "Fennel":    {"temperature": 19, "humidity": 55, "soil_moisture": 50, "light": "Medium"},
    "Coriander": {"temperature": 21, "humidity": 65, "soil_moisture": 55, "light": "Medium"},
    "Amaranthus":{"temperature": 25, "humidity": 68, "soil_moisture": 72, "light": "High"},
}

VALID_STAGES = {"Seedling", "Vegetative", "Flowering", "Fruiting", "Harvest"}

DEFAULT_CROPS = {"Zone1": "Paddy",      "Zone2": "Tomato"}
DEFAULT_STAGES = {"Zone1": "Vegetative", "Zone2": "Vegetative"}

MINIMUM_WATER_LEVEL = 0.0


def load_selected_crops(path: str = "crop_selection.json") -> Dict[str, str]:
    """Load saved crop+stage selections. Returns dict with Zone1/Zone2 crop and stage."""
    selected = DEFAULT_CROPS.copy()
    stages   = DEFAULT_STAGES.copy()
    try:
        with open(path, encoding="utf-8") as file:
            stored = json.load(file)
        for zone in selected:
            if stored.get(zone) in CROP_CONFIGURATIONS:
                selected[zone] = stored[zone]
            stage_key = f"{zone}_stage"
            if stored.get(stage_key) in VALID_STAGES:
                stages[zone] = stored[stage_key]
    except (OSError, json.JSONDecodeError):
        pass

    # Merge stages into the returned dict
    result = {}
    for zone in selected:
        result[zone] = selected[zone]
        result[f"{zone}_stage"] = stages[zone]
    return result


def save_selected_crops(selected: Dict[str, str], path: str = "crop_selection.json") -> None:
    """Persist crop+stage selections atomically."""
    temp_path = f"{path}.tmp"
    with open(temp_path, "w", encoding="utf-8") as file:
        json.dump(selected, file, indent=2)
    os.replace(temp_path, path)


class RuleBasedDecisionEngine:
    """Replaceable policy boundary for a future XGBoost model adapter."""

    def decide(self, sensor_data: Dict[str, Any], crop_config: Dict[str, Any], now: datetime | None = None) -> Dict[str, int]:
        hour   = (now or datetime.now()).hour
        uv_on  = 6 <= hour <= 23

        temp        = sensor_data.get("Temperature", 0.0)
        target_temp = crop_config["temperature"]
        fan         = int(temp > target_temp)

        uv = int(uv_on and crop_config["light"] in {"Medium", "High"})

        print(
            f"[AI Decision] Temp={temp:.1f}°C (target≤{target_temp}°C) → Fan={'ON' if fan else 'OFF'} | "
            f"Hour={hour} Light={crop_config['light']} → UV={'ON' if uv else 'OFF'}"
        )

        return {
            "pump": int(sensor_data["Soil_Moisture"] < crop_config["soil_moisture"]
                        and sensor_data.get("Water_Level", 0.0) > MINIMUM_WATER_LEVEL),
            "fan":  fan,
            "uv":   uv,
        }


class CropAutomationController:
    """Dashboard-independent controller, ready for engine substitution."""

    def __init__(self, engine: RuleBasedDecisionEngine | None = None):
        self.engine = engine or RuleBasedDecisionEngine()

    def decide_for_zone(self, sensor_data: Dict[str, Any], crop_name: str) -> Dict[str, int]:
        crop_config = CROP_CONFIGURATIONS.get(
            crop_name,
            CROP_CONFIGURATIONS[DEFAULT_CROPS[sensor_data["Zone"]]]
        )
        return self.engine.decide(sensor_data, crop_config)
