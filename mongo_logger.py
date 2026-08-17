"""
AgriVision AI - MongoDB Atlas Integration Module
================================================
Database:    AgriVision
Collections:
  - farm_history        (per-second telemetry snapshots)
  - automation_events   (pump / fan / UV relay state changes)
  - notifications       (alerts, warnings, thresholds exceeded)
"""

import os
import sys
import time
import traceback
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

# Always load .env file at module import time
try:
    from dotenv import load_dotenv
    env_loaded = load_dotenv()
    if not env_loaded:
        load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
except ImportError:
    print("[MongoDB Setup Warning] 'python-dotenv' not installed. Please run: pip install python-dotenv")

try:
    import pymongo
    from pymongo import MongoClient, DESCENDING, ASCENDING
    PYMONGO_AVAILABLE = True
except ImportError:
    PYMONGO_AVAILABLE = False
    print("[MongoDB Setup Warning] 'pymongo' not installed. Please run: pip install pymongo dnspython")

DB_NAME = "AgriVision"
COLLECTION_NAME = "farm_history"
EVENTS_COLLECTION = "automation_events"
NOTIFICATIONS_COLLECTION = "notifications"

_client: Optional[Any] = None
_db: Optional[Any] = None
_collection: Optional[Any] = None
_events_collection: Optional[Any] = None
_notifications_collection: Optional[Any] = None
_last_insert_time: float = 0.0
_has_logged_uri_warning: bool = False


def check_mongodb_config() -> tuple[bool, str]:
    """Check if MONGODB_URI is set and valid (not empty and no placeholders)."""
    uri = os.getenv("MONGODB_URI", "").strip()
    if not uri:
        return False, "MONGODB_URI is not defined in .env or environment variables."
    if "<" in uri or ">" in uri or "YOUR_PASSWORD" in uri.upper() or "<PASSWORD>" in uri.upper() or "<DB_PASSWORD>" in uri.upper():
        return False, "MONGODB_URI contains password placeholder ('<db_password>'). Please replace '<db_password>' with your real MongoDB Atlas database password in your .env file."
    return True, uri


def _get_db():
    """Get connected MongoDB database, initialising all collections on first call."""
    global _client, _db, _collection, _events_collection, _notifications_collection, _has_logged_uri_warning

    if _db is not None:
        return _db

    if not PYMONGO_AVAILABLE:
        if not _has_logged_uri_warning:
            print("[MongoDB Atlas Error] PyMongo package is missing! Run: pip install pymongo dnspython")
            _has_logged_uri_warning = True
        return None

    is_valid, uri_or_reason = check_mongodb_config()
    if not is_valid:
        if not _has_logged_uri_warning:
            print("\n" + "=" * 80)
            print("[MongoDB Atlas Configuration Required]")
            print(f"   Reason: {uri_or_reason}")
            print("   Action required: Open your .env file in AgriVision_AI project root")
            print("   Set: MONGODB_URI=mongodb+srv://moulyajagarlamudi93_db_user:<YOUR_ACTUAL_PASSWORD>@cluster0.pvodhao.mongodb.net/?appName=Cluster0")
            print("=" * 80 + "\n")
            _has_logged_uri_warning = True
        return None

    try:
        _client = MongoClient(uri_or_reason, serverSelectionTimeoutMS=5000)
        _client.admin.command("ping")
        _db = _client[DB_NAME]

        # --- farm_history collection ---
        _collection = _db[COLLECTION_NAME]
        _collection.create_index([("timestamp", DESCENDING)])

        # --- automation_events collection ---
        _events_collection = _db[EVENTS_COLLECTION]
        _events_collection.create_index([("timestamp", DESCENDING)])

        # --- notifications collection ---
        _notifications_collection = _db[NOTIFICATIONS_COLLECTION]
        _notifications_collection.create_index([("timestamp", DESCENDING)])

        global _has_logged_connection_success
        if not getattr(sys.modules[__name__], "_has_logged_connection_success", False):
            print("\n" + "=" * 78)
            print("[MongoDB Atlas] SUCCESSFULLY CONNECTED!")
            print(f"   Database:    {DB_NAME}")
            print(f"   Collections: {COLLECTION_NAME}, {EVENTS_COLLECTION}, {NOTIFICATIONS_COLLECTION}")
            print("=" * 78 + "\n")
            setattr(sys.modules[__name__], "_has_logged_connection_success", True)
        return _db
    except Exception as e:
        err_msg = str(e)
        print("\n" + "=" * 78)
        print("[MongoDB Atlas Connection Failure]")
        print(f"   Error Type: {type(e).__name__}")
        print(f"   Details:    {err_msg}")
        if "authentication failed" in err_msg.lower() or "bad auth" in err_msg.lower():
            print("   -> Cause: Invalid username or password in MONGODB_URI.")
            print("   -> Fix: Verify your MongoDB Atlas database user password in .env")
        elif "serverselectiontimeouterror" in type(e).__name__.lower():
            print("   -> Cause: Cannot reach MongoDB Atlas cluster.")
            print("   -> Fix: Network Access -> Add IP 0.0.0.0/0 in Atlas Dashboard")
        print("=" * 78 + "\n")
        return None


