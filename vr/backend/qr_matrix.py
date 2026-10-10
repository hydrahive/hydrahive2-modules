"""QR-Matrix aufbauen (Funktionsmuster, Daten, Maske) und als SVG ausgeben.

Codewörter/Fehlerkorrektur kommen aus ``qr.py``.
"""
from __future__ import annotations

from .qr import _ALIGN, _MASKS, _codewords, _format_bits, _version_bits, _version_for


def _base(v: int) -> tuple[list[list[int | None]], list[list[bool]]]:
    n = 17 + 4 * v
    m: list[list[int | None]] = [[None] * n for _ in range(n)]
    fixed = [[False] * n for _ in range(n)]

    def put(r: int, c: int, val: int) -> None:
        if 0 <= r < n and 0 <= c < n:
            m[r][c] = val
            fixed[r][c] = True

    for r0, c0 in ((0, 0), (0, n - 7), (n - 7, 0)):          # Finder + Trennlinie
        for dr in range(-1, 8):
            for dc in range(-1, 8):
                inside = 0 <= dr <= 6 and 0 <= dc <= 6
                ring = inside and (dr in (0, 6) or dc in (0, 6))
                core = 2 <= dr <= 4 and 2 <= dc <= 4
                put(r0 + dr, c0 + dc, 1 if (ring or core) else 0)
    for i in range(8, n - 8):                                 # Timing
        put(6, i, 1 - i % 2)
        put(i, 6, 1 - i % 2)
    pos = _ALIGN[v]
    last = pos[-1] if pos else 0
    finder_corners = {(6, 6), (6, last), (last, 6)}           # dort liegen schon Finder
    for r in pos:                                             # Ausrichtung
        for c in pos:
            if (r, c) in finder_corners:
                continue
            for dr in range(-2, 3):
                for dc in range(-2, 3):
                    put(r + dr, c + dc, 1 if max(abs(dr), abs(dc)) != 1 else 0)
    put(n - 8, 8, 1)                                          # dunkles Modul
    for i in range(9):                                        # Format-Bereiche reservieren
        if i != 6:                                            # (6,8)/(8,6) gehören zum Timing
            put(8, i, 0)
            put(i, 8, 0)
    for i in range(8):
        put(8, n - 1 - i, 0)
        put(n - 1 - i, 8, 0)
    if v >= 7:                                                # Versions-Bereiche
        for i in range(6):
            for j in range(3):
                put(i, n - 11 + j, 0)
                put(n - 11 + j, i, 0)
    return m, fixed


def _place(m, fixed, words: list[int]) -> None:
    n = len(m)
    bits = [w >> (7 - i) & 1 for w in words for i in range(8)]
    k, up, c = 0, True, n - 1
    while c > 0:
        if c == 6:
            c -= 1
        rows = range(n - 1, -1, -1) if up else range(n)
        for r in rows:
            for cc in (c, c - 1):
                if not fixed[r][cc]:
                    m[r][cc] = bits[k] if k < len(bits) else 0
                    k += 1
        up = not up
        c -= 2


def _apply(m, fixed, mask: int, v: int) -> list[list[int]]:
    n = len(m)
    out = [[(m[r][c] ^ (1 if (not fixed[r][c] and _MASKS[mask](r, c)) else 0)) for c in range(n)] for r in range(n)]
    f = _format_bits(mask)
    for i in range(15):
        bit = f >> i & 1
        # senkrecht: neben dem Finder oben links, dann unten links
        if i < 6:
            out[i][8] = bit
        elif i < 8:
            out[i + 1][8] = bit
        else:
            out[n - 15 + i][8] = bit
        # waagerecht: rechts oben, dann neben dem Finder oben links
        if i < 8:
            out[8][n - 1 - i] = bit
        elif i < 9:
            out[8][15 - i] = bit
        else:
            out[8][14 - i] = bit
    out[n - 8][8] = 1  # dunkles Modul
    if v >= 7:
        vb = _version_bits(v)
        for i in range(18):
            bit = vb >> i & 1
            out[i // 3][n - 11 + i % 3] = bit
            out[n - 11 + i % 3][i // 3] = bit
    return out


def _penalty(g: list[list[int]]) -> int:
    n, p = len(g), 0
    for lines in (g, [list(col) for col in zip(*g)]):
        for row in lines:
            run = 1
            for i in range(1, n):
                if row[i] == row[i - 1]:
                    run += 1
                else:
                    p += run - 2 if run >= 5 else 0
                    run = 1
            p += run - 2 if run >= 5 else 0
            s = "".join(map(str, row))
            p += 40 * sum(s.count(pat) for pat in ("10111010000", "00001011101"))
    for r in range(n - 1):
        for c in range(n - 1):
            if g[r][c] == g[r][c + 1] == g[r + 1][c] == g[r + 1][c + 1]:
                p += 3
    dark = sum(map(sum, g)) * 100 // (n * n)
    p += 10 * (abs(dark - 50) // 5)
    return p


def matrix(text: str, mask: int | None = None) -> list[list[int]]:
    """Fertige Modul-Matrix (1 = dunkel). [mask] nur für Tests erzwingen."""
    data = text.encode("utf-8")
    v = _version_for(len(data))
    base, fixed = _base(v)
    _place(base, fixed, _codewords(data, v))
    if mask is not None:
        return _apply(base, fixed, mask, v)
    return min((_apply(base, fixed, k, v) for k in range(8)), key=_penalty)


def svg(text: str, scale: int = 8, border: int = 4) -> str:
    """QR als eigenständiges SVG (schwarz auf weiß, ruhige Zone [border] Module)."""
    g = matrix(text)
    size = (len(g) + 2 * border) * scale
    rects = "".join(
        f'<rect x="{(c + border) * scale}" y="{(r + border) * scale}" width="{scale}" height="{scale}"/>'
        for r, row in enumerate(g) for c, val in enumerate(row) if val
    )
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" width="{size}" height="{size}">'
            f'<rect width="100%" height="100%" fill="#fff"/><g fill="#000">{rects}</g></svg>')
