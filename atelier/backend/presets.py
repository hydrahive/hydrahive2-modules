"""Atelier — Regie-Presets (Cinematography).

Kuratierte Kamera-/Licht-/Wetter-Bausteine. Der User wählt im Frontend
verständliche Labels (Dropdowns); hier liegt die englische Prompt-Phrase, die
beim Generieren angehängt wird. SSOT für Backend (Prompt-Bau) und Frontend
(Dropdown-Optionen via GET /presets).

Aufbau: GROUPS[group] = { key: phrase }. ``key`` ist stabil (geht ins Sidecar),
``phrase`` ist der englische Prompt-Text, das Label kommt aus i18n im Frontend.
Reihenfolge der Gruppen = Anzeige-Reihenfolge.
"""
from __future__ import annotations

GROUPS: dict[str, dict[str, str]] = {
    "shot": {
        "extreme_closeup": "extreme close-up shot",
        "closeup": "close-up shot",
        "medium": "medium shot",
        "full": "full body shot",
        "wide": "wide establishing shot",
        "aerial": "aerial bird's-eye view",
        "low_angle": "dramatic low angle shot",
        "high_angle": "high angle shot",
        "over_shoulder": "over-the-shoulder shot",
        "dutch": "dutch angle, tilted frame",
    },
    "lens": {
        "wide_24": "shot on 24mm wide-angle lens",
        "normal_50": "shot on 50mm lens, natural perspective",
        "portrait_85": "shot on 85mm portrait lens, shallow depth of field, creamy bokeh",
        "tele_135": "shot on 135mm telephoto lens, compressed perspective",
        "macro": "macro lens, extreme detail",
        "fisheye": "fisheye lens, strong distortion",
        "anamorphic": "anamorphic lens, cinematic widescreen, lens flares",
    },
    "light": {
        "golden_hour": "golden hour lighting, warm soft sunlight",
        "soft": "soft diffused lighting",
        "rembrandt": "Rembrandt lighting, dramatic shadows",
        "backlit": "backlit, rim light, glowing edges",
        "studio": "professional studio lighting, softboxes",
        "neon": "neon lighting, vibrant colored glow",
        "hard": "hard directional light, strong contrast",
        "candle": "warm candlelight, intimate mood",
        "overcast": "flat overcast lighting",
    },
    "weather": {
        "clear": "clear sky",
        "rain": "rainy, falling raindrops, wet surfaces",
        "storm": "stormy, dramatic dark clouds, lightning",
        "snow": "snowing, soft snowflakes",
        "fog": "thick fog, misty atmosphere",
        "cloudy": "cloudy overcast sky",
        "wet_street": "wet street reflections after rain",
        "windy": "windy, motion in hair and fabric",
    },
    "time": {
        "dawn": "at dawn, first light",
        "morning": "morning light",
        "noon": "bright midday sun",
        "afternoon": "warm afternoon light",
        "dusk": "at dusk, twilight",
        "night": "at night, dark ambient",
        "blue_hour": "blue hour, deep blue twilight",
    },
    "mood": {
        "teal_orange": "cinematic teal and orange color grade",
        "warm": "warm color grade",
        "cool": "cool color grade",
        "desaturated": "desaturated, muted tones",
        "pastel": "soft pastel tones",
        "moody": "dark moody atmosphere",
        "vibrant": "vibrant saturated colors",
        "noir": "high-contrast black and white film noir",
    },
}


# Stil-Looks (Kunst-Stil der ganzen Szene). Anders als die Regie-Gruppen ist
# das EINE Auswahl, und sie kommt im Prompt VOR die Szene (durchgehender Look,
# wie ein CI-Style-Anker). key stabil (Sidecar), phrase = englischer Prompt-Text.
STYLES: dict[str, str] = {
    "photo": "photorealistic, high detail",
    "cinematic": "cinematic film still, dramatic lighting",
    "flat_vector": "clean flat vector illustration, bold outlines",
    "watercolor": "soft watercolor painting, delicate washes",
    "oil_painting": "classical oil painting, visible brushstrokes",
    "retro_anime": "retro 90s anime style, cel shaded",
    "modern_anime": "modern anime style, vibrant, detailed",
    "comic": "western comic book style, ink and halftone",
    "pixel_art": "pixel art, 16-bit retro game style",
    "3d_render": "3d render, octane, soft global illumination",
    "claymation": "claymation, handmade plasticine look",
    "pencil_sketch": "detailed pencil sketch, graphite shading",
    "vintage_tarot": "vintage tarot card art, ornate borders, muted gold",
    "low_poly": "low poly 3d, faceted geometric shapes",
    "papercut": "layered paper cut-out, soft shadows",
    "synthwave": "synthwave, neon grid, retro 80s sci-fi",
}


def phrase_for(group: str, key: str) -> str | None:
    """Englische Prompt-Phrase für eine Auswahl. None bei unbekanntem key."""
    return GROUPS.get(group, {}).get(key)


def style_phrase(key: str) -> str | None:
    """Englische Prompt-Phrase für einen Stil-Look. None bei unbekanntem key."""
    return STYLES.get(key)


def collect_phrases(selection: dict[str, str]) -> list[str]:
    """selection {group: key} → Liste der Phrasen (in GROUPS-Reihenfolge)."""
    out: list[str] = []
    for group in GROUPS:
        key = selection.get(group)
        if key:
            phrase = phrase_for(group, key)
            if phrase:
                out.append(phrase)
    return out


def catalog() -> dict[str, list[str]]:
    """{group: [keys]} für das Frontend (Labels kommen aus i18n).

    Enthält die Regie-Gruppen plus die Sondergruppe 'style' (Stil-Look, eine
    Auswahl, kommt im Prompt vor die Szene statt danach).
    """
    out = {group: list(opts.keys()) for group, opts in GROUPS.items()}
    out["style"] = list(STYLES.keys())
    return out
