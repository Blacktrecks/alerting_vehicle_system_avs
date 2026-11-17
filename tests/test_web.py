"""Tests for the Django layer (run with: MCD_SIMULATE=1 python manage.py test)."""
import json
import os

from django.test import SimpleTestCase
from django.urls import reverse

from mcd import config, pcs, tim, usb


class ViewTests(SimpleTestCase):
    def setUp(self):
        old = os.environ.get(config.SIM_ENV)
        os.environ[config.SIM_ENV] = "1"

        def restore():
            pcs.PCS_vDeinit()
            usb.USB_vCloseAll()
            tim.TIM_vInit()
            if old is None:
                os.environ.pop(config.SIM_ENV, None)
            else:
                os.environ[config.SIM_ENV] = old

        self.addCleanup(restore)

    def test_index_shows_pin_table(self):
        resp = self.client.get(reverse("web:index"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Proximity and Impact Warning System")
        for row in config.PIN_TABLE:
            self.assertContains(resp, row["signal_name"])

    def test_no_removed_hardware_in_pin_table(self):
        names = {row["signal_name"] for row in config.PIN_TABLE}
        self.assertFalse(names & {"I2C_SDA", "I2C_SCL", "VCC_MPU"})

    def test_api_pins(self):
        resp = self.client.get(reverse("api_pins"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()["pins"]), len(config.PIN_TABLE))

    def test_api_state_schema_has_no_demo_data(self):
        resp = self.client.get(reverse("api_state"))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        for key in ("mode", "alert", "outputs", "links", "drivers"):
            self.assertIn(key, data)
        for removed in ("ego", "neighbours", "accel", "stats", "devices"):
            self.assertNotIn(removed, data)

    def test_api_selftest_post_only_and_passes(self):
        self.assertEqual(self.client.get(reverse("api_selftest")).status_code, 405)
        resp = self.client.post(reverse("api_selftest"))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ok"], data["log"])
        self.assertGreater(data["tests_run"], 20)

    def test_navigation_pages_exist(self):
        for path in ("/", "/devices/", "/simulator/", "/tests/"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_removed_pages_are_gone(self):
        for path in ("/stats/", "/operator/", "/diagnostics/", "/api/dashboard/", "/api/accel/"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 404)

    def test_api_mode_toggle(self):
        for mode in ("simulation", "hardware", "simulation"):
            resp = self.client.post("/api/mode/", data={"mode": mode}, content_type="application/json")
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.json()["state"]["mode"], mode)

    def test_api_mode_rejects_invalid_mode(self):
        resp = self.client.post("/api/mode/", data={"mode": "warp"}, content_type="application/json")
        self.assertEqual(resp.status_code, 400)

    def test_api_mode_toggle_with_csrf(self):
        client = self.client_class(enforce_csrf_checks=True)
        resp = client.get("/")
        self.assertEqual(resp.status_code, 200)
        csrf_token = resp.cookies.get("csrftoken")
        self.assertIsNotNone(csrf_token)

        denied = client.post("/api/mode/", data=json.dumps({"mode": "hardware"}), content_type="application/json")
        self.assertEqual(denied.status_code, 403)

        resp = client.post(
            "/api/mode/",
            data=json.dumps({"mode": "hardware"}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf_token.value,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["state"]["mode"], "hardware")
        client.post("/api/mode/", data=json.dumps({"mode": "simulation"}),
                    content_type="application/json", HTTP_X_CSRFTOKEN=csrf_token.value)

    def test_post_not_allowed_on_read_only_endpoints(self):
        self.assertEqual(self.client.post(reverse("api_pins")).status_code, 405)
        self.assertEqual(self.client.post(reverse("api_state")).status_code, 405)

    def test_static_files_are_served_without_debug(self):
        resp = self.client.get("/static/web/css/app.css")
        self.assertEqual(resp.status_code, 200)
