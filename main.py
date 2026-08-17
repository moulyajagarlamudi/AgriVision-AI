import json
import os
import time

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from fastapi import FastAPI, HTTPException, Request
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
# NOTE: do NOT import 'system_online' directly – Python booleans are immutable
# primitives so a bare import would snapshot False at startup and never update.
# Always read it as live_prediction.system_online (module attribute lookup).



from ai_control import CROP_CONFIGURATIONS, VALID_STAGES, load_selected_crops, save_selected_crops
from mongo_logger import query_mongo_history, get_mongo_collection, query_automation_events, query_notifications
import live_prediction

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    import threading

    # 1. Health monitor (8s timeout)
    threading.Thread(
        target=live_prediction.monitor_connection_health, daemon=True
    ).start()

    # 2. MQTT client – connects to Mosquitto and forwards sensor data to live_prediction
    def _run_mqtt():
        try:
            import mqtt_client
            mqtt_client.start()
        except Exception as e:
            print(f"[MQTT] Failed to start MQTT client: {e}")

    threading.Thread(target=_run_mqtt, daemon=True).start()

    # 3. ESP32 Port 8001 background listener
    def _run_port_8001():
        try:
            import uvicorn
            uvicorn.run(live_prediction.app, host="0.0.0.0", port=8001, log_level="warning")
        except Exception as e:
            print(f"[Port 8001 Background Listener Note] {e}")

    threading.Thread(target=_run_port_8001, daemon=True).start()
    yield

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)




templates = Jinja2Templates(directory="templates")

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.post("/api/esp32/zone1")
def receive_zone1(payload: live_prediction.SensorPayload):
    return live_prediction.process_sensor_payload(payload)

@app.post("/api/esp32/zone2")
def receive_zone2(payload: live_prediction.SensorPayload):
    return live_prediction.process_sensor_payload(payload)

@app.post("/api/esp32/relay/telemetry")
def receive_relay_telemetry(payload: live_prediction.RelayTelemetryPayload):
    return live_prediction.receive_relay_telemetry(payload)

@app.get("/api/esp32/relay/commands")
def relay_commands():
    return live_prediction.relay_commands()

DATA_FRESHNESS_SECONDS = 5


def is_latest_data_fresh() -> bool:
    if not os.path.exists("latest_data.json"):
        return False
    return (time.time() - os.path.getmtime("latest_data.json")) <= DATA_FRESHNESS_SECONDS


def read_system_status() -> dict:
    if os.path.exists("system_status.json"):
        try:
            with open("system_status.json", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"status": "offline"}


from typing import Optional

class CropSelection(BaseModel):
    crop: Optional[str] = None
    stage: Optional[str] = None


@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/api/crops")
def get_selected_crops():
    return load_selected_crops()


@app.put("/api/crops/{zone}")
def set_selected_crop(zone: str, selection: CropSelection):
    if zone not in {"Zone1", "Zone2"}:
        raise HTTPException(status_code=404, detail="Unknown zone")
    selected = load_selected_crops()
    if selection.crop is not None:
        if selection.crop not in CROP_CONFIGURATIONS:
            raise HTTPException(status_code=422, detail="Unsupported crop")
        selected[zone] = selection.crop
    if selection.stage is not None:
        if selection.stage not in VALID_STAGES:
            raise HTTPException(status_code=422, detail="Unsupported stage")
        selected[f"{zone}_stage"] = selection.stage

    save_selected_crops(selected)

    # Publish updated config to HiveMQ as a retained MQTT message for ESP32
    try:
        import mqtt_client
        mqtt_client.publish_crop_config(
            zone1_crop=selected.get("Zone1", "Paddy"),
            zone1_stage=selected.get("Zone1_stage", "Vegetative"),
            zone2_crop=selected.get("Zone2", "Tomato"),
            zone2_stage=selected.get("Zone2_stage", "Vegetative"),
        )
    except Exception as e:
        print(f"[MQTT Config Publish Error] {e}")

    return {
        "zone": zone,
        "crop": selected.get(zone),
        "stage": selected.get(f"{zone}_stage"),
    }



