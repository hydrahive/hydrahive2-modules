// Spiel-Registry — zentrale Liste aller einbaubaren Spiele.
// Neues Spiel hinzufügen: Datei in games/ anlegen (GameModule exportieren),
// hier importieren + in GAMES eintragen. Backend-Whitelist (backend/games.py)
// nicht vergessen. Sonst nichts anfassen.
import { frogger } from "./frogger"
import { invaders } from "./invaders"
import { snake } from "./snake"
import type { GameModule } from "../types"

export const GAMES: GameModule[] = [
  snake,
  invaders,
  frogger,
]

export function gameById(id: string): GameModule | undefined {
  return GAMES.find((g) => g.meta.id === id)
}
