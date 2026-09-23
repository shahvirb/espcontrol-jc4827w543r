---
name: flash-displays
description: Flash EspControl display firmware from this repository using ESPHome. Use when the user invokes /flash-displays with no extra display name, or asks to flash, reflash, update, or upload firmware to all known displays in sequence, or to a specific display such as 7inch, 7-inch P4, 10inch, 10-inch V1, 10-inch V2, JC4827W543R, P4-86, 4.3-inch P4, 4-inch P4, or S3, over an explicitly supplied OTA target or USB serial device.
---

# Flash Displays

## Overview

Use the local development ESPHome configs to flash the known EspControl displays. If the user invokes `/flash-displays` with no additional display name or target, assume they mean all displays. Flash one requested display, or flash all displays in the fixed order below. Use OTA with the default hard-coded target unless the user provides a different target; use USB only when the user explicitly asks for USB.

## Device Map

| Request names | ESPHome config directory | Default OTA target |
|---|---|---|
| `7inch`, `7-inch`, `7inch P4`, `7-inch P4`, `7inch V1`, `7-inch V1`, `JC1060P470` | `devices/guition-esp32-p4-jc1060p470` | `192.168.6.102` |
| `7inch V2`, `7-inch V2`, `JC1060P470 V2` | `devices/guition-esp32-p4-jc1060p470-v2` | Ask for the target |
| `10inch`, `10-inch`, `10inch P4`, `10-inch P4`, `10inch V1`, `10-inch V1`, `JC8012P4A1` | `devices/guition-esp32-p4-jc8012p4a1` | `192.168.6.103` |
| `10inch V2`, `10-inch V2`, `JC8012P4A1 V2` | `devices/guition-esp32-p4-jc8012p4a1-v2` | Ask for the target |
| `4inch P4`, `4-inch P4`, `P4-86`, `86 Panel`, `Waveshare P4-86`, `esp32-p4-86` | `devices/esp32-p4-86` | `192.168.6.104` |
| `4.3inch P4`, `4.3-inch P4`, `P4 4.3inch`, `P4 4.3-inch`, `JC4880P443` | `devices/guition-esp32-p4-jc4880p443` | `192.168.6.101` |
| `JC4827W543R`, `JC4827`, `4.3-inch JC4827` | `devices/guition-jc4827w543r` | Ask for the target |
| `S3`, `4inch S3`, `4-inch S3`, `4848S040` | `devices/guition-esp32-s3-4848s040` | `192.168.6.105` |

Treat the JC4827W543R as distinct from the JC4880P443. The JC4827 row is the
Guition 4.3-inch ESP32-S3 panel in `devices/guition-jc4827w543r`; it has no
default OTA target, so require an explicit OTA target or USB device.

Treat the 7-inch panel at `192.168.6.102`, and an ambiguous or default `7inch` request, as V1 hardware. Always flash that panel with the V1 `JC1060P470` configuration in `devices/guition-esp32-p4-jc1060p470`; never substitute the V2 configuration because that firmware will not work on this panel. Select the V2 directory only when the user explicitly requests the 7-inch V2 panel and supplies a different OTA target or explicitly requests USB.

Treat the 10-inch panel at `192.168.6.103`, and an ambiguous or default `10inch` request, as V1 hardware. Always flash that panel with the V1 `JC8012P4A1` configuration in `devices/guition-esp32-p4-jc8012p4a1`; never substitute the V2 configuration because that firmware will not work on this panel. Select the V2 directory only when the user explicitly requests the 10-inch V2 panel and supplies a different OTA target or explicitly requests USB.

All screens can also be flashed over USB when explicitly requested. Use the selected screen's config directory and the exact local serial target supplied by the user. On Linux, common targets are `/dev/ttyACM0` and `/dev/ttyUSB0`; on macOS, common targets are `/dev/cu.usbmodem*`. Device paths are case-sensitive; `/dev/ttyACM0` is valid, while `/dev/tty/acm0` is not.

If the user says only `4inch` or `4-inch`, ask whether they mean the 4-inch P4 screen or the S3 screen.

For `/flash-displays` with no extra target, or for `all`, flash in this sequence by default over OTA using the default targets above:

1. 7-inch P4 V1.
2. 10-inch P4 V1.
3. 4-inch P4 / P4-86.
4. 4.3-inch P4.
5. S3.

The JC4827W543R is not included in the automatic `all` sequence because it
has no default OTA target. Flash it only when the user names it and supplies
an OTA target or an explicit USB device.

