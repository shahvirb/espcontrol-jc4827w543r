# Guition JC4827W543R

Minimal hardware-first configuration for display bring-up.

This configuration includes the ESP32-S3 board setup, Wi-Fi, native OTA, the
GPIO1 display backlight, the reference NV3041A display bus, and a simple LVGL
test screen. It also includes the reference XPT2046 touchscreen bus and LVGL
touch binding with calibration values measured from the four-corner hardware
test.

Build from this directory with:

```bash
python3 ../../scripts/local_esphome.py esphome.yaml compile
```

The local ignored `secrets.yaml` must provide `wifi_ssid`, `wifi_password`, and
`ota_password`. Keep those values local and do not commit credentials. The
repository's tracked 1Password template is `opencode.jsonc.tpl`; regenerate its
ignored `opencode.jsonc` with `/home/shahvirb/gitsource/utils/op-unpack.sh`.
