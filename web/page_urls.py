from django.urls import path

from . import pages

app_name = "web"

urlpatterns = [
    path("", pages.index, name="index"),
    path("devices/", pages.page_devices, name="devices"),
    path("simulator/", pages.page_simulator, name="simulator"),
    path("tests/", pages.page_tests, name="tests"),
]
