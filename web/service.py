import json
import threading
import time
from datetime import datetime, timezone
from pathlib import Path


class LogStore:
    """Persist simple application log entries to a JSONL file."""

    def __init__(self, path: str | Path | None = None):
        base_dir = Path(__file__).resolve().parent.parent
        self.path = Path(path) if path is not None else base_dir / "logs" / "system.log"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)

    def _record(self, level: str, message: str, **extra):
        entry = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "level": level,
            "message": str(message),
        }
        if extra:
            entry.update(extra)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return entry

    def info(self, message: str, **extra):
        return self._record("INFO", message, **extra)

    def warning(self, message: str, **extra):
        return self._record("WARNING", message, **extra)

    def error(self, message: str, **extra):
        return self._record("ERROR", message, **extra)

    def read(self, limit: int = 200):
        if not self.path.exists():
            return []
        entries = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    payload = {"message": line.strip()}
                entries.append(payload)
        return entries[-limit:]


def _driver_states(mode):
    label = "hardware" if mode == "hardware" else "simulated"
    return {"gpio": label, "usb_zigbee": label, "usb_meshtastic": label}


class StateService:
    """In-memory application state shared by the web views (single instance)."""

    _instance = None
    _lock = threading.RLock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self._logger = LogStore()
        self._state = {
            "v": 3,
            "ts": time.time(),
            "mode": "simulation",
            "alert": {"active": False, "type": None, "source": None, "distance_cm": None, "expires_in_s": None},
            "outputs": {"buzzer": 0, "led": 0},
            "links": {
                "zigbee": {"state": "simulated"},
                "meshtastic": {"state": "simulated"},
            },
            "drivers": _driver_states("simulation"),
        }
        self._logger.info("StateService initialized")

    @property
    def logger(self):
        return self._logger

    def snapshot(self):
        with self._lock:
            self._state["ts"] = time.time()
            return json.loads(json.dumps(self._state))

    def set_output(self, channel, value, duration_ms=None):
        with self._lock:
            if channel not in ("buzzer", "led"):
                raise ValueError("invalid channel")
            if value not in (0, 1) or isinstance(value, bool):
                raise ValueError("invalid value")
            self._state["outputs"][channel] = int(value)
            if duration_ms is not None:
                self._state["outputs"][f"{channel}_ttl_ms"] = int(duration_ms)
        self._logger.info(f"Output {channel} set to {value}", channel=channel, value=int(value))

    def set_outputs_off(self):
        with self._lock:
            self._state["outputs"]["buzzer"] = 0
            self._state["outputs"]["led"] = 0
        self._logger.info("Outputs disabled")

    def ack_alert(self):
        with self._lock:
            self._state["alert"] = {"active": False, "type": None, "source": None,
                                    "distance_cm": None, "expires_in_s": None}
        self._logger.info("Alert acknowledged")

    def set_mode(self, mode):
        with self._lock:
            normalized = str(mode or "").strip().lower()
            if normalized in ("sim", "simulation", "virtual"):
                self._state["mode"] = "simulation"
            elif normalized in ("hw", "hardware", "real"):
                self._state["mode"] = "hardware"
            else:
                raise ValueError("invalid mode: choose simulation or hardware")
            self._state["drivers"] = _driver_states(self._state["mode"])
        self._logger.info(f"Mode changed to {normalized}", mode=normalized)

    def inject_impact(self):
        """Simulated remote impact alert (scripted remote vehicle V2)."""
        with self._lock:
            self._state["alert"] = {
                "active": True,
                "type": "impact",
                "source": "V2",
                "distance_cm": None,
                "expires_in_s": 5,
            }
        self._logger.warning("Impact alert simulated", source="V2")

    def start(self):
        self.set_mode("simulation")

    def pause(self):
        pass

    def stop(self):
        self.set_outputs_off()
        self.ack_alert()