## YAML Selection

Use `dev.yaml` by default. If the user names another YAML file, use that file instead.

- If the user explicitly says `dev`, `dev file`, or `dev.yaml`, use `dev.yaml` instead.
- If the user gives a bare filename such as `esphome.yaml`, resolve it inside the selected display's config directory.
- If the user gives a repo-relative path such as `devices/guition-esp32-p4-jc8012p4a1/esphome.yaml`, resolve it from the repository root.
- For the 7-inch panel at `192.168.6.102`, or an ambiguous/default 7-inch request, require the selected YAML to resolve inside `devices/guition-esp32-p4-jc1060p470`, which is the V1 configuration. Allow `devices/guition-esp32-p4-jc1060p470-v2` only when the user explicitly requests V2 and supplies a different OTA target or explicitly requests USB; otherwise stop and clarify instead of flashing it.
- For the 10-inch panel at `192.168.6.103`, or an ambiguous/default 10-inch request, require the selected YAML to resolve inside `devices/guition-esp32-p4-jc8012p4a1`, which is the V1 configuration. Allow `devices/guition-esp32-p4-jc8012p4a1-v2` only when the user explicitly requests V2 and supplies a different OTA target or explicitly requests USB; otherwise stop and clarify instead of flashing it.
- Only use YAML files inside this repository. If the selected file does not exist, ask for the correct file instead of guessing.
- Use the required local secrets file described below. Do not create secret values or print, modify, copy, or commit the file contents.

## Secrets File

All development YAML files require a local `secrets.yaml` containing
`wifi_ssid` and `wifi_password`. Use the existing local file or symlink in the
selected display's config directory. Do not assume a maintainer-specific
absolute path.

Before flashing each selected display:

1. From the selected display's config directory, verify `test -f secrets.yaml`.
2. If it is missing or the symlink is broken, stop and ask the user for the approved local secrets location; do not create or guess secret values.
3. If it already exists, leave it unchanged and use it as-is. Never replace a file or symlink automatically.

Never display the secrets file, include its contents in command output, or add it to Git. The per-device `.gitignore` files exclude `secrets.yaml`.

## USB Backup Gate

Treat a USB upload with the local ESPHome `run` flow as destructive to
persistent panel state. The merged firmware image can erase the NVS range
while writing the application, even when no explicit full-erase option was
passed. On the JC4827W543R, the saved EspControl configuration and Home
Assistant API key live in that storage.

Before any USB flash:

1. Tell the user to open **Setup > Settings > Backup > Export** and save the backup file.
2. Require the user's explicit confirmation that the backup is complete before invoking ESPHome.
3. State that an upload-success result does not mean the saved app configuration survived.

After a successful USB flash, tell the user to open **Setup > Settings > Backup > Import** and select the saved file. Backups restore the panel configuration but not Wi-Fi credentials or the Home Assistant encryption key; reconnect Wi-Fi and re-pair Home Assistant when required. OTA updates normally preserve this storage and do not use this USB backup gate.

## Workflow

1. Confirm the repository state:
   - Run `git status --short --branch`.
   - Use the current checkout as the source. If it is not `main`, report the branch and do not switch branches or pull automatically; flashing a just-built fix must use the checkout the user selected.
   - If the worktree is dirty, do not revert or commit unrelated changes. Tell the user the flash will use the current local checkout as-is.
2. Resolve the requested display names from the device map. If the user invoked `/flash-displays` without naming a display, resolve it as `all`. If the request is ambiguous, ask one short clarification.
3. Resolve the YAML file from the user's request. If none is provided, use `dev.yaml`.
4. Prepare and verify the required local `secrets.yaml` symlink in each selected display's config directory by following the Secrets File section. Do not print or commit the secrets.
5. Resolve OTA targets from an explicit user-supplied target first, then from the device's default hard-coded target. If a needed OTA target is missing, ask for that target or ask whether to use USB.
6. If the user says `USB`, `over USB`, `use USB`, `local`, or similar, use USB for the selected display instead of OTA.
   - For a single display, use that display's config directory and the exact USB target.
   - For `all over USB`, flash the displays in the normal all-display sequence, but ask the user to connect the correct display before each USB flash if the connected device is not clearly identifiable.
