"""Phase 1 (F1): the signal bus is real.

Tests written test-first, before the implementation:
- ALR_vStep takes no level/impact/distance arguments; it reads the RTE signals.
- PRX publishes the distance-sensor validity through RTE_u8GetDistanceSensorStatus.
- NODE publishes the vibration input level (RTE_u8GetVibrationState) and logs link up/down
  transitions once per second (RTE_u8GetTick1s + mesh/zigbee status).
- Every public RTE_* function has a caller in app/, web/ or sim/.
- docs/rte_api.md contains the Signal | Writer | Readers table and every listed module really calls it.

Run with: MCD_SIMULATE=1 python -m pytest tests/test_phase1_f1.py  (or via manage.py test)
"""

import ast
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

import rte  # noqa: E402


def _callers(name):
    """Modules in app/, web/ or sim/ that call the RTE function ``name``."""
    found = set()
    for layer in ("app", "web", "sim"):
        base = os.path.join(ROOT, layer)
        for folder, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                path = os.path.join(folder, fname)
                try:
                    tree = ast.parse(open(path, encoding="utf-8").read())
                except SyntaxError:
                    continue
                for node in ast.walk(tree):
                    called = None
                    if isinstance(node, ast.Call):
                        f = node.func
                        if isinstance(f, ast.Attribute):
                            called = f.attr
                        elif isinstance(f, ast.Name):
                            called = f.id
                    elif isinstance(node, ast.Name) and node.id == name:
                        # registered as a value (e.g. _SENDERS dict, getter tuple) is a real use
                        called = name
                    if isinstance(node, ast.ImportFrom) and name in (a.name for a in node.names):
                        # an import alone is not a call; only count real uses below
                        continue
                    if called == name:
                        found.add(layer + "/" + os.path.relpath(path, base))
                        break
        # module-level scan continues
    return found


class DeadApiTests(unittest.TestCase):
    def test_every_public_rte_function_has_a_caller(self):
        dead = []
        for name in sorted(dir(rte)):
            if not name.startswith("RTE_") or not callable(getattr(rte, name)):
                continue
            # the writer of a signal pair is called by its own reader-side module; count calls inside rte itself too
            callers = _callers(name)
            if not callers:
                dead.append(name)
        self.assertEqual(dead, [], "dead RTE functions with no caller in app/, web/ or sim/: %s" % ", ".join(dead))


