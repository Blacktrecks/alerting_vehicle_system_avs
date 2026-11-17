"""NODE: the runtime step, called every 100 ms by ONE background thread (started from web/apps.py).

``NODE_vStep`` runs PRX -> IMP -> ALR -> RPT once. ``NODE_vStart`` / ``NODE_vStop`` manage the single
runtime thread and the RTE lifecycle; the thread forces buzzer and LED off when it stops, also after
an unexpected error. Web views read ``NODE_tGetStatus`` / ``NODE_lGetEvents`` and never touch hardware.
"""

import threading
import time
from collections import deque

from rte import (RTE_DISTANCE_INVALID, RTE_u8GetTick60s, RTE_u8GetTick100ms, RTE_u16ReadDistanceCm,
                 RTE_vDeinit, RTE_vInit)

from .alr import ALR_vShutdown, ALR_vStep, AlertManager
from .imp import IMP, IMP_vStep
from .prx import PRX, PRX_vStep
from .rpt import RPT

NODE_STEP_S = 0.1
NODE_EVENTS_MAX = 100

_lock = threading.RLock()
_thread = None
_stop = threading.Event()


class NodeRuntime:
    """All application state of the node; one instance is used by the runtime thread."""

    def __init__(self):
        self.prx = PRX()
        self.imp = IMP()
        self.alr = AlertManager()
        self.rpt = RPT()
        self.events = deque(maxlen=NODE_EVENTS_MAX)
        self.last_report = None
        self.distance_cm = RTE_DISTANCE_INVALID
        self.level = 0
        self.impact = 0
        self.buzzer = 0
        self.led = 0
        self.steps = 0
        self._fault_prev = False

    def log(self, text):
        self.events.append({"time": time.time(), "text": text})

    def step(self, now_ms):
        old_level = self.level
        self.level = PRX_vStep(self.prx, now_ms)
        self.distance_cm = RTE_u16ReadDistanceCm()
        valid = self.distance_cm != RTE_DISTANCE_INVALID
        self.rpt.add_sample(self.distance_cm, self.level, valid)
        if self.level != old_level:
            self.log("level %d -> %d" % (old_level, self.level))
        if self.prx.fault and not self._fault_prev:
            self.rpt.add_fault()
            self.log("sensor fault")
        elif self._fault_prev and not self.prx.fault:
            self.log("sensor recovered")
        self._fault_prev = self.prx.fault

        if IMP_vStep(self.imp, now_ms):
            self.rpt.add_impact()
            self.log("impact detected")
        self.impact = 1 if self.imp.active(now_ms) else 0

        def on_rx(radio, alert):
            self.rpt.add_rx(radio)
            self.log("remote alert via %s: node %s kind %d level %d" % (
                radio, alert["node"], alert["kind"], alert["level"]))

        actions = ALR_vStep(self.alr, now_ms, self.level, self.impact, self.distance_cm,
                            on_rx=on_rx, on_tx=lambda radio, kind, level: self.rpt.add_tx(radio))
        self.buzzer, self.led = actions["buzzer"], actions["led"]
        if RTE_u8GetTick60s():
            self.last_report = self.rpt.snapshot(reset=True)
            self.log("report: %d samples, max level %d, %d impacts" % (
                self.last_report["samples"], self.last_report["max_level"], self.last_report["impacts"]))
        self.steps += 1


def _now_ms():
    return int(time.monotonic() * 1000)


_runtime = NodeRuntime()


def NODE_vStep(now_ms=None):
    """Run one application step (PRX, IMP, ALR, RPT). Called every 100 ms by the runtime thread."""
    with _lock:
        _runtime.step(_now_ms() if now_ms is None else now_ms)


def _loop(stop):
    try:
        while not stop.is_set():
            if RTE_u8GetTick100ms():
                try:
                    NODE_vStep()
                except Exception as exc:                  # keep running, but never leave outputs on
                    ALR_vShutdown()
                    _runtime.log("step error: %s" % exc)
            stop.wait(0.01)
    finally:
        ALR_vShutdown()


def NODE_vStart():
    """Initialize the RTE and start the single runtime thread (safe to call twice)."""
    global _thread, _runtime
    with _lock:
        if _thread is not None and _thread.is_alive():
            return
        RTE_vInit()
        _runtime = NodeRuntime()
        _stop.clear()
        _thread = threading.Thread(target=_loop, args=(_stop,), name="node-runtime", daemon=True)
        _thread.start()


def NODE_vStop():
    """Stop the runtime thread, force buzzer and LED off and deinitialize the RTE."""
    global _thread
    with _lock:
        _stop.set()
        thread, _thread = _thread, None
    if thread is not None:
        thread.join(timeout=2.0)
    ALR_vShutdown()
    RTE_vDeinit()


def NODE_bIsRunning():
    return _thread is not None and _thread.is_alive()


def NODE_bAlertActive():
    """True while a real alert is active (used to refuse manual buzzer/LED tests)."""
    return _runtime.alr.active


def NODE_tGetStatus():
    """Snapshot for the dashboard: distance, level, buzzer, LED, impact, fault, last remote alert, report."""
    with _lock:
        r = _runtime
        return {
            "distance_cm": None if r.distance_cm == RTE_DISTANCE_INVALID else r.distance_cm,
            "level": r.level,
            "buzzer": r.buzzer,
            "led": r.led,
            "impact": r.impact,
            "sensor_fault": r.prx.fault,
            "last_remote_alert": dict(r.alr.last_remote) if r.alr.last_remote else None,
            "report": r.last_report,
            "running": NODE_bIsRunning(),
        }


def NODE_lGetEvents():
    """Recent events, oldest first."""
    with _lock:
        return list(_runtime.events)
