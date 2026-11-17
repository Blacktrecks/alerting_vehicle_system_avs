"""Layer tests for the BSW routing (IOC) and the old RTE helpers, with real assertions."""
import ast
import os
import unittest

from app import rpt
from ioc import IOC_CH_BUZZER, IOC_CH_LED, IOC_vSetOutputPort
from mcd import config, pcs
from rte import vSetAlertaSonora, vSetAlertaVizuala
from sdc.packets import AlertPacket, PositionPacket, decode_packet, encode_position_packet, validate_replay


class Phase1LayerTests(unittest.TestCase):
    def setUp(self):
        self._old = os.environ.get(config.SIM_ENV)
        os.environ[config.SIM_ENV] = "1"
        pcs.PCS_vDeinit()

    def tearDown(self):
        pcs.PCS_vDeinit()
        if self._old is None:
            os.environ.pop(config.SIM_ENV, None)
        else:
            os.environ[config.SIM_ENV] = self._old

    def test_ioc_routes_known_channels(self):
        IOC_vSetOutputPort(IOC_CH_BUZZER, 1)
        self.assertEqual(pcs.PCS_u8GetGpio(config.GPIO_BUZZER), 1)
        self.assertEqual(pcs.PCS_u8GetGpio(config.GPIO_LED), 0)
        IOC_vSetOutputPort(IOC_CH_LED, 1)
        self.assertEqual(pcs.PCS_u8GetGpio(config.GPIO_LED), 1)
        IOC_vSetOutputPort(IOC_CH_BUZZER, 0)
        self.assertEqual(pcs.PCS_u8GetGpio(config.GPIO_BUZZER), 0)
        self.assertEqual(pcs.PCS_u8GetGpio(config.GPIO_LED), 1)

    def test_unknown_channel_is_ignored(self):
        IOC_vSetOutputPort(IOC_CH_BUZZER, 1)
        IOC_vSetOutputPort(0xFFFF, 0)
        self.assertEqual(pcs.PCS_u8GetGpio(config.GPIO_BUZZER), 1)
        self.assertEqual(pcs.PCS_u8GetGpio(config.GPIO_LED), 0)

    def test_rte_valid_values_drive_the_pins(self):
        vSetAlertaSonora(1)
        vSetAlertaVizuala(1)
        self.assertEqual(pcs.PCS_u8GetGpio(config.GPIO_BUZZER), 1)
        self.assertEqual(pcs.PCS_u8GetGpio(config.GPIO_LED), 1)
        vSetAlertaSonora(0)
        self.assertEqual(pcs.PCS_u8GetGpio(config.GPIO_BUZZER), 0)
        self.assertEqual(pcs.PCS_u8GetGpio(config.GPIO_LED), 1)

    def test_rte_invalid_values_leave_the_pins_unchanged(self):
        vSetAlertaSonora(1)
        for bad in (2, -1, 0.6, True, None, "1"):
            vSetAlertaSonora(bad)
            self.assertEqual(pcs.PCS_u8GetGpio(config.GPIO_BUZZER), 1, "value %r" % (bad,))
        vSetAlertaVizuala(0)
        for bad in (5, -1, None, "0"):
            vSetAlertaVizuala(bad)
            self.assertEqual(pcs.PCS_u8GetGpio(config.GPIO_LED), 0, "value %r" % (bad,))

    def test_position_packet_round_trip(self):
        # NOTE: replaced by the unified alert packet in phase P2 (this test then goes away with it).
        pkt = encode_position_packet(7, 123456789, 47.15, 27.59, 42, 90, vehicle_id="V1")
        decoded = decode_packet(pkt)
        self.assertEqual(decoded["seq"], 7)
        self.assertEqual(decoded["vehicle_id"], "V1")
        self.assertEqual(decoded["speed_kmh"], 42)
        self.assertEqual(decoded["heading_deg"], 90)
        # Known defect (AGENTS.md section 9, item 2), fixed in phase P2:
        # validate_replay currently accepts only an equal seq. Kept unchanged here.
        self.assertTrue(validate_replay(7, 7))
        self.assertFalse(validate_replay(7, 6))

    def test_alert_packet_decode(self):
        pkt = AlertPacket(seq=9, vehicle_id="V3", alert_type="impact", distance_m=12).encode()
        decoded = decode_packet(pkt)
        self.assertEqual(decoded["alert_type"], "impact")
        self.assertEqual(decoded["distance_m"], 12)

    def test_report_for_alert_and_clear(self):
        report = rpt.build_report({"active": True, "type": "impact", "source": "V2"}, [{"id": "V3"}])
        self.assertEqual(report["status"], "impact")
        self.assertEqual(report["source"], "V2")
        self.assertEqual(report["neighbour_count"], 1)
        self.assertEqual(rpt.build_report(None, [])["status"], "clear")

    def test_app_import_rule(self):
        app_dir = os.path.join(os.path.dirname(__file__), "..", "app")
        checked = 0
        for root, _, files in os.walk(app_dir):
            for file_name in files:
                if not file_name.endswith(".py"):
                    continue
                path = os.path.join(root, file_name)
                with open(path, "r", encoding="utf-8") as handle:
                    tree = ast.parse(handle.read(), filename=path)
                checked += 1
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        names = [alias.name for alias in node.names]
                        self.assertNotIn("mcd", names)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module and node.module.startswith("mcd"):
                            self.fail(f"app module imports mcd: {path}")
        self.assertGreater(checked, 0)


if __name__ == "__main__":
    unittest.main()
