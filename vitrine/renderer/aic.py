"""ArtInChip-USB-Display (33c3:0e02): finden, authentisieren, JPEG-Bilder senden.

Eigene Umsetzung nach der öffentlichen Protokollbeschreibung (Quellen: vitrine/UPSTREAM.md):
1. GET_PARAMS: Vendor-Control-Transfer (0xC0, Request 0) → 8×uint16: ver, chip, fmt, bus, modes, Breite, Höhe, fps
2. AUTH_DEV:  Kopf + zufällige Challenge, mit dem Public Key verschlüsselt → Gerät schickt sie im Klartext zurück
3. AUTH_HOST: Kopf → Gerät schickt einen mit seinem privaten Schlüssel signierten Block → Host „entschlüsselt“ ihn
              mit dem Public Key (RSA-Rohoperation, PKCS#1 Typ 1) und schickt den Inhalt zurück
4. FRAME:     Kopf (Magic, Länge, frame_id, Format, 0, Magic) + JPEG in Stücken von höchstens 256 KiB
"""
from __future__ import annotations

import os
import struct
from pathlib import Path

import usb.core
import usb.util
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding

VENDOR, PRODUCT = 0x33C3, 0x0E02
IFACE, EP_OUT, EP_IN = 0, 0x01, 0x81
FRAME, AUTH_DEV, AUTH_HOST = 0xA1C62B01, 0xA1C62B10, 0xA1C62B11
CHUNK = 4096 * 64
_HEAD = "<IIHHII"


class DisplayError(RuntimeError):
    pass


def _public_key():
    return serialization.load_pem_public_key(Path(__file__).with_name("artinchip_pub.pem").read_bytes())


def rsa_public_decrypt(pub, block: bytes) -> bytes:
    """RSA-Rohoperation mit dem Public Key + PKCS#1-Typ-1-Padding entfernen."""
    n, e = pub.public_numbers().n, pub.public_numbers().e
    m = pow(int.from_bytes(block, "big"), e, n).to_bytes((n.bit_length() + 7) // 8, "big")
    if m[:2] != b"\x00\x01":
        raise DisplayError("Antwort des Displays hat kein gültiges PKCS#1-Typ-1-Padding")
    i = 2
    while i < len(m) and m[i] == 0xFF:
        i += 1
    if i >= len(m) or m[i] != 0:
        raise DisplayError("Antwort des Displays: Trennbyte fehlt")
    return m[i + 1:]


def find():
    return usb.core.find(idVendor=VENDOR, idProduct=PRODUCT)


class Display:
    def __init__(self, dev, width: int, height: int, fps: int):
        self.dev, self.width, self.height, self.fps = dev, width, height, fps
        self.frame_id = 0

    @classmethod
    def open(cls, dev) -> "Display":
        try:
            if dev.is_kernel_driver_active(IFACE):
                dev.detach_kernel_driver(IFACE)
        except (usb.core.USBError, NotImplementedError):
            pass
        usb.util.claim_interface(dev, IFACE)
        raw = bytes(dev.ctrl_transfer(0xC0, 0, 0, 0, 256, timeout=3000))
        w, h, fps = struct.unpack_from("<8H", raw, 0)[5:8]
        if not (w and h):
            raise DisplayError(f"Display meldet keine Größe ({w}x{h})")
        d = cls(dev, w, h, fps)
        d._authenticate()
        return d

    def _authenticate(self) -> None:
        pub = _public_key()
        challenge = os.urandom(32)
        self.dev.write(EP_OUT, struct.pack(_HEAD, AUTH_DEV, 0x100, 0, 0, 0, AUTH_DEV), timeout=3000)
        self.dev.write(EP_OUT, pub.encrypt(challenge, padding.PKCS1v15()), timeout=3000)
        if bytes(self.dev.read(EP_IN, 256, timeout=3000))[:32] != challenge:
            raise DisplayError("Display hat die Challenge nicht bestätigt")
        self.dev.write(EP_OUT, struct.pack(_HEAD, AUTH_HOST, 0x100, 0, 0, 0, AUTH_HOST), timeout=3000)
        signed = bytes(self.dev.read(EP_IN, 256, timeout=3000))
        self.dev.write(EP_OUT, rsa_public_decrypt(pub, signed), timeout=3000)

    def send_jpeg(self, jpeg: bytes) -> None:
        self.dev.write(EP_OUT, struct.pack(_HEAD, FRAME, len(jpeg), self.frame_id & 0xFFFF, 0, 0, FRAME), timeout=5000)
        for pos in range(0, len(jpeg), CHUNK):
            self.dev.write(EP_OUT, jpeg[pos:pos + CHUNK], timeout=10000)
        self.frame_id = (self.frame_id + 1) & 0xFFFF

    def close(self) -> None:
        try:
            usb.util.release_interface(self.dev, IFACE)
            usb.util.dispose_resources(self.dev)
        except (usb.core.USBError, AttributeError):
            pass
