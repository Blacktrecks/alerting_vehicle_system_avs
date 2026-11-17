"""MCD configuration: pin mapping, channels and simulation mode."""
import os

# --------------------------------------------------------------- simulation
# MCD_SIMULATE = "auto" (default): real hardware if the library and the device
#                exist, otherwise simulation (running on a PC);
#                "1": forced simulation; "0": forced hardware (error if missing).
SIM_ENV = "MCD_SIMULATE"


def simulation_mode():
    return os.environ.get(SIM_ENV, "auto").strip().lower()


def use_simulation(hw_available):
    """Decide whether a driver runs in simulation."""
    mode = simulation_mode()
    if mode in ("1", "true", "yes", "on"):
        return True
    if mode in ("0", "false", "no", "off"):
        return False
    return not hw_available


# --------------------------------------------------------------------- GPIO
PCS_PIN_MIN = 0
PCS_PIN_MAX = 27          # valid range from L3 (BCM numbering)

GPIO_BUZZER = 17          # buzzer through an NPN transistor
GPIO_LED = 27             # LED with a 330 ohm resistor
OUTPUT_PINS = (GPIO_BUZZER, GPIO_LED)

# --------------------------------------------------------------------- USB
USB_CH_ZIGBEE = 0         # XBee3 through a USB adapter
USB_CH_MESHTASTIC = 1     # Meshtastic ESP module

_USB_DEFAULTS = {
    USB_CH_ZIGBEE: {"name": "ZIGBEE", "port": "/dev/ttyUSB0", "baud": 9600,
                    "env": "MCD_ZIGBEE_PORT"},
    USB_CH_MESHTASTIC: {"name": "MESHTASTIC", "port": "/dev/ttyACM0",
                        "baud": 115200, "env": "MCD_MESHTASTIC_PORT"},
}


def usb_channels():
    return tuple(_USB_DEFAULTS)


def usb_config(channel):
    """Return {name, port, baud} for a channel (the port can be overridden from the environment)."""
    if channel not in _USB_DEFAULTS:
        raise ValueError("invalid USB channel: %r" % (channel,))
    cfg = dict(_USB_DEFAULTS[channel])
    cfg["port"] = os.environ.get(cfg.pop("env"), cfg["port"])
    return cfg


# ------------------------------------------------------------ pin mapping table
# Format required by L4: Pin | Signal type | Signal name | Definition
# Types: DOP = digital output, DIP = digital input, COM = communication,
#        PWR = power supply
PIN_TABLE = [
    {"pin": "GPIO17 (pin 11)", "signal_type": "DOP", "signal_name": "BUZZER",
     "definition": "Audible alert: 1 kOhm resistor, NPN transistor base, "
                   "buzzer between 5 V and collector, protection diode"},
    {"pin": "GPIO27 (pin 13)", "signal_type": "DOP", "signal_name": "LED",
     "definition": "Visual alert: LED with a 330 Ohm resistor to GND"},
    {"pin": "USB (powered hub)", "signal_type": "COM", "signal_name": "ZIGBEE",
     "definition": "XBee3 Zigbee through a USB adapter, /dev/ttyUSB0, 9600 baud"},
    {"pin": "USB (powered hub)", "signal_type": "COM", "signal_name": "MESHTASTIC",
     "definition": "Meshtastic (LoRa) ESP module, /dev/ttyACM0, 115200 baud"},
    {"pin": "GND (pin 6)", "signal_type": "PWR", "signal_name": "GND",
     "definition": "Common ground (Pi, LED, buzzer transistor)"},
]
