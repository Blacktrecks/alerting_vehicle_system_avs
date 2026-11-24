# AGENTS.md: Proximity and Impact Warning System (AVS)

Read this file first. Keep changes small. If a rule here conflicts with a request, stop and ask.

## 1. Purpose and scope
University project, course "Proiectarea sistemelor incorporate" (labs L1-L5). A vehicle node on a Raspberry Pi
measures distance (ultrasonic), detects impacts (vibration), warns with a buzzer and an LED, and shares signed alerts
over Zigbee (short range) and LoRa Meshtastic (long range). **Warning only: never control brakes or engine.**

**Current graded deliverable: L5 RTE.** It consists of `rte/__init__.py`, `rte/test.py` (the lab's `unit.c`) and
`docs/rte_api.md`. Anything else is supporting code. Do not add features outside the open-work list (section 9).

Core (must stay small and clean): `mcd`, `ioc`, `sched`, `rte`, `app`, `sdc` links and packets.
Optional (frozen, fix bugs only): `sim`, `sdc/registry.py`, `web` pages other than the dashboard, kiosk scripts.

## 2. Hardware truth (this is ALL the hardware that exists)
- Raspberry Pi 5 (target) and Pi 4 (development, host `Pi4Master`). Raspberry Pi OS, Python 3.11+, GPIO through `lgpio`.
- HC-SR04: TRIG=GPIO23, ECHO=GPIO24 through a 1 kOhm + 2 kOhm divider (Pi pins are 3.3 V). VCC=5 V.
- Active buzzer on GPIO17 through an NPN transistor (1 kOhm base). On/off only. LED on GPIO27 (330 Ohm).
- Vibration modules (SW-420 type), digital: VIB1=GPIO22, optional VIB2=GPIO25, powered from 3.3 V. Count rising edges.
- Zigbee: ONE XBee3 on a USB adapter, 9600 baud, transparent mode. With one module there is no peer, so Zigbee
  receive can only be tested in simulation. Never claim a Zigbee link was verified over the air.
- LoRa Meshtastic, stock firmware, no custom firmware: Heltec V3 = the Pi's modem (USB serial); Heltec e-ink and Seeed
  XIAO = simulated remote vehicles V2 and V3. Write "LoRa Meshtastic", never "LoRaWAN".
- NOT present: GPS, MPU6050 or any I2C sensor. No code, docs or UI for them.
- Serial names are unstable: identify devices through `/dev/serial/by-id/*`, overrides `ZIGBEE_PORT`, `MESHTASTIC_PORT`.
- Anything simulated must be labelled `SIMULATED` in logs, API and UI.

## 3. Language
English only: code, comments, docstrings, commits, logs, UI text, API fields, docs.

## 4. Architecture
```
web -> app -> rte -> ioc / sdc / sched -> mcd          sim -> rte, sdc
```
| Layer | Role | May import |
| --- | --- | --- |
| `mcd` | drivers: `pcs` GPIO, `ultrasonic`, `usb`, `tim`, `config` | nothing from the project, no Django |
| `ioc` | logical channels to drivers | `mcd` |
| `sched` | 100 ms / 1 s / 60 s ticks | `mcd` |
| `sdc` | packets, transports, Meshtastic and Zigbee links | `mcd`, pyserial, meshtastic |
| `rte` | the ONLY door from `app` to the BSW, plus signals between app modules | `ioc`, `sdc`, `sched` |
| `app` | pure logic: `prx`, `imp`, `alr`, `rpt`, `node` | `rte`, stdlib |
| `sim` | scripted remote vehicles, device manager | `rte`, `sdc` |
| `web` | Django dashboard and API | `rte`, `app`, `sim` |
Nothing imports upward. `tests/test_layers.py` enforces this with `ast`; never weaken it.
Threading: ONE runtime thread (`app/node.py`, 100 ms step) touches hardware. Web views only read signals or enqueue
a request. Shared state is lock protected.

## 5. RTE contract (lab L5)
26 functions in `rte/__init__.py`, documented one table each in `docs/rte_api.md`:
Name | Description | Parameters (name, type, description, interval) | Return value | Reentrant (Yes/No).
- Naming: `RTE_vSetX(u8Value)`, `RTE_u8GetX()`, `RTE_u16GetX()`, `RTE_tGetX()`. Prefix `v` void, `u8`/`u16` unsigned,
  `b` bool, `t` dict or tuple.
- Binary values are real ints 0 or 1 (reject bool, float, None, str, 2, -1). Invalid parameters are IGNORED: no change,
  no exception. Setters and signal writers return nothing.
- Adding, renaming or removing an RTE function means updating, in the same commit: the code, its table in
  `docs/rte_api.md`, the function count in that file, and a test in `rte/test.py`.
- `DocumentationTests` in `rte/test.py` fails if docs and code disagree. Keep it.
- Simulation hooks for `web` and `sim` live in `rte/sim_support.py` and never start with `RTE_`.

## 6. Code conventions
- Keep existing MCD names (`PCS_vSetOutputGpio`, `USB_u16Write`, `TIM_bHasElapsed`, ...). Adding functions is allowed.
- Constants (thresholds, periods, pins) live in one place per module. No magic numbers in logic.
- A change in behaviour needs a test that fails before and passes after. Never weaken or delete a test to get green.
  No vacuous assertions (`assertTrue(True)`).
- Safety: buzzer and LED are forced off on shutdown, on runtime stop and after any step error.
- Security: key from `MESH_HMAC_KEY` (dev default must log a warning). No secrets, hard-coded hosts or IPs in git.
- No dummy data in production code paths. Generated files (`data/`, `logs/`, `reports/`, `staticfiles/`, `.venv/`) are
  git-ignored. Never commit or zip `.venv`.

## 7. Commands
```
MCD_SIMULATE=1 python -m mcd.test
MCD_SIMULATE=1 python -m rte.test                       # L5 unit test
MCD_SIMULATE=1 DJANGO_DEBUG=1 python manage.py test     # everything (345 tests, 4 hardware tests skipped)
MCD_HW_TESTS=1 MCD_SIMULATE=0 python -m mcd.test        # on the Pi only, with the wiring connected
```

## 8. Raspberry Pi 5 bring-up (acceptance order; stop at the first failure)
1. `sudo apt install python3-lgpio python3-venv`; venv with `--system-site-packages`; user in groups `dialout`, `gpio`.
2. `gpiodetect`: note which chip is `pinctrl-rp1`. Run
   `python -c "from mcd import pcs; print(pcs._resolve_gpiochip())"` and compare. Set `MCD_GPIOCHIP` if they differ.
3. Buzzer and LED pulse test (`MCD_HW_TESTS=1`), then the vibration edge test (tap the sensor).
4. Ultrasonic: 20 reads at a known distance (for example 50 cm, 100 cm). Record the spread; valid if within +-2 cm
   after the PRX debounce. Check the ECHO divider with a multimeter before connecting.
5. Meshtastic: Heltec V3 on USB, send a test text, then receive a scripted alert from V2 or V3.
6. Zigbee: only check that the serial port answers (`+++` then `OK`, `ATVR`). Report it as "serial verified, radio link
   not verified" unless a second XBee exists.
7. `sudo ./scripts/install-service.sh`; reboot; confirm buzzer and LED are off at boot and after `systemctl stop`.

## 9. Open work (verified in the code; do in this order, one commit each, with tests)
1. **Replay guard after a sender reboot** (`sdc/packets.py`, `sdc/alert_link.py`). The sequence restarts at 0, so a
   receiver that saw seq 100 rejects the first ~100 packets of the rebooted sender (checked: 0 of 100 accepted).
   Add a resync rule (for example: after 3 consecutive rejected packets from one node whose sequence numbers increase,
   accept and reset the guard) or a boot counter in the packet. Keep the 14-byte format unless a packet-format change
   is documented in `docs/architecture.md` and tested.
2. **GPIO chip detection on the Pi 5** (`mcd/pcs.py: _read_chip_label`). The parser takes the first string in what
   `lgpio.gpio_get_chip_info` returns; if that tuple is `(status, lines, name, label)` it returns the NAME, no chip
   matches `pinctrl-rp1`, and the code falls back to the first chip. Read the label explicitly (last string of the
   tuple, or `/sys/class/gpio/gpiochipN/label` first), close the handle that `gpiochip_open` returns, and add a test with
   both tuple orders. Confirm on the real Pi (section 8, step 2).
3. **Ultrasonic timing** (`mcd/ultrasonic.py`). The echo is timed by polling from Python; one GIL switch (5 ms) during
   a read is an error of tens of cm. Preferred: claim ECHO as an alert on both edges and use the kernel timestamps from
   the lgpio callback. Minimum: median of 3 reads per step. Keep the simulation path and the existing tests.
4. **Radio connect on start-up** (`rte.RTE_vInit`, `web/apps.py`). `SerialInterface` can block for seconds while Django
   starts. Connect with a timeout or in the runtime thread; the dashboard must show "connecting".
5. **Hardware doc fixes** (`docs/hardware.md`): add a 10 kOhm pull-down on the buzzer transistor base (pin state is
   undefined if the process dies); say that XBee USB adapters with CP210x or CH340 chips are classified as Meshtastic by
   `config.py`, so `ZIGBEE_PORT` must be set; note SW-420 polarity differs between modules (the code counts rising edges).
6. **Repo hygiene**: add `docs/Meshtastic_Setup_Guide.docx` to git or ignore it; keep the zip for submission free of
   `.venv`.
Do NOT start new features (maps, GPS, more pages, more device types) before 1-3 are done.

## 10. Rules for the agent
- Work on the current branch. One small commit per open-work item, message `fix(layer): ...` or `docs: ...`.
- Open only the files named in the task. Do not print whole large files or the whole repo.
- If a test fails twice, stop and report the failing output instead of looping.
- Do not claim a hardware behaviour is working unless a hardware test or a measurement on the Pi proves it; say
  "simulated" or "not verified" instead.
- Final reply of each task: at most 15 lines: what changed, test command and result, open issues. Do not paste files.