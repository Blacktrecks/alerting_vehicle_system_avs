# Setup Guide — Alerting Vehicle System (AVS)

How to install and run the app on **Linux**, a **Raspberry Pi 4 / Pi 5**, or **Windows**.

Needs **Python 3.10+** (tested here with Python 3.14.4). Packages: Django >=5.2 <6, pyserial, meshtastic >=2.7.5, whitenoise (`requirements.txt`).

Board wiring and radio configuration are in [docs/hardware.md](hardware.md) and the [Meshtastic setup guide](meshtastic_setup_guide.md); this file is only about getting the software running.

## 0. Same steps on every platform

1. Copy the project folder, then create a virtual environment inside it.
2. Install the requirements.
3. Copy `.env.example` to `.env` and set at least `DJANGO_SECRET_KEY`, `MESH_HMAC_KEY` (same value on every node) and `DJANGO_ALLOWED_HOSTS`.
4. Run the tests, then start the dashboard.

Without hardware the app runs in simulation (`MCD_SIMULATE=1`) — useful for a first check on any machine.

---

## 1. Linux (PC or laptop)

**Verified on this machine:** Python 3.14.4, `manage.py test` → *Ran 345 tests, OK (skipped=4)*, simulation mode.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
nano .env                       # DJANGO_SECRET_KEY, MESH_HMAC_KEY, DJANGO_ALLOWED_HOSTS

MCD_SIMULATE=1 DJANGO_DEBUG=1 python manage.py test        # all tests
MCD_SIMULATE=1 DJANGO_DEBUG=1 python manage.py runserver   # http://127.0.0.1:8000/
```

With real hardware attached (XBee adapter, Heltec V3):

- Add your user to the serial group once: `sudo usermod -aG dialout $USER`, then log out and back in.
- Ports are auto-detected through `/dev/serial/by-id` (`mcd/config.py`). If two adapters match, the app reports "ambiguous" — set `ZIGBEE_PORT` / `MESHTASTIC_PORT` in `.env` to the full by-id path.
- Run with `MCD_SIMULATE=0` and load `.env` first: `set -a; . ./.env; set +a`.

---

## 2. Raspberry Pi 4 or Pi 5 (Raspberry Pi OS)

Pi4 and Pi5 take the same steps. The one rule: **lgpio comes from apt, not pip**, so the venv must be created with `--system-site-packages`.

```bash
sudo apt update
sudo apt install python3-lgpio python3-venv git
sudo usermod -aG dialout,gpio $USER        # log out and back in afterwards

cd alerting_vehicle_system_AVS
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
pip install -r requirements-pi.txt

cp .env.example .env
nano .env                                  # DJANGO_SECRET_KEY, MESH_HMAC_KEY, DJANGO_ALLOWED_HOSTS (add the Pi's name or IP)
```

Test run with real hardware:

```bash
set -a; . ./.env; set +a
MCD_SIMULATE=0 python manage.py test                       # GPIO/radio tests need the wiring
MCD_SIMULATE=0 python manage.py runserver 0.0.0.0:8000 --noreload
```

Autostart with systemd (Linux-only, as on the Pi):

```bash
sudo ./scripts/install-service.sh            # add --kiosk for the optional full-screen browser
journalctl -u proximity -f                   # logs
```

Open `http://<pi-name-or-ip>:8000/` from a phone or laptop on the same network. The name or IP must be in `DJANGO_ALLOWED_HOSTS`, otherwise Django answers `DisallowedHost` / HTTP 400.

If the dashboard shows a `SIMULATION` badge on the Pi: `MCD_SIMULATE` is 1, lgpio is missing (venv without `--system-site-packages`), or `/dev/gpiochip*` is not readable — check the `gpio` group.

---

## 3. Windows

Windows runs the app in simulation and can talk to boards over USB serial or TCP. Three differences from Linux:

1. **No `/dev/serial/by-id`**, so auto-detection cannot run (`mcd/config.py` reads that directory). Set the COM ports explicitly in `.env`, e.g. `ZIGBEE_PORT=COM3`, `MESHTASTIC_PORT=COM4`. Check the numbers in Device Manager; install the CP210x driver for Heltec boards if the port does not appear.
2. **No lgpio**, so GPIO is always simulated on Windows (`mcd/pcs.py` falls back when lgpio or `/dev/gpiochip*` is missing). Use `MCD_SIMULATE=1`.
3. **Commands differ**: activate with `.venv\Scripts\activate`, set variables with `$env:NAME="value"` (PowerShell) or `set NAME=value` (cmd), and use PuTTY serial instead of picocom. For scanning the LAN for port 4403, nmap also exists for Windows; otherwise any LAN scanner works.

```powershell
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

copy .env.example .env
notepad .env                                   # DJANGO_SECRET_KEY, MESH_HMAC_KEY, COM ports if boards are attached

$env:MCD_SIMULATE = "1"
$env:DJANGO_DEBUG = "1"
python manage.py test
python manage.py runserver                     # http://127.0.0.1:8000/
```

The dashboard's Devices page uses `serial.tools.list_ports`, which works on Windows too, so boards appear there once the COM port is set in `.env`. There is no systemd service on Windows; start `runserver` manually or with a scheduled task.

---

## 4. What was verified and what was not

- **Verified here (Linux):** Python 3.14.4, all 345 tests pass in simulation mode (`OK (skipped=4)`), system check reports no issues.
- **Checked against the code:** `requirements.txt`, `requirements-pi.txt`, `.env.example`, `mcd/config.py` (by-id detection), `mcd/pcs.py` (lgpio fallback), `scripts/install-service.sh`.
- **Not verified by running:** the Pi and Windows steps were read from the code, not executed on a Pi or a Windows machine in this session.
