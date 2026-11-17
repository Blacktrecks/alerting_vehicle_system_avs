"""PCS driver: digital GPIO outputs/inputs (Raspberry Pi, lgpio library).

Implements PCS_vSetOutputGpio from lab L3: invalid parameters are ignored,
so a wrong command never changes the state of the outputs.
Without lgpio or without /dev/gpiochip* the driver runs in simulation.
"""
import glob
import os
import threading

from . import config

try:
    import lgpio
except ImportError:          # development PC
    lgpio = None

PCS_PIN_OFF = 0
PCS_PIN_ON = 1
PCS_PIN_INVALID = 0xFF       # value returned for an invalid pin

_lock = threading.RLock()
_initialized = False
_simulated = True
_handle = None
_direction = {}              # pin -> "out" | "in"
_level = {}                  # pin -> level (output cache / simulated values)


def _hw_available():
    return lgpio is not None and bool(glob.glob("/dev/gpiochip*"))


def _is_valid_pin(pin):
    return (isinstance(pin, int) and not isinstance(pin, bool)
            and config.PCS_PIN_MIN <= pin <= config.PCS_PIN_MAX)


def _is_valid_level(value):
    return isinstance(value, int) and value in (PCS_PIN_OFF, PCS_PIN_ON)


TARGET_GPIO_LABELS = {"pinctrl-rp1", "pinctrl-bcm2711"}


def _parse_chip_label(value):
    """Extract a chip label from the various structures returned by lgpio."""
    if value is None:
        return None
    if isinstance(value, dict):
        for key in ("label", "name", "chip_label", "chip_name"):
            entry = value.get(key)
            parsed = _parse_chip_label(entry)
            if parsed is not None:
                return parsed
        return None
    if isinstance(value, (list, tuple)):
        for entry in value:
            parsed = _parse_chip_label(entry)
            if parsed is not None:
                return parsed
        return None
    if hasattr(value, "label"):
        parsed = _parse_chip_label(getattr(value, "label"))
        if parsed is not None:
            return parsed
    if hasattr(value, "name"):
        parsed = _parse_chip_label(getattr(value, "name"))
        if parsed is not None:
            return parsed
    if isinstance(value, str):
        return value.strip().lower()
    return None


def _read_chip_label(chip_id):
    """Try to read the chip label from lgpio or from sysfs."""
    if lgpio is not None:
        for attempt in (
            lambda cid: lgpio.gpio_get_chip_info(cid),
            lambda cid: (lambda handle: lgpio.gpio_get_chip_info(handle))(lgpio.gpiochip_open(cid)),
        ):
            try:
                label = _parse_chip_label(attempt(chip_id))
                if label is not None:
                    return label
            except Exception:
                continue

    label_path = "/sys/class/gpio/gpiochip%d/label" % chip_id
    try:
        if os.path.exists(label_path):
            with open(label_path, "r", encoding="utf-8") as handle:
                return handle.read().strip().lower()
    except OSError:
        pass
    return None


def _resolve_gpiochip():
    """Return the number of the GPIO chip with the correct Pi 4/5 label."""
    env_value = os.environ.get("MCD_GPIOCHIP", "").strip()
    if env_value:
        raw = env_value.lower()
        if raw.startswith("gpiochip"):
            raw = raw.replace("gpiochip", "", 1)
        try:
            return int(raw)
        except ValueError:
            pass

    chips = []
    for path in sorted(glob.glob("/dev/gpiochip*")):
        chip_name = os.path.basename(path)
        if chip_name.startswith("gpiochip"):
            try:
                chips.append(int(chip_name.replace("gpiochip", "", 1)))
            except ValueError:
                continue

    for chip_id in chips:
        label = _read_chip_label(chip_id)
        if label in TARGET_GPIO_LABELS:
            return chip_id

    return chips[0] if chips else 4


