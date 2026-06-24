# Brettspiele — Modul für rundenbasierte Brettspiele

Status: **Runde 1 umgesetzt** (2026-06-24) · Schach mit Hotseat + lokaler KI

## Was
Eigenes Modul für rundenbasierte Brettspiele (Schach zuerst, später Dame, Mühle,
Vier gewinnt, Reversi …). Anders als das Echtzeit-Arcade-Modul „minigames":
klickbares Brett statt Pixel-Canvas, mehrere Spielmodi, kein Punkte-Score sondern
Sieg/Niederlage/Remis. Zwei Einstiege: Brettspiele-Tab + Buddy-Box. Spiel öffnet
als Vollbild-Overlay.

## Warum
Schach lag bereits als getestete Engine im ProjectX-Projekt vor (reines JS). Statt
neu zu schreiben → nach TypeScript portiert (verifiziert: 15/15 Engine-Tests). Das
Modul ist erweiterbar wie minigames: neues Spiel = eigene Komponente + Registry-
Eintrag + Backend-Whitelist.

## Architektur
- **Registry-Pattern**: `BoardGameModule {meta, component}`. Jedes Spiel bringt
  seine eigene React-Komponente mit (Brettspiele sind untereinander zu verschieden
  für frühe harte Abstraktion). Geteilt: Overlay-Host, Spielauswahl, Ergebnis-Store.
- **Overlay** (Portal, ESC schließt) — wie minigames, da Buddy-Widgets nur in
  schmaler Sidebar gerendert werden.

### Schach
- **Engine** (Port aus ProjectX): `engine_types.ts` (Typen/Konstanten/START),
  `movegen.ts` (Angriff + pseudo-legale Züge), `engine.ts` (make/unmake, legalMoves,
  outcome). Voll: Rochade, En-Passant, Promotion, Schach/Matt/Patt, Fesselung.
- **KI** `minimax.ts`: Minimax + Alpha-Beta, Material + Piece-Square-Tables, Tiefe 3.
  Spielt vernünftig (findet Matt in 1, schlägt hängende Figuren), kein Stockfish.
- **UI** `ChessGame.tsx` + `useChessGame.ts`: Modus-Wahl, klickbares 8×8-Brett,
  legale Zielfelder markiert, letzter Zug hervorgehoben. Engine ist Regel-Autorität.

### Spielmodi
- **Hotseat** — zwei Menschen am Gerät (zählt nicht in die Bilanz)
- **vs. Computer** — lokale Minimax-KI (Mensch Weiß, KI Schwarz); Ergebnis wird gemeldet
- **vs. LLM** — Modus reserviert (Whitelist kennt „llm"), Implementierung in Runde 2

## Backend (Ergebnisse statt Score)
- Tabelle `module_boardgames_results (user, game_id, mode, result, opponent, created_at)`
- `POST /results` {game_id, mode, result, opponent} — Whitelist-validiert
- `GET /results/mine?game_id=&mode=` — eigene W/L/D-Bilanz
- `GET /results/leaderboard?game_id=` — meiste Siege je User, global
- Auth: `require_auth`, tuple[0] = Username (für Bestenliste)

## Akzeptanzkriterien
- [x] Schach spielbar: Hotseat + vs. KI, klickbares Brett, legale Züge markiert
- [x] Engine korrekt (15/15 Port-Tests: Eröffnung, Matt, Rochade, En-Passant, Promo, Patt, Fesselung)
- [x] KI spielt sinnvoll (Matt-in-1, schlägt hängende Figuren, immer legal)
- [x] Ergebnis vs. KI server-seitig gespeichert, Bilanz abrufbar
- [x] Globale Bestenliste (meiste Siege)
- [x] Overlay öffnet/schließt (ESC), 11 Backend-Tests grün
- [x] Echter Frontend-Build grün, alle Dateien ≤200 Z.
- [x] hub.json-Eintrag vorhanden

## Lieferung in Runden
1. **Diese Runde:** Modul + Schach (Hotseat + lokale Minimax-KI) + Ergebnis-Backend.
2. (geplant) **LLM-Gegner**: Modell-Auswahl via `/api/llm/catalog`, Backend-Route
   `POST /chess/ai-move` ruft `hydrahive.llm.client.complete()`, Engine validiert
   den LLM-Zug (Retry + Minimax-Fallback bei illegal). Modus „llm" ist vorbereitet.
3. (später) Weitere Brettspiele: Dame, Vier gewinnt, Mühle, Reversi.
