# Atelier — Media-Modell-Referenz (OpenRouter)

> Live gegen die OpenRouter-APIs geprüft am **2026-07-08**. OpenRouter listet
> ständig neue Modelle / ändert Parameter — diese Tabelle ist eine Momentaufnahme,
> keine feste Wahrheit. Vor größeren Entscheidungen live nachschlagen:
> - Video: `GET https://openrouter.ai/api/v1/videos/models`
> - Bild: `GET https://openrouter.ai/api/v1/images/models`
> - Sprache (TTS): `GET https://openrouter.ai/api/v1/models?output_modalities=speech`
> - Musik/Audio: `GET https://openrouter.ai/api/v1/models?output_modalities=audio`
> - Transkription: `GET https://openrouter.ai/api/v1/models?input_modalities=audio`
>
> Im Code zentral gebündelt: `core/src/hydrahive/llm/media_models.py`
> (`list_video_models`, `list_image_models`, `list_speech_models`,
> `list_audio_models`, `list_transcribe_models`, je 5-Min-Cache).

## Wie die Tabellen zu lesen sind

- **Input** = was man dem Modell zusätzlich zum Text-Prompt mitgeben kann
  (Referenzbilder, Start-/Endframe, Video/Audio als Referenz).
- **Frame-Control** (nur Video) = `first_frame` (Startbild), `last_frame`
  (Endbild — "von diesem Bild zu jenem Bild"), oder beides.
- **Seed** = deterministische Wiederholbarkeit (gleicher Seed + Prompt →
  ähnliches Ergebnis). Nicht alle Modelle unterstützen das.
- **Preis** ist der von OpenRouter gemeldete SKU-Preis, keine Garantie —
  Stand der Abfrage.

---

## 1. Video-Generierung (`POST /api/v1/images` … nein: `/api/v1/videos`)

Endpoint: `POST https://openrouter.ai/api/v1/videos`
Request-Felder: `model`, `prompt`, `duration`, `aspect_ratio`,
`frame_images: [{type:"image_url", image_url:{url}, frame_type: "first_frame"|"last_frame"}]`,
optional `seed`.
Async: submit → `GET /api/v1/videos/{id}` pollen bis `status=completed` → `url`.