def _open_chip():
    last = None
    candidates = []
    resolved = None
    try:
        resolved = _resolve_gpiochip()
    except Exception:
        resolved = None
    if resolved is not None:
        candidates.append(resolved)

    for path in sorted(glob.glob("/dev/gpiochip*")):
        chip_name = os.path.basename(path)
        if chip_name.startswith("gpiochip"):
            try:
                chip_id = int(chip_name.replace("gpiochip", "", 1))
            except ValueError:
                continue
            if chip_id not in candidates:
                candidates.append(chip_id)

    if not candidates:
        candidates = [4]

    seen = set()
    for chip in candidates:
        if chip in seen:
            continue
        seen.add(chip)
        try:
            return lgpio.gpiochip_open(chip)
        except Exception as exc:     # lgpio.error
            last = exc
    raise RuntimeError("cannot open gpiochip: %s" % (last,))


def _configure(pin, direction):
    """Configure the direction of a pin (called with _lock held)."""
    if _direction.get(pin) == direction:
        return
    if not _simulated:
        if pin in _direction:
            lgpio.gpio_free(_handle, pin)
        if direction == "out":
            lgpio.gpio_claim_output(_handle, pin, PCS_PIN_OFF)
        else:
            lgpio.gpio_claim_input(_handle, pin)
    _direction[pin] = direction
    if direction == "out":
        _level[pin] = PCS_PIN_OFF


def PCS_vInit():
    """Initialize the driver; the alert outputs start switched off."""
    global _initialized, _simulated, _handle
    with _lock:
        if _initialized:
            return
        _simulated = config.use_simulation(_hw_available())
        if not _simulated:
            if lgpio is None:
                raise RuntimeError("lgpio is not installed (pip install lgpio)")
            _handle = _open_chip()
        _initialized = True
        for pin in config.OUTPUT_PINS:
            _configure(pin, "out")


def PCS_vDeinit():
    """Switch the outputs off, release the pins and reset the driver state."""
    global _initialized, _simulated, _handle
    with _lock:
        if _initialized and not _simulated:
            for pin, direction in list(_direction.items()):
                if direction == "out":
                    lgpio.gpio_write(_handle, pin, PCS_PIN_OFF)
                lgpio.gpio_free(_handle, pin)
            lgpio.gpiochip_close(_handle)
        _initialized = False
        _simulated = True
        _handle = None
        _direction.clear()
        _level.clear()


def PCS_bIsSimulated():
    with _lock:
        if _initialized:
            return _simulated
        return config.use_simulation(_hw_available())


def PCS_vConfigInput(u8Pin):
    """Configure a pin as a digital input (invalid pin: ignored)."""
    if not _is_valid_pin(u8Pin):
        return
    with _lock:
        PCS_vInit()
        _configure(u8Pin, "in")


def PCS_vSetOutputGpio(u8Pin, value):
    """Set the level of an output pin. Invalid parameters are ignored."""
    if not _is_valid_pin(u8Pin) or not _is_valid_level(value):
        return
    with _lock:
        PCS_vInit()
        _configure(u8Pin, "out")
        if not _simulated:
            lgpio.gpio_write(_handle, u8Pin, int(value))
        _level[u8Pin] = int(value)


def PCS_u8GetGpio(u8Pin):
    """Read the level of a pin; PCS_PIN_INVALID (0xFF) for an invalid pin."""
    if not _is_valid_pin(u8Pin):
        return PCS_PIN_INVALID
    with _lock:
        PCS_vInit()
        if u8Pin not in _direction:
            _configure(u8Pin, "in")
        if _direction[u8Pin] == "out":
            return _level.get(u8Pin, PCS_PIN_OFF)
        if _simulated:
            return _level.get(u8Pin, PCS_PIN_OFF)
        return int(lgpio.gpio_read(_handle, u8Pin))


def PCS_vSimSetInput(u8Pin, value):
    """Simulation only: force the level of an input pin (for tests)."""
    if not _is_valid_pin(u8Pin) or not _is_valid_level(value):
        return
    with _lock:
        PCS_vInit()
        if not _simulated:
            raise RuntimeError("PCS_vSimSetInput is only available in simulation")
        if _direction.get(u8Pin) != "in":
            _configure(u8Pin, "in")
        _level[u8Pin] = int(value)
