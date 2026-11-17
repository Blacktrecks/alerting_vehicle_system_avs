import atexit
import os
import sys

from django.apps import AppConfig

from .runtime import should_start_runtime


class WebConfig(AppConfig):
    name = "web"
    verbose_name = "Web dashboard"

    def ready(self):
        if not should_start_runtime(sys.argv, os.environ):
            return
        from app import node
        node.NODE_vStart()
        atexit.register(node.NODE_vStop)       # buzzer and LED are forced off when the process exits
