# Guition JC4827W543R

Hardware-first configuration for the Guition JC4827W543R.

This configuration includes the ESP32-S3 board setup, Wi-Fi, the GPIO1 display
backlight, the reference NV3041A display bus, and the reference XPT2046
touchscreen bus with calibration values measured from the four-corner hardware
test. The 4 MB single-app partition does not have room for dual OTA slots, so
firmware installation and updates are USB-only; native ESPHome OTA, HTTP OTA,
and browser OTA uploads are disabled.

Build from this directory with:

```bash
python3 ../../scripts/local_esphome.py esphome.yaml compile
```

The local ignored `secrets.yaml` must provide `wifi_ssid` and `wifi_password`.
Keep those values local and do not commit credentials. The repository's tracked
1Password template is `opencode.jsonc.tpl`; regenerate its ignored
`opencode.jsonc` with `/home/shahvirb/gitsource/utils/op-unpack.sh`.