7. For OTA targets, check reachability first with `ping -c 2 -W 1000 <target>`.
8. For USB flashing:
   - If the user supplied a target, verify that exact path exists and is readable and writable.
   - On Linux, inspect `/dev/ttyACM*` and `/dev/ttyUSB*` when no target was supplied.
   - On macOS, inspect `/dev/cu.usbmodem*` when no target was supplied.
   - If there is no clear port, ask the user to connect the display or choose the port.
9. If using USB, complete the USB Backup Gate and receive explicit backup confirmation before compiling or uploading.
10. Flash each selected display with the command below, running displays sequentially. Do not run multiple flashes in parallel.
11. After each OTA flash, ping the target again. A first ping may fail during reboot; retry once after a short delay before reporting a problem.
12. After each USB flash, report the upload result separately from configuration restoration and repeat the Backup > Import instructions.
13. Do not commit or push for flashing alone. Commit/push only if this skill or other source files were intentionally changed as part of the user request.

## Commands

Use the project wrapper so a flash always uses the ESPHome version pinned by
`.github/esphome.env`. It stops before compiling if the installed executable is
older or newer than the release version. The wrapper also builds from the local
repository checkout:

```bash
python3 scripts/local_esphome.py <yaml-file> run --device <target> --no-logs
```

Run from the appropriate config directory:

```bash
# JC4827W543R over USB on Linux; require a completed backup first
cd devices/guition-jc4827w543r
python3 ../../scripts/local_esphome.py dev.yaml run --device /dev/ttyACM0 --no-logs

# 7-inch P4 over OTA
cd /Users/jtenniswood/Git/espcontrol/devices/guition-esp32-p4-jc1060p470
python3 ../../scripts/local_esphome.py dev.yaml run --device 192.168.6.102 --no-logs

# 7-inch P4 over USB, only when explicitly requested
cd /Users/jtenniswood/Git/espcontrol/devices/guition-esp32-p4-jc1060p470
python3 ../../scripts/local_esphome.py dev.yaml run --device /dev/cu.usbmodem201301 --no-logs

# 10-inch P4 V1 over OTA
cd /Users/jtenniswood/Git/espcontrol/devices/guition-esp32-p4-jc8012p4a1
python3 ../../scripts/local_esphome.py dev.yaml run --device 192.168.6.103 --no-logs

# 10-inch P4 V1 over USB, only when explicitly requested
cd /Users/jtenniswood/Git/espcontrol/devices/guition-esp32-p4-jc8012p4a1
python3 ../../scripts/local_esphome.py dev.yaml run --device /dev/cu.usbmodem201301 --no-logs

# 4-inch P4 / P4-86 over OTA
cd /Users/jtenniswood/Git/espcontrol/devices/esp32-p4-86
python3 ../../scripts/local_esphome.py dev.yaml run --device 192.168.6.104 --no-logs

# 4-inch P4 / P4-86 over USB, only when explicitly requested
cd /Users/jtenniswood/Git/espcontrol/devices/esp32-p4-86
python3 ../../scripts/local_esphome.py dev.yaml run --device /dev/cu.usbmodem201301 --no-logs

# 4.3-inch P4 over OTA
cd /Users/jtenniswood/Git/espcontrol/devices/guition-esp32-p4-jc4880p443
python3 ../../scripts/local_esphome.py dev.yaml run --device 192.168.6.101 --no-logs

# 4.3-inch P4 over USB, only when explicitly requested
cd /Users/jtenniswood/Git/espcontrol/devices/guition-esp32-p4-jc4880p443
python3 ../../scripts/local_esphome.py dev.yaml run --device /dev/cu.usbmodem201301 --no-logs

# S3 over OTA
cd /Users/jtenniswood/Git/espcontrol/devices/guition-esp32-s3-4848s040
python3 ../../scripts/local_esphome.py dev.yaml run --device 192.168.6.105 --no-logs

# S3 over USB, only when explicitly requested
cd /Users/jtenniswood/Git/espcontrol/devices/guition-esp32-s3-4848s040
python3 ../../scripts/local_esphome.py dev.yaml run --device /dev/cu.usbmodem201301 --no-logs

```

## Reporting

Keep user updates concise:

- Say which display is currently compiling/uploading.
- Mention known ESPHome warnings only if they affect the result; framework, platform, GPIO19/GPIO20, and MIPI narrowing warnings are normally non-blocking.
- For USB, distinguish firmware upload success from app-configuration restoration; remind the user to import the backup and reconnect or re-pair services as needed.
- Final response: list each requested display as flashed successfully, or clearly identify the display that failed and the blocking symptom.
