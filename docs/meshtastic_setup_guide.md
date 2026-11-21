# Meshtastic Setup Guide

Raspberry Pi + Seeed XIAO ESP32-S3 + Heltec Wireless Paper

Region EU_868 · Wi-Fi/TCP control · LoRa messaging · Updated 17 November 2026

## Contents

1. [Overview](#1-overview)
2. [Preparing the Raspberry Pi](#2-preparing-the-raspberry-pi)
3. [Connecting over USB](#3-connecting-over-usb)
4. [LoRa configuration](#4-lora-configuration)
5. [Wi-Fi configuration](#5-wi-fi-configuration)
6. [Finding the boards on the network](#6-finding-the-boards-on-the-network)
7. [Sending and receiving messages](#7-sending-and-receiving-messages)
8. [Using Python](#8-using-python)
9. [Tips for reliable testing](#9-tips-for-reliable-testing)
10. [Troubleshooting](#10-troubleshooting)
11. [Quick command reference](#11-quick-command-reference)
12. [Placeholders used in this guide](#12-placeholders-used-in-this-guide)

## 1. Overview

This guide documents a working Meshtastic test setup: two LoRa boards controlled from a Raspberry Pi. It collects the configuration steps, commands, tips and troubleshooting from the build session in one place.

| Item | Role | Notes |
|---|---|---|
| Raspberry Pi 4 (Pi4Master) | Control computer | Runs the meshtastic CLI and Python scripts. Example IP: 10.33.173.229 |
| Seeed XIAO ESP32-S3 (+ LoRa) | Board A ("XIAO") | Example node ID: `!62f9fd48`. USB shows up as `/dev/ttyACM0` |
| Heltec Wireless Paper | Board B ("Paper") | USB shows up as `/dev/ttyUSB0`. Needs Wi-Fi configured |
| 2.4 GHz Wi-Fi network | Link between Pi and boards | Example SSID: Pantherion. 5 GHz-only networks will not work |

### How the pieces talk to each other

- **Wi-Fi / TCP (port 4403):** only connects your computer to each board, so the Pi can configure it and send or read messages.
- **LoRa radio:** carries the messages between the two boards. This needs no Wi-Fi and no router.
- **USB serial:** used for first-time configuration, before Wi-Fi is set up.

**Key point:** Each board accepts only one TCP connection at a time. Close the phone app, picocom and any other meshtastic session before connecting.

## 2. Preparing the Raspberry Pi

### Install the Meshtastic CLI

Use a virtual environment so the install stays separate from system Python.

```bash
python3 -m venv ~/meshtastic-venv
source ~/meshtastic-venv/bin/activate
pip install --upgrade meshtastic
meshtastic --version
```

### Install nmap

nmap is used to find the boards on your network.

```bash
sudo apt install nmap
```

### Allow serial access

If you get a permission error on `/dev/ttyACM0` or `/dev/ttyUSB0`, add your user to the `dialout` group and log in again.

```bash
sudo usermod -aG dialout $USER
# then log out and back in (or reboot)
```

## 3. Connecting over USB

Plug in one board at a time and check which device name appears.

```bash
ls /dev/ttyACM* /dev/ttyUSB*
meshtastic --port /dev/ttyACM0 --info
```

| Device | Usual board |
|---|---|
| `/dev/ttyACM0` | Seeed XIAO ESP32-S3 (native USB) |
| `/dev/ttyUSB0` | Heltec Wireless Paper (USB-serial chip) |

**Tip:** The name can change if you plug the boards in a different order. Always confirm with `--info` before changing settings. If you need a serial log, use `picocom -b 115200 /dev/ttyACM0` and exit with Ctrl+A then Ctrl+X.

## 4. LoRa configuration

Both boards must use the same region and the same channel to hear each other. For Europe use EU_868. Run this on each board over USB.

```bash
meshtastic --port /dev/ttyACM0 --set lora.region EU_868
meshtastic --port /dev/ttyUSB0 --set lora.region EU_868
```

Check the result with `--info` and make sure the channel settings match on both boards. The default public channel is fine for testing.

## 5. Wi-Fi configuration

Enable Wi-Fi on each board so the Pi can reach it over TCP. Replace the placeholders with your own values. **Never share or commit your real password.**

```bash
meshtastic --port /dev/ttyUSB0 \
  --set network.wifi_enabled true \
  --set network.wifi_ssid "<YOUR_SSID>" \
  --set network.wifi_psk "<YOUR_WIFI_PASSWORD>"
```

The output should end with "Writing modified preferences to device" and "Writing network configuration to device". The board then reboots. Wait about 20 seconds before scanning.

Repeat for the other board, changing the `--port` value.

**Common mistake:** Run the command as one line, or with the backslashes exactly as shown, and use the full device path (`/dev/ttyUSB0`, not `ttyUSB0`). If the output stops before the "network configuration" line, the Wi-Fi settings did not finish saving. Run it again.

**Wi-Fi band:** The boards support 2.4 GHz only. If your network is 5 GHz only, they cannot join it.

## 6. Finding the boards on the network

1. Get the Pi's own address.

   ```bash
   hostname -I
   # example: 10.33.173.229
   ```

2. Scan the same network for open port 4403. Use the first three numbers from the previous step.

   ```bash
   sudo nmap -p 4403 --open 10.33.173.0/24
   ```

3. You should see two hosts with port 4403 open. Note which IP belongs to which board (check with `meshtastic --host <IP> --info`).

If your network is larger than a /24 (some hotspots and campus networks), widen the scan to `10.33.0.0/16`. It takes longer.

### If only one board, or none, appears

- Confirm the second board's Wi-Fi command finished (see section 5) and wait 20 seconds after each reboot.
- Check that the network is 2.4 GHz.
- Close anything else holding the TCP connection (phone app, other CLI sessions).
- Read the IP from the serial log: open picocom on the board, press reset, and look for a line with the IP address.

## 7. Sending and receiving messages

Placeholders: `<IP_XIAO>` is board A and `<IP_PAPER>` is board B.

### Listen on board A (terminal 1)

```bash
meshtastic --host <IP_XIAO> --listen
```

### Send from board B (terminal 2)

```bash
meshtastic --host <IP_PAPER> --sendtext "hello from Paper"
```

The text goes out over LoRa and should appear in terminal 1 within a few seconds. This is a broadcast to everyone on the channel.

### Direct message to one node

```bash
meshtastic --host <IP_PAPER> --sendtext "hi XIAO" --dest '!62f9fd48'
```

### Direct message with acknowledgement

```bash
meshtastic --host <IP_PAPER> --sendtext "hi XIAO" --dest '!62f9fd48' --ack
```

With `--ack` the CLI waits and reports whether the message was delivered.

### Check that the boards hear each other

```bash
meshtastic --host <IP_XIAO> --nodes
```

Look for the other board in the list with a recent LastHeard time. If it stays N/A, the boards are not hearing each other over LoRa yet.

## 8. Using Python

Both boards can be driven from one script. Run it inside the same virtual environment as the CLI.

```python
import time
import meshtastic.tcp_interface
from pubsub import pub

def on_receive(packet, interface):
    d = packet.get("decoded", {})
    if d.get("portnum") == "TEXT_MESSAGE_APP":
        print("RX:", packet["fromId"], d["text"])

pub.subscribe(on_receive, "meshtastic.receive")

a = meshtastic.tcp_interface.TCPInterface(hostname="<IP_XIAO>")
b = meshtastic.tcp_interface.TCPInterface(hostname="<IP_PAPER>")
time.sleep(2)
b.sendText("hello from Paper", destinationId="!62f9fd48", wantAck=True)
time.sleep(10)
a.close()
b.close()
```

**Note:** Closing the interfaces at the end releases the TCP connections so the next command can connect.

## 9. Tips for reliable testing

- Keep the boards 1 to 2 metres apart. Too close and the receiver can be overloaded, so the message may not arrive.
- Attach the antenna before powering a LoRa board. Transmitting without one can damage the radio.
- Other nodes in your area (for example IDs ending `864e` or `c90b`) also receive broadcasts on the default public channel. Use `--dest` for targeted tests.
- Only one TCP client per board. Close the phone app, picocom and other sessions first.
- Wait about 20 seconds after any reboot before scanning or connecting.
- Both boards must share the same region (EU_868) and the same channel settings.

## 10. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Permission denied on `/dev/tty...` | User not in `dialout` group | `sudo usermod -aG dialout $USER`, then log in again |
| Command fails on `ttyUSB0` | Wrong device name or board unplugged | Check `ls /dev/ttyUSB* /dev/ttyACM*`, use the full path |
| nmap shows only one board | Second board's Wi-Fi not saved, or still rebooting | Re-run the Wi-Fi command on one line, wait 20 s |
| nmap shows none | Wrong subnet, or 5 GHz network | Check `hostname -I`, widen to /16, use a 2.4 GHz network |
| Connection refused / busy | Another client is connected | Close phone app and other sessions |
| Message does not arrive | Region or channel mismatch, or boards too close or too far | Set EU_868 on both, same channel, 1 to 2 m apart |
| LastHeard stays N/A | Boards not hearing each other over LoRa | Check distance, antennas, region and channel |

## 11. Quick command reference

| Command | What it does |
|---|---|
| `meshtastic --port <DEV> --info` | Show device and config info over USB |
| `meshtastic --host <IP> --info` | Show device and config info over Wi-Fi |
| `meshtastic --port <DEV> --set lora.region EU_868` | Set the radio region |
| `meshtastic --port <DEV> --set network.wifi_enabled true` | Turn Wi-Fi on |
| `... --set network.wifi_ssid "<SSID>"` | Set the Wi-Fi network name |
| `... --set network.wifi_psk "<PASSWORD>"` | Set the Wi-Fi password |
| `meshtastic --host <IP> --listen` | Print incoming messages |
| `meshtastic --host <IP> --sendtext "text"` | Broadcast a text message |
| `meshtastic --host <IP> --sendtext "text" --dest '!ID'` | Send to one node |
| `... --ack` | Wait for delivery acknowledgement |
| `meshtastic --host <IP> --nodes` | List nodes the board has heard |
| `meshtastic --host <IP> --reboot` | Reboot the board |
| `hostname -I` | Show the Pi's IP address |
| `sudo nmap -p 4403 --open <NET>/24` | Find boards with the API port open |

## 12. Placeholders used in this guide

| Placeholder | Replace with |
|---|---|
| `<IP_XIAO>` | IP address of the Seeed XIAO board (from nmap) |
| `<IP_PAPER>` | IP address of the Wireless Paper board (from nmap) |
| `<YOUR_SSID>` | Your 2.4 GHz Wi-Fi network name |
| `<YOUR_WIFI_PASSWORD>` | Your Wi-Fi password (keep it private) |
| `!62f9fd48` | The node ID of the board you are sending to (see `--nodes`) |
| `<DEV>` | `/dev/ttyACM0` or `/dev/ttyUSB0` |