def get_mongo_collection():
    """Return the farm_history collection or None."""
    global _collection
    db = _get_db()
    if db is None:
        return None
    return _collection


def _get_events_collection():
    global _events_collection
    db = _get_db()
    if db is None:
        return None
    return _events_collection


def _get_notifications_collection():
    global _notifications_collection
    db = _get_db()
    if db is None:
        return None
    return _notifications_collection


# =========================================================================
# TELEMETRY SNAPSHOT (farm_history)
# =========================================================================

def insert_telemetry_snapshot(dashboard_data: Dict[str, Any], selected_crops: Dict[str, str]) -> bool:
    """
    Inserts real ESP32 telemetry snapshot into MongoDB 'farm_history' every 1 second.
    """
    global _last_insert_time
    if not dashboard_data or dashboard_data.get("status") == "offline":
        return False

    now_ts = time.time()

    if now_ts - _last_insert_time < 1.0:
        return False

    coll = get_mongo_collection()
    if coll is None:
        return False

    try:
        z1 = dashboard_data.get("Zone1", {})
        z2 = dashboard_data.get("Zone2", {})
        rel = dashboard_data.get("Relay", {})
        now_dt = datetime.now()
        timestamp_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")
        date_str = now_dt.strftime("%Y-%m-%d")

        doc = {
            "timestamp": timestamp_str,
            "date": date_str,
            "rack1": {
                "temperature": float(z1.get("Temperature", 0.0)),
                "humidity": float(z1.get("Humidity", 0.0)),
                "soil": float(z1.get("Soil_Moisture", 0.0)),
                "air": int(z1.get("Air", 0)),
                "pump": int(rel.get("Zone1Pump", 0)),
                "fan": int(rel.get("Zone1Fan", 0)),
                "uv": int(rel.get("Zone1UV", 0)),
                "crop": selected_crops.get("Zone1", "Amaranthus"),
                "stage": selected_crops.get("Zone1_stage", "Vegetative")
            },
            "rack2": {
                "temperature": float(z2.get("Temperature", 0.0)),
                "humidity": float(z2.get("Humidity", 0.0)),
                "soil": float(z2.get("Soil_Moisture", 0.0)),
                "air": int(z2.get("Air", 0)),
                "pump": int(rel.get("Zone2Pump", 0)),
                "fan": int(rel.get("Zone2Fan", 0)),
                "uv": int(rel.get("Zone2UV", 0)),
                "crop": selected_crops.get("Zone2", "Tomato"),
                "stage": selected_crops.get("Zone2_stage", "Flowering")
            },
            "waterTank": float(dashboard_data.get("Common_Water_Level", 0.0))
        }

        result = coll.insert_one(doc)
        _last_insert_time = now_ts
        print(f"[MongoDB] Snapshot saved | {timestamp_str} | R1 Temp:{doc['rack1']['temperature']}C Soil:{doc['rack1']['soil']}% | R2 Temp:{doc['rack2']['temperature']}C | Tank:{doc['waterTank']}%")
        return True
    except Exception as e:
        print(f"\n[MongoDB Snapshot Insert Error] {type(e).__name__}: {e}")
        traceback.print_exc()
        return False


# =========================================================================
# AUTOMATION EVENTS (automation_events)
# =========================================================================

