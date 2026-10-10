"""Eigener QR-Encoder: Bit für Bit gegen die Referenz-Bibliothek `qrcode` (nur Test-Abhängigkeit)."""
from __future__ import annotations

import pytest

qrcode = pytest.importorskip("qrcode")

from backend.qr_matrix import matrix, svg  # noqa: E402

SAMPLES = [
    "hydravr://pair?s=https://192.168.178.2&c=ABCD-EFGH-JKMN&p=Qq+l3uS8rWmIabcdefghijklmnopqrstuvwxyz012=",
    "hydravr://pair?s=https://hydrahive.example.home.arpa&c=ABCD-EFGH-JKMN&p=",
    "kurz",
    "x" * 120,
    "Ü-Umlaute & Sonderzeichen ✓ " * 3,
]


def _reference(text: str, mask: int):
    q = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=0, mask_pattern=mask)
    q.add_data(text.encode("utf-8"), optimize=0)
    q.make(fit=True)
    return [[1 if v else 0 for v in row] for row in q.get_matrix()]


@pytest.mark.parametrize("text", SAMPLES)
@pytest.mark.parametrize("mask", range(8))
def test_matches_reference_bit_for_bit(text, mask):
    assert matrix(text, mask=mask) == _reference(text, mask)


@pytest.mark.parametrize("text", SAMPLES)
def test_chosen_mask_is_valid_one_of_the_eight(text):
    g = matrix(text)
    assert any(g == _reference(text, m) for m in range(8))


def test_svg_is_selfcontained():
    s = svg(SAMPLES[0])
    assert s.startswith("<svg") and s.endswith("</svg>") and "<script" not in s


def test_too_long_is_rejected():
    with pytest.raises(ValueError):
        matrix("x" * 400)
