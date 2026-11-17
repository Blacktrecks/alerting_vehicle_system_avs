"""HTML pages of the dashboard (all state is loaded by the JavaScript from /api/state/)."""
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET

from mcd import config
from sdc.registry import DeviceRegistry

from .service import StateService


@ensure_csrf_cookie
@require_GET
def index(request):
    return render(request, "web/dashboard.html", {
        "pins": config.PIN_TABLE,
        "state": StateService().snapshot(),
    })


@ensure_csrf_cookie
@require_GET
def page_devices(request):
    devices = DeviceRegistry().scan()
    return render(request, "web/devices.html", {"devices": devices})


@ensure_csrf_cookie
@require_GET
def page_simulator(request):
    return render(request, "web/simulator.html")


@ensure_csrf_cookie
@require_GET
def page_tests(request):
    return render(request, "web/tests.html")