| Modell (id) | Anbieter | Input-Frames | Referenz-Bilder | Dauer (s) | Auflösung | Seitenverhältnisse | Audio | Seed | Preis/Sek (720p) | Bemerkung |
|---|---|---|---|---|---|---|---|---|---|---|
| `google/veo-3.1` | Google | first + **last** | – | 4/6/8 | bis **4K** | 16:9, 9:16 | ✅ nativ synchron | ✅ | $0,20–0,40 | Top-Qualität, teuer |
| `google/veo-3.1-fast` | Google | first + **last** | – | 4/6/8 | bis 4K | 16:9, 9:16 | ✅ | ✅ | $0,03–0,10 | guter Kompromiss |
| `google/veo-3.1-lite` | Google | first + **last** | – | 4/6/8 | 720p/1080p | 16:9, 9:16 | ✅ | ✅ | $0,03–0,05 | günstigster Veo |
| `kwaivgi/kling-v3.0-pro` | Kuaishou | first + **last** | – | 3–15 | 720p | 16:9, 9:16, 1:1 | ✅ optional | – | $0,112 (+$0,056 mit Audio) | passthrough: negative_prompt, cfg_scale |
| `kwaivgi/kling-v3.0-std` | Kuaishou | first + **last** | – | 3–15 | 720p | 16:9, 9:16, 1:1 | ✅ optional | – | $0,084 | Preis/Leistung — **unser Party/Freund-Default in `_MODEL_DURATIONS`** |
| `kwaivgi/kling-video-o1` | Kuaishou | first + **last** | – | 5/10 | 720p | 16:9, 9:16, 1:1 | ✅ | – | $0,112 | für kinoartige Shots |
| `bytedance/seedance-2.0` | ByteDance | first + **last** | ✅ **multi-ref-to-video** | 4–15 | bis **4K** | 7 Ratios (inkl. 21:9) | ✅ | ✅ | ~$0,007/Token | stark bei Charakter-Konsistenz |
| `bytedance/seedance-2.0-fast` | ByteDance | first + **last** | ✅ multi-ref | 4–15 | 480p/720p | 7 Ratios | ✅ | ✅ | ~$0,0056/Token | schnell+günstig, **aktuell im Atelier-Code** (`video.py`) |
| `bytedance/seedance-1-5-pro` | ByteDance | first + **last** | – | 4–12 | bis 1080p | 7 Ratios | ✅ **Video+Audio in einem Pass** | ✅ | günstig (Token-basiert) | Lippen-Sync-tauglich (Dual-Branch) |
| `alibaba/wan-2.7` | Alibaba | first + **last** | ✅ **reference-to-video** (Stil/Inhalt) | 2–10 | 720p/1080p | 16:9,9:16,1:1,4:3,3:4 | ✅ | ✅ | $0,10 | einziges mit `last_image`-Passthrough + Referenz-Video |
| `alibaba/wan-2.6` | Alibaba | nur first | – | 5/10 | 720p/1080p | 16:9, 9:16 | ✅ | ✅ | $0,04–0,15 | 10+ "visual capabilities" laut Anbieter |
| `alibaba/happyhorse-1.0` / `-1.1` | Alibaba | nur first | ✅ Referenzbild-**Set** | 3–15 | 720p/1080p | 7 Ratios | – | ✅ | $0,099–0,169 | reines Referenz-Set statt first/last |
| `minimax/hailuo-2.3` | MiniMax | nur first | – | 6/10 | 1080p | 16:9 | ❌ | – | $0,082 | **aktueller Core-Tool-Default** (`generate_video`) |
| `x-ai/grok-imagine-video` | xAI | nur first | ✅ reference-conditioned | 1–15 | 480p/720p | 7 Ratios | ❌ | – | $0,05–0,07 | schnell, günstig |
| `openai/sora-2-pro` | OpenAI | **kein Bild-Input** (nur Text) | – | 4/8/12/16/20 | bis 1080p | 16:9, 9:16 | ✅ | – | $0,30–0,50 | Multi-Shot-Kohärenz, aber **kein Image-to-Video** → für Keyframe-Pipeline ungeeignet |

**Für den Regie-/Shot-Flow relevant:**
- Modelle mit **first+last frame**: Veo 3.1(+Fast/Lite), Kling v3.0(Pro/Std), Kling O1, Seedance 2.0(+Fast+1.5-Pro), Wan 2.7 → hier lässt sich "Start bei Bild A, Ende bei Bild B" direkt umsetzen.
- Modelle mit **Multi-Referenz-Steuerung** (nicht nur Start/Ende, sondern laufende Stil-/Charakter-Referenz während der ganzen Clip-Generierung): Seedance 2.0(+Fast), Wan 2.7, HappyHorse, Grok Imagine Video.
- Modelle mit **nativer Audio-Generierung** (Ambience/Musik/teils Lippen-Sync direkt im Video, kein separates TTS nötig): Veo 3.1-Familie, Kling v3.0, Seedance 2.0/1.5-Pro, Wan 2.6/2.7, Sora 2 Pro.

---

## 2. Bild-Generierung (`POST /api/v1/images`)

Endpoint: `POST https://openrouter.ai/api/v1/images`
Request-Felder: `model`, `prompt`, `aspect_ratio`,
`input_references: [{type:"image_url", image_url:{url}}]`, optional `seed`.
Response: `data:[{b64_json}]`.

