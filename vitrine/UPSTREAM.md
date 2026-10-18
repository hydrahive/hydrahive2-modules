# Vitrine — Quellen und Lizenzen

Vitrine spricht das ArtInChip-USB-Display (`33c3:0e02`) mit **eigenem Code** an. Übernommen wurde nur
Wissen über das Protokoll, kein Quelltext.

| Quelle | Lizenz | Was daraus stammt |
|---|---|---|
| [PolybiusPro/MSI-P13-Control](https://github.com/PolybiusPro/MSI-P13-Control), `docs/protocol-display.md` | GPL-3.0 | Beschreibung des Ablaufs GET_PARAMS → AUTH_DEV → AUTH_HOST → FRAME, Magic-Werte, Stückgröße |
| [hevnsnt/artinchip-linux](https://github.com/hevnsnt/artinchip-linux) | MIT | öffentlicher RSA-Schlüssel des Herstellers (`renderer/artinchip_pub.pem`, aus Artinchips `aic-render`) |
| [hevnsnt/artinchip-linux](https://github.com/hevnsnt/artinchip-linux) `evdi_wrapper.py`, `edid.py` | MIT | Vorbild für die libevdi-Anbindung per ctypes (`renderer/evdi_lib.py`) und den EDID-Aufbau (`renderer/edid.py`); eigener Code, Strukturen nach `evdi_lib.h` |
| Cooler Master, MasterFrame 360 Stage LCD | — | Geräteangaben (15,6", Treibername `AicUsbDisplayDriverV1.1.1.0`, Firmware `FW_V88.cpio`) |

Der Schlüssel ist ein **öffentlicher** Schlüssel; private Schlüssel oder Herstellerfirmware enthält Vitrine nicht.
