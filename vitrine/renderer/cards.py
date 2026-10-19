"""Einblendungen als Karten unten über der Status-Leiste (neueste oben), mit Ein- und Ausblenden."""
from __future__ import annotations

from PIL import Image, ImageDraw

from .scene import _font

COLORS = {"info": (105, 215, 255, 255), "success": (90, 220, 140, 255),
          "warning": (255, 200, 80, 255), "error": (255, 95, 95, 255)}
LABELS = {"info": "Info", "success": "Erledigt", "warning": "Warnung", "error": "Fehler"}
FADE = 0.4
MAX_LINES = 3
HINT = "Maus bewegen für Details"          # S3; ohne 🖱 – DejaVu hat das Zeichen nicht (Kästchen auf dem Display)
HINT_COLOR = (141, 154, 176, 255)


class Cards:
    def __init__(self, width: int, height: int):
        self.w, self.h = width, height
        u = width / 1080
        self.u = u
        self.font = _font("DejaVuSans.ttf", int(40 * u))
        self.title_font = _font("DejaVuSans-Bold.ttf", int(40 * u))
        self.margin = int(40 * u)
        self.bar = int(14 * u)
        self.pad = int(26 * u)
        self.text_width = width - 2 * self.margin - self.bar - 2 * self.pad
        self.line_h = int(52 * u)
        self.bottom = height - int(150 * u)           # oberhalb der Status-Leiste

    def wrap(self, text: str) -> list[str]:
        words, lines, cur = text.split(), [], ""
        for w in words:
            cand = f"{cur} {w}".strip()
            if self.font.getlength(cand) <= self.text_width:
                cur = cand
                continue
            if cur:
                lines.append(cur)
            cur = w
            if len(lines) == MAX_LINES:
                break
        if cur and len(lines) < MAX_LINES:
            lines.append(cur)
        if len(lines) == MAX_LINES and (len(" ".join(lines)) < len(text.strip())):
            last = lines[-1]
            while last and self.font.getlength(last + "…") > self.text_width:
                last = last[:-1]
            lines[-1] = last.rstrip() + "…"
        return lines

    def headline(self, m: dict) -> str:
        head = m.get("title") or LABELS.get(m.get("kind"), "Info")
        return f"{head}  ×{m['count']}" if m.get("count", 1) > 1 else head

    def _alpha(self, m: dict, now: float) -> float:
        a = min(1.0, max(0.0, (now - m["created"]) / FADE))
        return min(a, max(0.0, (m["expires"] - now) / FADE))

    def render(self, messages: list[dict], now: float, hint: bool = False) -> Image.Image:
        """hint: zusätzliche Zeile HINT (nur wenn die Statuszentrale bereit ist – entscheidet der Dienst)."""
        img = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
        y = self.bottom
        for m in messages:                                   # neueste zuerst → unten nach oben stapeln
            lines = self.wrap(m.get("text", ""))
            height = self.pad * 2 + self.line_h * (len(lines) + 1 + int(hint))
            a = self._alpha(m, now)
            if a <= 0:
                continue
            slide = int((1 - a) * 30 * self.u)
            top = y - height + slide
            card = Image.new("RGBA", (self.w, height), (0, 0, 0, 0))
            dr = ImageDraw.Draw(card)
            x0, x1 = self.margin, self.w - self.margin
            dr.rounded_rectangle([x0, 0, x1, height - 1], int(22 * self.u), fill=(10, 14, 24, 205))
            dr.rectangle([x0, int(10 * self.u), x0 + self.bar, height - int(10 * self.u)], fill=COLORS.get(m.get("kind"), COLORS["info"]))
            tx = x0 + self.bar + self.pad
            dr.text((tx, self.pad), self.headline(m), font=self.title_font, fill=COLORS.get(m.get("kind"), COLORS["info"]))
            for i, line in enumerate(lines):
                dr.text((tx, self.pad + self.line_h * (i + 1)), line, font=self.font, fill=(235, 240, 248, 255))
            if hint:
                dr.text((tx, self.pad + self.line_h * (len(lines) + 1)), HINT, font=self.font, fill=HINT_COLOR)
            if a < 1:
                card.putalpha(card.getchannel("A").point(lambda v: int(v * a)))
            img.alpha_composite(card, (0, max(0, top)))
            y = top - int(18 * self.u)
        return img