| Modell (id) | Anbieter | Max. Referenzbilder | Max. Auflösung | Seitenverhältnisse | Seed | Sonstige Parameter |
|---|---|---|---|---|---|---|
| `openai/gpt-image-1` | OpenAI | **16** | — | frei | – | quality, background (inkl. **transparent**), n bis 10 |
| `openai/gpt-image-1-mini` | OpenAI | 16 | — | frei | – | wie gpt-image-1, günstiger |
| `openai/gpt-image-2` | OpenAI | 16 | — | frei | – | quality, background (opaque only), n bis 10 |
| `openai/gpt-5-image` | OpenAI | 16 | — | frei | – | LLM+Image kombiniert, quality/background |
| `openai/gpt-5-image-mini` | OpenAI | **16** | — | frei | – | **unser Default** (`DEFAULTS["image"]`) |
| `openai/gpt-5.4-image-2` | OpenAI | 16 | — | frei | – | neuestes GPT-Image |
| `google/gemini-3-pro-image(-preview)` "Nano Banana Pro" | Google | 14 | bis **4K** | 10 Ratios | – | resolution 1K/2K/4K |
| `google/gemini-3.1-flash-image(-preview)` "Nano Banana 2" | Google | 14 | bis 4K | 14 Ratios | – | resolution inkl. 512px |
| `google/gemini-3.1-flash-lite-image` "Nano Banana 2 Lite" | Google | 14 | 1K | 14 Ratios | – | schnellste/günstigste Nano-Banana-Variante |
| `google/gemini-2.5-flash-image` "Nano Banana" | Google | 3 | — | 9 Ratios | – | Vorgänger-Generation |
| `bytedance-seed/seedream-4.5` | ByteDance | 14 | bis 4K | 17 Ratios | ✅ | n bis 10 — **Seed-fähig!** |
| `sourceful/riverflow-v2.5-pro` | Sourceful | 10 | bis 4K | — | – | output_format png/jpeg/webp, background transparent |
| `sourceful/riverflow-v2.5-fast` | Sourceful | 4 | bis 2K | — | – | schneller, jpeg only |
| `sourceful/riverflow-v2-pro` | Sourceful | 10 | bis 4K | — | – | Vorgänger |
| `sourceful/riverflow-v2-fast` | Sourceful | 4 | bis 4K | — | – | |
| `black-forest-labs/flux.2-max` | BFL | 8 | — | — | ✅ | output_format png/jpeg — **Seed-fähig** |
| `black-forest-labs/flux.2-pro` | BFL | 8 | — | — | ✅ | starke Prompt-Adherenz, stabile Beleuchtung |
| `black-forest-labs/flux.2-flex` | BFL | 8 | — | — | ✅ | gut bei Text/Typografie im Bild |
| `black-forest-labs/flux.2-klein-4b` | BFL | 4 | — | — | ✅ | günstigstes FLUX.2 |
| `microsoft/mai-image-2.5` | Microsoft | 1 | — | 7 Ratios + auto | – | Azure AI Foundry |
| `x-ai/grok-imagine-image-quality` | xAI | 3 | 1K/2K | 13 Ratios | – | photorealistisch |
| `recraft/recraft-v4(.1)(-pro)` | Recraft | 1 | ~1–2K | frei | – | n bis 6, auch Vektor-Varianten (SVG-Output) |
| `recraft/*-vector` | Recraft | 1 | — | frei | – | **SVG statt Raster** |

**Seed-fähige Bildmodelle** (für reproduzierbare Serien): `seedream-4.5`,
`flux.2-max/pro/flex/klein-4b`. Alle anderen (inkl. unser Default
`gpt-5-image-mini`) **ignorieren** einen mitgeschickten Seed.

**Meiste Referenzbilder** (für Multi-Charakter-Szenen / Konsistenz über viele
Anker): GPT-Image-Familie und GPT-5-Image-Familie mit **16**, dicht gefolgt von
Nano-Banana-Familie und Seedream 4.5 mit **14**.

---

## 3. Musik-Generierung (Core-Tool `generate_music`, kein eigener Atelier-Client)

Modalität `output_modalities=audio` im normalen Chat-Katalog (kein eigener
Endpoint wie Video/Bild) — läuft über den normalen `/chat/completions`-Pfad.

