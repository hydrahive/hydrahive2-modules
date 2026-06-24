# Schach Runde 2 — LLM-Gegner mit Modell-Auswahl

## Was
Ein dritter Spielmodus für Schach: **vs. LLM**. Der Spieler wählt vor der Partie
ein Sprachmodell aus dem zentralen LLM-Katalog; dieses Modell spielt Schwarz.
Jeder LLM-Zug wird gegen die Engine validiert — bei Halluzination (illegaler oder
unverständlicher Zug) greift automatisch der vorhandene Minimax-Bot als Fallback.

## Warum
Runde 1 lieferte Hotseat + Minimax-Bot. Der Modus `"llm"` ist in `types.ts` und
der Backend-Whitelist (`games.MODES`) bereits vorgesehen, aber ohne Logik. Diese
Runde füllt ihn — und zeigt HydraHives LLM-Layer spielerisch: jedes konfigurierte
Modell (Cloud wie lokal) kann antreten, ohne dass das Frontend je einen API-Key sieht.

## Wie (grob)

### Datenfluss pro LLM-Zug
1. Frontend ist am Zug für die KI (`turn === LLM_SIDE`, schwarz).
2. Frontend baut aus `legalMoves(state, turn)` eine **UCI-Liste** (`e7e5`, `g8f6`,
   `e7e8q` …) — Reihenfolge stabil, Index = Position in der Liste.
3. Frontend `POST /api/modules/boardgames/chess/llm-move`
   `{ model, fen, moves: ["e7e5", ...], history: ["e2e4", ...] }`.
4. Backend ruft `hydrahive.llm.client.complete()` mit einem **constrained Prompt**:
   "Du spielst Schwarz. Stellung (FEN): … Erlaubte Züge: … Antworte NUR mit JSON
   `{\"move\": \"<uci>\"}` aus der Liste." `temperature=0.2`, kleine `max_tokens`.
5. Backend parst robust (Vorbild `deepresearch/research/llm.py`: `<think>`-Strip,
   Fence-Strip, balanciertes JSON). Prüft, ob der Zug **in der übergebenen Liste**
   ist. Gibt `{ "move": "<uci>", "index": <n>, "source": "llm" }` zurück; wenn das
   LLM danebenliegt: `{ "move": null, "source": "invalid" }` (kein 500).
6. Frontend: ist `move` gesetzt und in der eigenen Liste → spielen. Sonst →
   `bestMove(state, AI_DEPTH)` (Minimax-Fallback) spielen. Quelle wird im UI dezent
   angezeigt ("Modell" / "Notzug").

### Warum UCI + Move-Liste statt freiem FEN-Zug
- Die Engine ist Single Source of Truth — wir lassen das LLM **aus legalen Zügen
  wählen**, nicht frei generieren. Das eliminiert die meisten Halluzinationen.
- UCI ist universell verstanden, trivial aus `Move` baubar (`sqName`+`sqName`+promo),
  kein SAN-Disambiguierungs-Code nötig.
- FEN wird **nur als Kontext** mitgeschickt (Stellung), nicht zur Zug-Rekonstruktion.

### Komponenten
| Datei | Rolle | Grenze |
|---|---|---|
| `frontend/chess/uci.ts` | `toUci(Move)`, `fenOf(State)` (nur Serialisierung) | neu, <120 Z. |
| `frontend/chess/engine_types.ts` | unverändert | — |
| `frontend/chess/useChessGame.ts` | `llm`-Zweig + Fallback, `model`-Param | erweitert |
| `frontend/chess/ChessGame.tsx` | Modell-Dropdown im `llm`-Modus | erweitert |
| `frontend/api.ts` | `llmMove()`, `listModels()` | erweitert |
| `backend/chess_llm.py` | Prompt-Bau, `complete()`, Parsing, Validierung | neu, <160 Z. |
| `backend/result_routes.py` (oder neu `chess_routes.py`) | `POST /chess/llm-move` | erweitert |
| `backend/games.py` | `"llm"` bereits in MODES — unverändert | — |

### Modell-Auswahl
- `GET /api/llm/models?modality=chat` liefert `{ default, models:[{id,label,...}] }`.
- Dropdown im `llm`-Modus, vorbelegt mit `default`. Auswahl wird an `llm-move`
  durchgereicht und beim Ergebnis als `opponent` gespeichert (Bilanz pro Modell).

## Akzeptanzkriterien
- [ ] vs-LLM spielbar: Spieler Weiß, gewähltes Modell Schwarz, vollständige Partie.
- [ ] Illegaler/kaputter LLM-Zug → Minimax-Fallback, Spiel läuft **nie** in einen
      illegalen Zustand und crasht nicht.
- [ ] Modell-Dropdown lädt aus `/api/llm/models`, Default vorausgewählt.
- [ ] Ergebnis wird mit `opponent=<model-id>` gemeldet (nur Modus `llm`).
- [ ] API-Key/Provider-Logik bleibt **vollständig** serverseitig.
- [ ] Backend-Tests: gültiger LLM-Zug, halluzinierter Zug (→ invalid), kaputtes
      JSON (→ invalid), `complete()` gemockt — kein echter Netzcall im Test.
- [ ] Engine-Port-Tests weiter 15/15. Alle Dateien ≤200 Z. Echter `npm run build` grün.

## Nicht in diesem Scope
- Keine Engine-Logik im Backend (kein Minimax-Duplikat — Fallback bleibt im Frontend).
- Kein Streaming, keine Zug-Erklärung/Chat des Modells (Kandidat für Runde 2c).
- Keine Schwierigkeits-/Persona-Prompts pro Modell.