def insert_automation_event(zone: str, actuator: str, action: str,
                             reason: str, sensor_values: Dict[str, Any],
                             crop: str) -> bool:
    """
    Log a relay state change (pump ON, fan OFF, UV ON etc.) to automation_events collection.
    """
    coll = _get_events_collection()
    if coll is None:
        return False
    try:
        now_dt = datetime.now()
        doc = {
            "timestamp": now_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "date": now_dt.strftime("%Y-%m-%d"),
            "time": now_dt.strftime("%H:%M:%S"),
            "zone": zone,
            "rack": "Rack 1" if "1" in zone else "Rack 2",
            "actuator": actuator,   # "Pump" | "Fan" | "UV"
            "action": action,       # "ON" | "OFF"
            "reason": reason,
            "crop": crop,
            "sensor_values": sensor_values
        }
        coll.insert_one(doc)
        print(f"[Automation Event] {zone} {actuator} -> {action} | {reason}")
        return True
    except Exception as e:
        print(f"[Automation Event Insert Error] {e}")
        return False


def query_automation_events(from_date: Optional[str] = None,
                             to_date: Optional[str] = None,
                             zone: Optional[str] = None,
                             limit: int = 500) -> List[Dict[str, Any]]:
    """Query automation_events collection."""
    coll = _get_events_collection()
    if coll is None:
        return []
    try:
        query: Dict[str, Any] = {}
        if from_date and to_date:
            query["timestamp"] = {"$gte": from_date, "$lte": to_date}
        elif from_date:
            query["timestamp"] = {"$gte": from_date}
        elif to_date:
            query["timestamp"] = {"$lte": to_date}
        if zone and zone != "all":
            query["rack"] = zone
        cursor = coll.find(query, {"_id": 0}).sort("timestamp", DESCENDING).limit(limit)
        return list(cursor)
    except Exception as e:
        print(f"[Automation Events Query Error] {e}")
        return []


# =========================================================================
# NOTIFICATIONS (notifications)
# =========================================================================

NOTIFICATION_THRESHOLDS = {
    "temperature_high": 35.0,
    "temperature_low": 10.0,
    "humidity_low": 30.0,
    "soil_dry": 15.0,
    "water_tank_low": 20.0,
    "air_quality_poor": 85,   # % above this = poor
}

_last_notification_time: Dict[str, float] = {}
NOTIFICATION_COOLDOWN = 60.0  # seconds between same-type notifications


def insert_notification(zone: str, notif_type: str, title: str,
                         message: str, severity: str,
                         sensor_values: Dict[str, Any]) -> bool:
    """
    Insert a sensor threshold alert into the notifications collection.
    severity: "info" | "warning" | "critical"
    """
    global _last_notification_time
    cooldown_key = f"{zone}_{notif_type}"
    now_ts = time.time()
    if now_ts - _last_notification_time.get(cooldown_key, 0) < NOTIFICATION_COOLDOWN:
        return False

    coll = _get_notifications_collection()
    if coll is None:
        return False
    try:
        now_dt = datetime.now()
        doc = {
            "timestamp": now_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "date": now_dt.strftime("%Y-%m-%d"),
            "time": now_dt.strftime("%H:%M:%S"),
            "zone": zone,
            "rack": "Rack 1" if "1" in zone else "Rack 2",
            "type": notif_type,
            "title": title,
            "message": message,
            "severity": severity,
            "read": False,
            "sensor_values": sensor_values
        }
        coll.insert_one(doc)
        _last_notification_time[cooldown_key] = now_ts
        print(f"[Notification] [{severity.upper()}] {zone} | {title}: {message}")
        return True
    except Exception as e:
        print(f"[Notification Insert Error] {e}")
        return False


def check_and_fire_notifications(dashboard_data: Dict[str, Any], selected_crops: Dict[str, str]) -> None:
    """
    Check sensor values against thresholds and fire notifications if exceeded.
    Called every sensor cycle from live_prediction.py.
    """
    for zone_key, rack_label in [("Zone1", "Rack 1"), ("Zone2", "Rack 2")]:
        z = dashboard_data.get(zone_key, {})
        temp = float(z.get("Temperature", 0))
        hum = float(z.get("Humidity", 0))
        soil = float(z.get("Soil_Moisture", 0))
        air = int(z.get("Air", 0))
        water = float(dashboard_data.get("Common_Water_Level", 0))
        crop = selected_crops.get(zone_key, "Unknown")

        sensor_snap = {
            "temperature": temp, "humidity": hum,
            "soil": soil, "air": air, "water_tank": water
        }

        # High temperature
        if temp > NOTIFICATION_THRESHOLDS["temperature_high"]:
            insert_notification(
                zone=zone_key, notif_type="temperature_high",
                title="High Temperature Alert",
                message=f"{rack_label} temperature is {temp}C (threshold: {NOTIFICATION_THRESHOLDS['temperature_high']}C). Fan may be required.",
                severity="critical", sensor_values=sensor_snap
            )

        # Low temperature
        if temp < NOTIFICATION_THRESHOLDS["temperature_low"] and temp > 0:
            insert_notification(
                zone=zone_key, notif_type="temperature_low",
                title="Low Temperature Alert",
                message=f"{rack_label} temperature dropped to {temp}C (threshold: {NOTIFICATION_THRESHOLDS['temperature_low']}C).",
                severity="warning", sensor_values=sensor_snap
            )

        # Low humidity
        if hum < NOTIFICATION_THRESHOLDS["humidity_low"] and hum > 0:
            insert_notification(
                zone=zone_key, notif_type="humidity_low",
                title="Low Humidity Alert",
                message=f"{rack_label} humidity is {hum}% (threshold: {NOTIFICATION_THRESHOLDS['humidity_low']}%). {crop} may need misting.",
                severity="warning", sensor_values=sensor_snap
            )

        # Dry soil
        if soil < NOTIFICATION_THRESHOLDS["soil_dry"] and soil > 0:
            insert_notification(
                zone=zone_key, notif_type="soil_dry",
                title="Dry Soil Alert",
                message=f"{rack_label} soil moisture is {soil}% (threshold: {NOTIFICATION_THRESHOLDS['soil_dry']}%). Irrigation recommended for {crop}.",
                severity="warning", sensor_values=sensor_snap
            )

        # Water tank low
        if water < NOTIFICATION_THRESHOLDS["water_tank_low"] and water > 0:
            insert_notification(
                zone="Common", notif_type="water_tank_low",
                title="Low Water Tank Alert",
                message=f"Water tank level is {water}% (threshold: {NOTIFICATION_THRESHOLDS['water_tank_low']}%). Refill required.",
                severity="critical", sensor_values=sensor_snap
            )

        # Poor air quality
        air_pct = min(100, max(0, round((air / 1000.0) * 100))) if air > 100 else air
        if air_pct > NOTIFICATION_THRESHOLDS["air_quality_poor"]:
            insert_notification(
                zone=zone_key, notif_type="air_quality_poor",
                title="Poor Air Quality Alert",
                message=f"{rack_label} air quality at {air_pct}% (threshold: {NOTIFICATION_THRESHOLDS['air_quality_poor']}%). Ventilation recommended.",
                severity="warning", sensor_values=sensor_snap
            )


def query_notifications(from_date: Optional[str] = None,
                         to_date: Optional[str] = None,
                         severity: Optional[str] = None,
                         limit: int = 200) -> List[Dict[str, Any]]:
    """Query notifications collection."""
    coll = _get_notifications_collection()
    if coll is None:
        return []
    try:
        query: Dict[str, Any] = {}
        if from_date and to_date:
            query["timestamp"] = {"$gte": from_date, "$lte": to_date}
        elif from_date:
            query["timestamp"] = {"$gte": from_date}
        elif to_date:
            query["timestamp"] = {"$lte": to_date}
        if severity and severity != "all":
            query["severity"] = severity
        cursor = coll.find(query, {"_id": 0}).sort("timestamp", DESCENDING).limit(limit)
        return list(cursor)
    except Exception as e:
        print(f"[Notifications Query Error] {e}")
        return []


# =========================================================================
# TELEMETRY HISTORY QUERY
# =========================================================================

def query_mongo_history(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    limit: int = 2000
) -> List[Dict[str, Any]]:
    """Query MongoDB collection 'farm_history' for historical documents."""
    coll = get_mongo_collection()
    if coll is None:
        return []
    try:
        query: Dict[str, Any] = {}
        if from_date and to_date:
            query["timestamp"] = {"$gte": from_date, "$lte": to_date}
        elif from_date:
            query["timestamp"] = {"$gte": from_date}
        elif to_date:
            query["timestamp"] = {"$lte": to_date}
        cursor = coll.find(query, {"_id": 0}).sort("timestamp", DESCENDING).limit(limit)
        return list(cursor)
    except Exception as e:
        print(f"[MongoDB Query Error] {type(e).__name__}: {e}")
        return []