| Modell (id) | Anbieter | Was | Input | Preis | Bemerkung |
|---|---|---|---|---|---|
| `google/lyria-3-pro-preview` | Google | volle Songs | Text (+Image möglich) | $0,08/Song | **unser Default** (`DEFAULTS["music"]`), 48kHz |
| `google/lyria-3-clip-preview` | Google | 30s-Clips | Text (+Image) | $0,04/Clip | kurze Untermalungen, Sound-Design |
| `openai/gpt-audio` | OpenAI | Konversations-Audio (kein reines Musik-Modell) | Text+Audio | $0,0000025–0,000032/Tok | eher Voice-Chat als Musikgenerierung |
| `openai/gpt-audio-mini` | OpenAI | wie gpt-audio, günstiger | Text+Audio | ~4x günstiger | dito |

→ Für Szenen-Musik im Regie-Flow ist **Lyria 3** (Pro für den fertigen Song,
Clip für kurze Untermalung) die einzig sinnvolle Wahl auf OpenRouter aktuell.

---

## 4. Sprache / TTS (Core-Tool `generate_speech`, eigene Fläche `/models?output_modalities=speech`)

| Modell (id) | Anbieter | Sprachen | # Voices | Emotion/Style | Preis (Text-Input) | Bemerkung |
|---|---|---|---|---|---|---|
| `google/gemini-3.1-flash-tts-preview` | Google | multi | **30** | – | $0,000001/Tok | größte Stimmauswahl |
| `hexgrad/kokoro-82m` | hexgrad (open) | 8 Sprachen | **54** (af/am/bf/bm/… Präfixe) | – | $0,00000062/Tok | **unser Default** (`DEFAULTS["tts"]`), sehr günstig, offen |
| `mistralai/voxtral-mini-tts-2603` | Mistral | en/gb/fr | 30 (mit **Emotions-Tags** wie `en_paul_angry`) | ✅ explizit in Voice-Namen kodiert | $0,000016/Tok | **Emotion direkt wählbar** — interessant für Dialogzeilen mit `emotion`-Feld in `scene.dialogues` |
| `x-ai/grok-voice-tts-1.0` | xAI | 20+ | 5 (Eve, Ara, Rex, Sal, Leo) | – | $0,000015/Tok | Auto-Language-Detection |
| `microsoft/mai-voice-2` | Microsoft | 10+ | 4 | ✅ SSML-Styles (cheerful/sad/excited) | $0,000022/Tok | Azure AI Speech, SSML-Kontrolle |
| `zyphra/zonos-v0.1-hybrid` / `-transformer` | Zyphra | en (US/GB) | 5 | – | $0,000007/Tok | |
| `sesame/csm-1b` | Sesame | en | 7 | – | $0,000007/Tok | conversational vs. read-speech Styles |
| `canopylabs/orpheus-3b-0.1-ft` | Canopy Labs | en | 7 | – | $0,000007/Tok | Narration-fokussiert |

**Für Dialog-Voiceover (SPEC-REGIE E6)**: `voxtral-mini-tts` (Emotion direkt in
der Voice kodierbar, passt zu `dialogues[].emotion`) oder `mai-voice-2`
(SSML-Styles) sind die einzigen mit **explizit steuerbarer Emotion** — alle
anderen liefern nur neutrale Prosodie unabhängig vom Text.

---

## 5. Transkription (Whisper-Familie, für spätere Untertitel-Extraktion)

| Modell (id) | Bemerkung |
|---|---|
| `openai/whisper-large-v3` | **unser Default** (`DEFAULTS["transcribe"]`), bestes offenes Modell |
| `openai/whisper-large-v3-turbo` | schneller, etwas weniger genau |
| `openai/whisper-1` | älteste Variante |

---

## 6. Kombinations-Strategien für den Regie-Flow

### A) Aktueller Stand im Atelier-Code (was schon läuft)
- **Bild**: `generate.py` → `input_references` (mehrere Hero-Shots je Figur) + `seed` falls Modell es kann. Voll umgesetzt.
- **Video**: `video.py` → schickt **nur `first_frame`**. `last_frame` und Multi-Referenz-Video werden von der API bereits angeboten, aber vom Code noch **nicht** genutzt (= offener Task `0b8b5fb4`).
- **Musik**: Core-Tool `generate_music`, im Atelier über `music.py`/`audio_routes.py` angebunden.
- **TTS**: noch nicht im Regie-Flow verdrahtet (E6 offen).

