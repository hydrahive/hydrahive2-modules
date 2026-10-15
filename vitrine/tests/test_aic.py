"""Display-Protokoll gegen ein Fake-Gerät (kein USB nötig)."""
from __future__ import annotations

import struct

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from renderer import aic

_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_PUB_PEM = _KEY.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)


class FakeDev:
    """Spielt das Display: GET_PARAMS, AUTH_DEV (entschlüsselt Challenge), AUTH_HOST (signierter Blob), Frames."""

    def __init__(self, w=1080, h=1920, *, wrong_echo=False):
        self.w, self.h, self.wrong_echo = w, h, wrong_echo
        self.writes: list[bytes] = []
        self._pending: list[bytes] = []
        self.host_plain = b"vitrine-host-check-0123456789abcdef"
        self.claimed = False

    # pyusb-Oberfläche, die aic nutzt
    def is_kernel_driver_active(self, iface):
        return False

    def detach_kernel_driver(self, iface):
        pass

    def ctrl_transfer(self, bm, req, val, idx, length, timeout=0):
        assert (bm, req) == (0xC0, 0)
        return bytearray(struct.pack("<8H", 5, 0x80, 16, 0, 1, self.w, self.h, 60) + bytes(length - 16))

    def write(self, ep, data, timeout=0):
        data = bytes(data)
        self.writes.append(data)
        if len(data) == 20:
            magic = struct.unpack_from("<I", data)[0]
            if magic == aic.AUTH_DEV:
                self._expect = "challenge"
            elif magic == aic.AUTH_HOST:
                sig = pow(int.from_bytes(self._pad1(self.host_plain), "big"),
                          _KEY.private_numbers().d, _KEY.public_key().public_numbers().n)
                self._pending.append(sig.to_bytes(256, "big"))
            return len(data)
        if getattr(self, "_expect", None) == "challenge":
            self._expect = None
            plain = _KEY.decrypt(data, padding.PKCS1v15())
            self._pending.append((b"x" * 32) if self.wrong_echo else plain)
        return len(data)

    def read(self, ep, size, timeout=0):
        return bytearray(self._pending.pop(0))

    @staticmethod
    def _pad1(msg: bytes) -> bytes:
        return b"\x00\x01" + b"\xff" * (256 - 3 - len(msg)) + b"\x00" + msg


@pytest.fixture(autouse=True)
def _testkey(monkeypatch):
    monkeypatch.setattr(aic, "_public_key", lambda: serialization.load_pem_public_key(_PUB_PEM))
    monkeypatch.setattr(aic.usb.util, "claim_interface", lambda dev, i: setattr(dev, "claimed", True))
    monkeypatch.setattr(aic.usb.util, "release_interface", lambda dev, i: None)


def test_oeffnen_liest_groesse_und_authentisiert():
    dev = FakeDev()
    d = aic.Display.open(dev)
    assert (d.width, d.height, d.fps) == (1080, 1920, 60)
    assert dev.claimed
    assert dev.writes[-1] == dev.host_plain           # AUTH_HOST-Antwort = entschlüsselter Blob


def test_falsches_echo_bricht_ab():
    with pytest.raises(aic.DisplayError):
        aic.Display.open(FakeDev(wrong_echo=True))


def test_frame_kopf_und_stuecke():
    dev = FakeDev()
    d = aic.Display.open(dev)
    n = len(dev.writes)
    jpeg = bytes(range(256)) * 2100                   # 537 600 Bytes → 3 Stücke à max. 256 KiB
    d.send_jpeg(jpeg)
    head, *parts = dev.writes[n:]
    assert struct.unpack("<IIHHII", head) == (aic.FRAME, len(jpeg), 0, 0, 0, aic.FRAME)
    assert [len(p) for p in parts] == [262144, 262144, len(jpeg) - 2 * 262144]
    assert b"".join(parts) == jpeg


def test_frame_id_zaehlt_und_laeuft_ueber():
    dev = FakeDev()
    d = aic.Display.open(dev)
    d.frame_id = 0xFFFF
    n = len(dev.writes)
    d.send_jpeg(b"a")
    d.send_jpeg(b"b")
    ids = [struct.unpack("<IIHHII", w)[2] for w in dev.writes[n:] if len(w) == 20]
    assert ids == [0xFFFF, 0]
    assert d.frame_id == 1, "Zähler bleibt im 16-Bit-Bereich (kein endloses Wachsen)"


def _raw_sign(block: bytes) -> bytes:
    n = _KEY.public_key().public_numbers().n
    return pow(int.from_bytes(block, "big"), _KEY.private_numbers().d, n).to_bytes(256, "big")


def test_gueltiges_padding_liefert_inhalt():
    pk = serialization.load_pem_public_key(_PUB_PEM)
    assert aic.rsa_public_decrypt(pk, _raw_sign(FakeDev._pad1(b"hallo"))) == b"hallo"


def test_falscher_padding_typ_wird_erkannt():
    """Typ 2 (Verschlüsselung) statt Typ 1 (Signatur) darf nicht als Signatur durchgehen."""
    pk = serialization.load_pem_public_key(_PUB_PEM)
    typ2 = b"\x00\x02" + b"\xff" * (256 - 3 - 5) + b"\x00" + b"hallo"   # sonst gültig – nur das Typ-Byte falsch
    with pytest.raises(aic.DisplayError):
        aic.rsa_public_decrypt(pk, _raw_sign(typ2))


def test_fehlendes_trennbyte_wird_erkannt():
    pk = serialization.load_pem_public_key(_PUB_PEM)
    with pytest.raises(aic.DisplayError):
        aic.rsa_public_decrypt(pk, _raw_sign(b"\x00\x01" + b"\xff" * 254))


def test_echter_schluessel_ist_rsa_2048():
    pem = (aic.Path(aic.__file__).with_name("artinchip_pub.pem")).read_bytes()
    k = serialization.load_pem_public_key(pem)
    assert k.key_size == 2048
