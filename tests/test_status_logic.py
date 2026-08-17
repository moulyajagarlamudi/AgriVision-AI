import importlib.util
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

spec = importlib.util.spec_from_file_location("main_module", ROOT / "main.py")
main_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main_module)

spec_live = importlib.util.spec_from_file_location("live_prediction_module", ROOT / "live_prediction.py")
live_prediction_module = importlib.util.module_from_spec(spec_live)
spec_live.loader.exec_module(live_prediction_module)


class FakeSerialPort:
    def __init__(self, lines):
        self._lines = list(lines)
        self.in_waiting = len(self._lines)

    def readline(self):
        if self._lines:
            self.in_waiting = len(self._lines) - 1
            return self._lines.pop(0)
        self.in_waiting = 0
        return b""


class StatusLogicTests(unittest.TestCase):
    def test_status_becomes_offline_when_latest_data_is_stale(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            os.chdir(tmp_dir)
            try:
                latest_data_path = Path("latest_data.json")
                latest_data_path.write_text(json.dumps({"status": "offline"}))
                os.utime(latest_data_path, (time.time() - 10, time.time() - 10))
                Path("system_status.json").write_text(json.dumps({"status": "online"}))

                response = main_module.status()

                self.assertEqual(response["status"], "offline")
            finally:
                os.chdir(ROOT)

    def test_data_endpoint_returns_offline_when_status_file_is_offline(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            os.chdir(tmp_dir)
            try:
                Path("system_status.json").write_text(json.dumps({"status": "offline"}))
                Path("latest_data.json").write_text(json.dumps({"Zone1": {}, "Zone2": {}}))
                response = main_module.get_data()
                self.assertEqual(response["status"], "offline")
            finally:
                os.chdir(ROOT)

    def test_automation_event_log_api_returns_success_payload(self):
        body = main_module.get_automation_events_api(limit=5)

        self.assertEqual(body["status"], "success")
        self.assertIn("data", body)

    def test_notification_center_api_returns_success_payload(self):
        body = main_module.get_notifications_api(limit=5)

        self.assertEqual(body["status"], "success")
        self.assertIn("data", body)

    def test_sensor_and_relay_parsing_keep_live_values(self):
        sensor_data = live_prediction_module._parse_sensor_packet("Zone1,27.2,74.3,62.4,1072", "Zone1")
        relay_level = live_prediction_module._parse_relay_packet("Water Level: 78%")

        self.assertEqual(sensor_data["Soil_Moisture"], 62.4)
        self.assertEqual(sensor_data["Humidity"], 74.3)
        self.assertEqual(relay_level, 78.0)

    def test_sensor_parser_accepts_prefixed_zone_labels(self):
        sensor_data = live_prediction_module._parse_sensor_packet("sensor Zone2,28.1,77.9,84.2,463", "Zone2")

        self.assertEqual(sensor_data["Zone"], "Zone2")
        self.assertEqual(sensor_data["Soil_Moisture"], 84.2)
        self.assertEqual(sensor_data["Air"], 463)

    def test_sensor_reader_prefers_latest_valid_zone_packet_over_noise(self):
        fake_port = FakeSerialPort([
            b"SOIL_RAW=1024 SOIL_PCT=60.2\r\n",
            b"Zone1,28.0,71.5,60.2,540,1024\r\n",
        ])

        sensor_data = live_prediction_module.read_sensor_data(fake_port, "Zone1")

        self.assertEqual(sensor_data["Zone"], "Zone1")
        self.assertEqual(sensor_data["Soil_Moisture"], 60.2)

    def test_port_resolution_prefers_env_override(self):
        previous = os.environ.get("ZONE1_PORT")
        try:
            os.environ["ZONE1_PORT"] = "COM9"
            candidates = live_prediction_module.resolve_port_candidates("ZONE1_PORT", ["COM6", "COM7"])
            self.assertEqual(candidates[0], "COM9")
        finally:
            if previous is None:
                os.environ.pop("ZONE1_PORT", None)
            else:
                os.environ["ZONE1_PORT"] = previous


if __name__ == "__main__":
    unittest.main()