@app.get("/data")
def get_data():
    """
    Dashboard telemetry endpoint.
    Returns live sensor readings and 'status': 'online' when telemetry is active,
    or zeroed readings and 'status': 'offline' when telemetry times out.
    """
    data = None
    if os.path.exists("latest_data.json"):
        try:
            with open("latest_data.json", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = None

    is_fresh = False
    if os.path.exists("latest_data.json"):
        if (time.time() - os.path.getmtime("latest_data.json")) <= 10.0:
            is_fresh = True

    # If the file hasn't been updated recently, we are definitively offline.
    if not is_fresh:
        return live_prediction.build_zero_dashboard()

    if data and isinstance(data, dict) and "Zone1" in data:
        file_status = str(data.get("status", "offline")).lower()
        if file_status == "offline":
            return live_prediction.build_zero_dashboard()
        
        # If file is fresh and says online, we are online.
        data["status"] = "online"
        return data

    return live_prediction.build_zero_dashboard()





@app.get("/status")
def status():
    status_info = read_system_status()
    if status_info.get("status", "offline").lower() == "online" and is_latest_data_fresh():
        return {"status": "online"}

    return {"status": "offline", "message": status_info.get("message", "No fresh ESP32 telemetry")}


@app.get("/api/automation-events")
def get_automation_events_api(from_date: str = None, to_date: str = None, zone: str = "all", limit: int = 20):
    events = query_automation_events(from_date=from_date, to_date=to_date, zone=zone, limit=limit)
    return {"status": "success", "count": len(events), "data": events}


@app.get("/api/notifications")
def get_notifications_api(from_date: str = None, to_date: str = None, severity: str = "all", limit: int = 20):
    notifications = query_notifications(from_date=from_date, to_date=to_date, severity=severity, limit=limit)
    return {"status": "success", "count": len(notifications), "data": notifications}


# =========================================================================
# FARM JOURNEY - MONGODB HISTORICAL TELEMETRY API & ROUTES
# =========================================================================

def safe_float(val, default=0.0) -> float:
    try:
        if val is None:
            return default
        return float(val)
    except Exception:
        return default


def safe_int(val, default=0) -> int:
    try:
        if val is None:
            return default
        return int(float(val))
    except Exception:
        return default


def _fetch_formatted_history(from_date: str = None, to_date: str = None, rack: str = "all", limit: int = 2000):
    """
    Core dataset loader: Queries MongoDB Atlas collection 'farm_history'.
    Falls back gracefully to CSV / synthetic generator if Mongo is offline.
    """
    records = []
    try:
        mongo_docs = query_mongo_history(from_date, to_date, limit)

        if mongo_docs:
            for doc in mongo_docs:
                ts = str(doc.get("timestamp", ""))
                d_str = str(doc.get("date", ts.split(" ")[0] if " " in ts else ""))
                t_str = ts.split(" ")[1] if " " in ts else ""
                w_tank = safe_float(doc.get("waterTank", 0.0))

                if rack in ["all", "Rack 1", "rack1"]:
                    r1 = doc.get("rack1", {})
                    records.append({
                        "timestamp": ts,
                        "date": d_str,
                        "time": t_str,
                        "rack": "Rack 1",
                        "crop": str(r1.get("crop", "Amaranthus")),
                        "stage": str(r1.get("stage", "Vegetative")),
                        "temperature": safe_float(r1.get("temperature", 0.0)),
                        "humidity": safe_float(r1.get("humidity", 0.0)),
                        "soil_moisture": safe_float(r1.get("soil", 0.0)),
                        "air_quality": safe_int(r1.get("air", 0)),
                        "water_tank": w_tank,
                        "pump": safe_int(r1.get("pump", 0)),
                        "fan": safe_int(r1.get("fan", 0)),
                        "uv": safe_int(r1.get("uv", 0))
                    })

                if rack in ["all", "Rack 2", "rack2"]:
                    r2 = doc.get("rack2", {})
                    records.append({
                        "timestamp": ts,
                        "date": d_str,
                        "time": t_str,
                        "rack": "Rack 2",
                        "crop": str(r2.get("crop", "Tomato")),
                        "stage": str(r2.get("stage", "Flowering")),
                        "temperature": safe_float(r2.get("temperature", 0.0)),
                        "humidity": safe_float(r2.get("humidity", 0.0)),
                        "soil_moisture": safe_float(r2.get("soil", 0.0)),
                        "air_quality": safe_int(r2.get("air", 0)),
                        "water_tank": w_tank,
                        "pump": safe_int(r2.get("pump", 0)),
                        "fan": safe_int(r2.get("fan", 0)),
                        "uv": safe_int(r2.get("uv", 0))
                    })

        # Fallback to CSV / Synthetic ONLY if MongoDB Atlas is offline or contains 0 records
        if not mongo_docs:
            csv_file = "dataset/AgriVision_training.csv"
            if os.path.exists(csv_file):
                try:
                    import csv
                    with open(csv_file, "r") as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            ts = str(row.get("timeStamp", ""))
                            parts = ts.split(" ")
                            d_str = parts[0] if len(parts) > 0 else "2026-07-30"
                            t_str = parts[1] if len(parts) > 1 else "00:00:00"

                            raw_zone = row.get("Zone", "Zone1")
                            rack_name = "Rack 1" if "1" in str(raw_zone) else "Rack 2"

                            record = {
                                "timestamp": ts,
                                "date": d_str,
                                "time": t_str,
                                "rack": rack_name,
                                "crop": "Amaranthus" if rack_name == "Rack 1" else "Tomato",
                                "stage": "Vegetative" if rack_name == "Rack 1" else "Flowering",
                                "temperature": safe_float(row.get("Temperature", 25.0)),
                                "humidity": safe_float(row.get("Humidity", 65.0)),
                                "soil_moisture": safe_float(row.get("Soil_Moisture", 70.0)),
                                "air_quality": safe_int(row.get("Air", 450)),
                                "water_tank": safe_float(row.get("Water_Level", 80.0)),
                                "pump": safe_int(row.get("Pump", 0)),
                                "fan": safe_int(row.get("Fan", 0)),
                                "uv": safe_int(row.get("Light_Output", 0))
                            }
                            records.append(record)
                except Exception as e:
                    print(f"Error reading CSV fallback: {e}")

            # Synthetic fallback only if CSV also empty
            if not records:
                import datetime
                now = datetime.datetime.now()
                base_time = now - datetime.timedelta(hours=12)
                records = []
                for i in range(48):
                    cur = base_time + datetime.timedelta(minutes=i * 15)
                    d_str = cur.strftime("%Y-%m-%d")
                    t_str = cur.strftime("%H:%M:%S")

                    for r_name in ["Rack 1", "Rack 2"]:
                        temp = round(24.0 + (i % 8) * 0.8 + (1.2 if r_name == "Rack 2" else 0), 1)
                        hum = round(60.0 + (i % 6) * 2.5, 1)
                        soil = round(75.0 - (i % 10) * 1.5, 1)
                        air = 400 + (i % 12) * 15
                        water = round(90.0 - (i * 0.5) % 30, 1)

                        records.append({
                            "timestamp": f"{d_str} {t_str}",
                            "date": d_str,
                            "time": t_str,
                            "rack": r_name,
                            "crop": "Amaranthus" if r_name == "Rack 1" else "Tomato",
                            "stage": "Vegetative" if r_name == "Rack 1" else "Flowering",
                            "temperature": temp,
                            "humidity": hum,
                            "soil_moisture": soil,
                            "air_quality": air,
                            "water_tank": water,
                            "pump": 1 if soil < 65 else 0,
                            "fan": 1 if temp > 28 else 0,
                            "uv": 1 if 6 <= cur.hour <= 22 else 0
                        })

        if rack and rack != "all":
            records = [r for r in records if r["rack"].lower().replace(" ", "") == rack.lower().replace(" ", "")]

        records.sort(key=lambda x: str(x.get("timestamp", "")))
    except Exception as err:
        print(f"[_fetch_formatted_history error] {err}")

    return records


@app.get("/journey")
def farm_journey(request: Request):
    """Render the Farm Journey page."""
    return templates.TemplateResponse(request=request, name="farm_journey.html")


@app.get("/api/history")
def get_history(from_date: str = None, to_date: str = None, rack: str = "all", param: str = "all"):
    records = _fetch_formatted_history(from_date, to_date, rack)
    return {"status": "success", "count": len(records), "data": records}


# =========================================================================
# REQUIRED MONGODB HISTORY FASTAPI ENDPOINTS
# =========================================================================

@app.get("/history/today")
def get_history_today(rack: str = "all"):
    import datetime
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    from_date = f"{today_str} 00:00:00"
    to_date = f"{today_str} 23:59:59"
    records = _fetch_formatted_history(from_date, to_date, rack)
    return {"status": "success", "period": "today", "count": len(records), "data": records}


@app.get("/history/yesterday")
def get_history_yesterday(rack: str = "all"):
    import datetime
    yest_str = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    from_date = f"{yest_str} 00:00:00"
    to_date = f"{yest_str} 23:59:59"
    records = _fetch_formatted_history(from_date, to_date, rack)
    return {"status": "success", "period": "yesterday", "count": len(records), "data": records}


@app.get("/history/week")
def get_history_week(rack: str = "all"):
    import datetime
    now = datetime.datetime.now()
    from_date = (now - datetime.timedelta(days=7)).strftime("%Y-%m-%d 00:00:00")
    to_date = now.strftime("%Y-%m-%d %H:%M:%S")
    records = _fetch_formatted_history(from_date, to_date, rack)
    return {"status": "success", "period": "week", "count": len(records), "data": records}


@app.get("/history/month")
def get_history_month(rack: str = "all"):
    import datetime
    now = datetime.datetime.now()
    from_date = (now - datetime.timedelta(days=30)).strftime("%Y-%m-%d 00:00:00")
    to_date = now.strftime("%Y-%m-%d %H:%M:%S")
    records = _fetch_formatted_history(from_date, to_date, rack)
    return {"status": "success", "period": "month", "count": len(records), "data": records}


@app.get("/history/custom")
def get_history_custom(from_date: str = None, to_date: str = None, rack: str = "all"):
    records = _fetch_formatted_history(from_date, to_date, rack)
    return {"status": "success", "period": "custom", "count": len(records), "data": records}


@app.get("/history/latest")
def get_history_latest():
    records = _fetch_formatted_history(limit=10)
    latest_record = records[-1] if records else {}
    return {"status": "success", "data": latest_record}


@app.get("/history/rack1")
def get_history_rack1(from_date: str = None, to_date: str = None):
    records = _fetch_formatted_history(from_date, to_date, rack="Rack 1")
    return {"status": "success", "rack": "Rack 1", "count": len(records), "data": records}


@app.get("/history/rack2")
def get_history_rack2(from_date: str = None, to_date: str = None):
    records = _fetch_formatted_history(from_date, to_date, rack="Rack 2")
    return {"status": "success", "rack": "Rack 2", "count": len(records), "data": records}


if __name__ == "__main__":
    import uvicorn

    print("\n==============================================================")
    print("          AgriVision AI - System Starting")
    print("==============================================================")
    print(" Dashboard : http://0.0.0.0:8000")
    print(" MQTT      : Starting automatically...")
    print(" AI Engine : Starting automatically...")
    print(" MongoDB   : Connecting automatically...")
    print("==============================================================\n")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )