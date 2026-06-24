# Minigames — Retro-Arcade-Modul

Status: **Genehmigt** (2026-06-24) · reines Frontend-Spiel + schlankes Highscore-Backend

## Was
Ein Modul mit selbst nachgebauten Retro-Minispielen (Snake, später Space Invaders,
Pacman …). Spiele laufen im Browser auf HTML5-Canvas. Zwei Einstiegspunkte:
- **Arcade-Tab** (eigene Modul-Seite) — Spielauswahl-Grid
- **Buddy-Box** — kleine Box im Buddy-Chat zum Schnellstart

Spiel startet als **Vollbild-Overlay** (React-Portal). Highscores werden
**server-seitig pro User** gespeichert, mit **globaler Bestenliste** über alle User.

## Warum
Spaß-Modul + Referenz, wie ein reines Frontend-Modul mit minimalem Backend
(nur Highscores) sauber ins Modul-System passt. Erweiterbar: jedes neue Spiel =
1 Datei + 1 Registry-Eintrag, ohne bestehende Spiele anzufassen.

## Nicht-Ziele
- ❌ Multiplayer / Echtzeit-Netzwerk
- ❌ Fremde Game-Engines / Lizenz-behaftete ROMs — alles selbst gebaut
- ❌ Anti-Cheat (persönliches System; Scores sind Vertrauenssache)

## Architektur

### Spiel-Vertrag (Registry-Pattern)
Jedes Spiel implementiert dieselbe Schnittstelle. Neue Spiele werden nur in
`_registry.ts` eingetragen.

```ts
export interface GameMeta {
  id: string            // "snake"
  titleKey: string      // i18n-Key
  icon: string          // lucide-Icon-Name
  accent: string        // "52 211 153" (rgb)
}

export interface GameInstance {
  start(): void
  stop(): void          // cleanup: rAF + Listener entfernen
}

export interface GameModule {
  meta: GameMeta
  // mountet das Spiel auf das Canvas; meldet Score-Änderungen via onScore
  mount(canvas: HTMLCanvasElement, opts: {
    onScore: (score: number) => void
    onGameOver: (finalScore: number) => void
  }): GameInstance
}
```

Eigene Tastatursteuerung registriert jedes Spiel selbst in `start()` und räumt
in `stop()` auf (keine Listener-Leaks beim Overlay-Schließen).

### Frontend-Dateien (≤200 Zeilen/Datei)
| Datei | Verantwortung |
|-------|---------------|
| `index.tsx` | Manifest: routes, nav, workspaceTabs, buddyWidgets, i18n |
| `ArcadeView.tsx` | Tab-Seite: Spielauswahl-Grid, öffnet Overlay |
| `components/MinigamesBuddyBox.tsx` | Buddy-Box: Spiel-Liste, öffnet Overlay |
| `components/GameOverlay.tsx` | Vollbild-Portal (fixed inset-0, ESC schließt), hostet Canvas + Score + Bestenliste |
| `components/GameCanvas.tsx` | Generischer Canvas-Wrapper: mountet GameModule, leitet Score/GameOver durch |
| `games/_registry.ts` | Liste aller GameModule |
| `games/snake.ts` | Spiel 1 (vollständig) |
| `api.ts` | submitScore, myBest, leaderboard |
| `types.ts` | Game-Vertrag + Score-Typen |

### Overlay statt Chat-Mitte (technische Begründung)
Buddy-Widgets rendert der Core **nur** in einer schmalen rechten Sidebar
(`BuddyPage.tsx`: `hidden xl:flex flex-col`, feste schmale Spalte). „In der
Chat-Mitte" hieße den Core-Chat umbauen — unerwünscht für ein Modul. Daher:
Box listet Spiele → Klick öffnet Vollbild-Overlay (Portal). Identisch von
Arcade-Tab und Buddy-Box. Mehr Platz, sauberer Fokus.

### Backend (Highscores + Bestenliste)
| Datei | Verantwortung |
|-------|---------------|
| `__init__.py` | register(ctx): score_router + Migrationen |
| `scores_store.py` | user-scoped Insert, eigene Bestleistung, globale Top-N |
| `score_routes.py` | POST /scores, GET /scores/mine, GET /scores/leaderboard |

Migration `001_scores.sql`:
```sql
CREATE TABLE IF NOT EXISTS module_minigames_scores (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    "user"     TEXT NOT NULL,
    game_id    TEXT NOT NULL,
    score      INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_minigames_scores_game
    ON module_minigames_scores(game_id, score DESC);
CREATE INDEX IF NOT EXISTS idx_minigames_scores_user
    ON module_minigames_scores("user", game_id);
```

### API
```
POST /api/modules/minigames/scores            {game_id, score} → {ok, is_personal_best}
GET  /api/modules/minigames/scores/mine?game_id=  → {best, recent:[...]}
GET  /api/modules/minigames/scores/leaderboard?game_id=&limit=10
      → [{rank, user, score, created_at}]  (Top-Score je User, absteigend)
```

Auth: `require_auth` → erster Tuple-Wert = Username (für Bestenliste).
Score-Validierung: `game_id` muss bekannt sein (Server-Whitelist), `score`
nicht-negativer Int, plausible Obergrenze (Schutz vor Müll, kein echtes Anti-Cheat).

## Spiel 1: Snake
- Raster (z.B. 24×24), Schlange wächst beim Fressen, Score = Anzahl Häppchen × 10
- Steuerung: Pfeiltasten / WASD; kein 180°-Turn
- Game-Over bei Wand/Selbstkollision → Score wird submitted, Bestenliste angezeigt
- Vollständig in `snake.ts` (passt unter 200 Z.); etabliert Registry+Canvas+Overlay+Score-Flow

## Akzeptanzkriterien
- [ ] Modul lädt: Arcade-Tab + Buddy-Box sichtbar
- [ ] Snake spielbar (Tastatur), sauberes Start/Stop ohne Listener-Leak
- [ ] Score wird server-seitig gespeichert (user-scoped)
- [ ] Eigene Bestleistung abrufbar; persönlicher Rekord erkannt
- [ ] Globale Bestenliste (Top-Score je User) korrekt sortiert
- [ ] Overlay öffnet/schließt (ESC + Button), Canvas wird sauber entladen
- [ ] Backend-Tests grün (Store + Routes, Auth, Validierung, per-User-Isolation, Leaderboard)
- [ ] TS-Typecheck sauber; alle Dateien ≤200 Z. (außer reine types.ts)
- [ ] Nur Whitelist-game_ids akzeptiert

## Lieferung in Runden
1. **Diese Runde:** Gerüst (Manifest, Backend Store/Routes/Migration, Frontend
   Registry/Canvas/Overlay/Tab/BuddyBox/i18n) + **Snake** + Tests.
2. (später) Space Invaders — neue Datei `games/invaders.ts` + Registry-Eintrag.
3. (später) Pacman — eigener Ordner (Logik/Render/Level getrennt, >200 Z.).