### B) Empfohlene Kombination für maximale Charakter-Konsistenz über einen ganzen Film
1. **Hero-Referenzbild** einer Figur einmal mit einem 16-Ref-fähigen Bildmodell
   (gpt-5-image-mini/gpt-image-1, Nano Banana Pro) erzeugen → als
   `character.references[]` ablegen.
2. **Keyframe je Shot**: `generate_image` mit `input_references` = Hero-Shot(s)
   der beteiligten Figuren + CI-Style-Anchor → liefert das Startbild.
3. **Video je Shot**: Modell mit **first+last frame** wählen (Kling v3.0-Std
   als Default, Seedance-2.0-Fast wenn Multi-Charakter-Referenz nötig ist).
   - `first_frame` = eigenes Keyframe aus Schritt 2.
   - `last_frame` = Keyframe des **nächsten** Shots (sofern schon generiert)
     → erzwingt nahtlosen Übergang zwischen aufeinanderfolgenden Shots, ohne
     Continue-Frame-Extraktion aus dem Video nötig zu haben.
   - Falls kein Folge-Keyframe vorliegt: nur `first_frame`, wie heute.
4. **Szenen-Musik**: `google/lyria-3-pro-preview` pro Szene (nicht pro Shot —
   ein Musikbett über mehrere Shots hinweg wirkt filmischer).
5. **Dialog-Voiceover** (E6, noch offen): `voxtral-mini-tts` mit dem
   `emotion`-Feld aus `scene.dialogues[]` auf den passenden Voice-Suffix
   gemappt (z.B. `resigniert` → `en_paul_sad`-artige Wahl je Sprache).
6. **Alternative für "alles aus einem Guss"**: bei Modellen mit **nativer
   Audio-Generierung** (Seedance 1.5 Pro, Veo 3.1, Wan 2.6/2.7) den Ton direkt
   vom Video-Modell mitgenerieren lassen (Ambience, ggf. grobe Lippen-Bewegung)
   statt separatem TTS — spart einen Schritt, aber kein exaktes Dialog-Scripting
   möglich (Modell entscheidet selbst, was es "hört").

### C) Kostenfaustregel (grobe Größenordnung pro Shot, 5s @720p)
- Günstigster Video-Pfad: Hailuo 2.3 (~$0,41) oder Seedance-2.0-Fast (~token-basiert, sehr günstig) — aber nur first_frame.
- Günstigster first+last-Pfad: Kling v3.0-Std (~$0,42/5s ohne Audio).
- Premium (Kino-Look, natives Audio, 4K): Veo 3.1 (~$1–2/5s je nach Audio/Auflösung).
- Bild-Keyframe: praktisch vernachlässigbar gegenüber Video-Kosten (Cent-Bereich).
- Musik: $0,04 (30s-Clip) bis $0,08 (voller Song) pauschal, unabhängig von Länge des Films.

---

## Offene Atelier-Tasks, die direkt auf diese Tabelle aufbauen

- **Task `0b8b5fb4`** — Start-/Endbild für Video (first_frame + last_frame):
  Backend (`video.py`, `render_clip`) + `media_models.list_video_models()` um
  `supported_frame_images` erweitern + Frontend `VideoDialog.tsx` zweites
  Bildfeld. Modell-Filterung anhand der Tabelle oben (Spalte "Input-Frames").
- **SPEC-REGIE E6** — Dialog-Voiceover: `voxtral-mini-tts` wegen
  Emotion-Mapping empfohlen statt des aktuellen TTS-Defaults `kokoro-82m`
  (keine Emotionssteuerung).
- **Multi-Referenz-Video** (Seedance/Wan/HappyHorse) als möglicher künftiger
  Konsistenz-Hebel *im Video selbst*, nicht nur im Keyframe — noch nirgends
  im Atelier-Code angebunden, aber technisch verfügbar.