class SignalBusTests(unittest.TestCase):
    def test_alr_vstep_has_no_signal_arguments(self):
        sig = ast.parse(open(os.path.join(ROOT, "app", "alr.py"), encoding="utf-8").read())
        for node in ast.walk(sig):
            if isinstance(node, ast.FunctionDef) and node.name == "ALR_vStep":
                args = [a.arg for a in node.args.args]
                self.assertEqual(args[:2], ["manager", "now_ms"],
                                 "ALR_vStep must take only (manager, now_ms), got %s" % args)
                self.assertNotIn("level", args)
                self.assertNotIn("impact", args)
                self.assertNotIn("distance_cm", args)

    def test_alr_reads_signals(self):
        text = open(os.path.join(ROOT, "app", "alr.py"), encoding="utf-8").read()
        for reader in ("RTE_u8ReadAlertLevel", "RTE_u8ReadImpact", "RTE_u16ReadDistanceCm"):
            self.assertRegex(text, r"%s\(\)" % reader, "ALR must read %s" % reader)

    def test_prx_uses_the_status_flag_as_validity(self):
        text = open(os.path.join(ROOT, "app", "prx.py"), encoding="utf-8").read()
        self.assertRegex(text, r"RTE_u8GetDistanceSensorStatus\(\)",
                         "PRX_vStep must use the status getter as the validity flag")

    def test_acceptance_signals_drive_the_outputs(self):
        """Drive ALR only through the bus: write signals, step, check buzzer/LED and packets."""
        from app.alr import AlertManager, ALR_vStep
        rte.RTE_vDeinit()                       # clean signal store
        sent = []
        def on_tx(radio, kind, level):
            sent.append((radio, kind, level))
        # danger level + impact active on the bus
        rte.RTE_vWriteAlertLevel(3)
        rte.RTE_vWriteImpact(1)
        rte.RTE_vWriteDistanceCm(25)
        actions = ALR_vStep(AlertManager(), 1000, on_tx=on_tx)
        self.assertEqual(actions["buzzer"], 1, "level 3 must drive the buzzer through the bus")
        self.assertEqual(actions["led"], 1, "level 3 must drive the LED through the bus")
        # in simulation the send functions return 0 (no real radio), so assert the planned packets
        self.assertTrue(actions["send"], "the node must send an alert built from the bus signals")
        radio, kind, level, distance = actions["send"][0]
        self.assertEqual(kind, rte.RTE_KIND_IMPACT)
        self.assertEqual(level, 3)
        from mcd import pcs
        from mcd.config import GPIO_BUZZER, GPIO_LED
        self.assertEqual(pcs.PCS_u8GetGpio(GPIO_BUZZER), 1, "the buzzer pin must be on after the bus step")
        self.assertEqual(pcs.PCS_u8GetGpio(GPIO_LED), 1, "the LED pin must be on after the bus step")

    def test_node_publishes_vibration_level(self):
        text = open(os.path.join(ROOT, "app", "node.py"), encoding="utf-8").read()
        self.assertRegex(text, r"RTE_u8GetVibrationState\(\)",
                         "NODE_tGetStatus must read the vibration input level")

    def test_node_logs_link_transitions_once_per_second(self):
        text = open(os.path.join(ROOT, "app", "node.py"), encoding="utf-8").read()
        self.assertRegex(text, r"RTE_u8GetTick1s\(\)", "NODE must use the 1 s tick")
        from unittest import mock
        from app import node
        runtime = node.NodeRuntime()
        with mock.patch.object(node, "RTE_u8GetTick1s", return_value=1), \
             mock.patch.object(node, "RTE_u8GetMeshStatus", return_value=1), \
             mock.patch.object(node, "RTE_u8GetZigbeeStatus", return_value=0):
            runtime._check_links(1000)
        self.assertEqual([], [e for e in runtime.events if "link" in e["text"]],
                         "the first check only records the state, it must not log")
        with mock.patch.object(node, "RTE_u8GetMeshStatus", return_value=0), \
             mock.patch.object(node, "RTE_u8GetZigbeeStatus", return_value=1):
            runtime._check_links(2000)
        texts = [e["text"] for e in runtime.events]
        self.assertIn("mesh link down", texts, "NODE must log mesh link up/down")
        self.assertIn("zigbee link up", texts, "NODE must log zigbee link up/down")

    def test_dashboard_shows_vibration_input_level(self):
        src = open(os.path.join(ROOT, "web", "api.py"), encoding="utf-8").read()
        self.assertIn("vibration_level", src,
                      "the Tests page status must include the vibration input level")


class RteApiTableTests(unittest.TestCase):
    TABLE_RE = re.compile(r"^\|\s*`?(\w+)`?\s*\|\s*([\w/\.]+)\s*\|\s*([^|]+)\|\s*$", re.M)
    SIGNAL_WRITE = {"distance_cm": "RTE_vWriteDistanceCm", "alert_level": "RTE_vWriteAlertLevel",
                    "remote_alert_level": "RTE_vWriteRemoteAlertLevel", "impact": "RTE_vWriteImpact"}
    SIGNAL_READ = {"distance_cm": "RTE_u16ReadDistanceCm", "alert_level": "RTE_u8ReadAlertLevel",
                   "remote_alert_level": "RTE_u8ReadRemoteAlertLevel", "impact": "RTE_u8ReadImpact"}

    def test_signal_table_exists_and_matches_the_code(self):
        text = open(os.path.join(ROOT, "docs", "rte_api.md"), encoding="utf-8").read()
        rows = self.TABLE_RE.findall(text)
        self.assertGreaterEqual(len(rows), 4, "docs/rte_api.md must contain the Signal | Writer | Readers table")

        def calls(module, func):
            path = os.path.join(ROOT, module)
            tree = ast.parse(open(path, encoding="utf-8").read())
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    f = node.func
                    name = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", None)
                    if name == func:
                        return True
            return False

        bad = []
        for signal, writer, readers in rows:
            if signal not in self.SIGNAL_WRITE:          # header or separator row
                continue
            write_fn, read_fn = self.SIGNAL_WRITE[signal], self.SIGNAL_READ[signal]
            if not calls(writer, write_fn):
                bad.append("%s: %s does not call %s" % (signal, writer, write_fn))
            for reader in [r.strip() for r in readers.split(",")]:
                if not calls(reader, read_fn):
                    bad.append("%s: %s does not call %s" % (signal, reader, read_fn))
        self.assertEqual(bad, [])


if __name__ == "__main__":
    unittest.main()
