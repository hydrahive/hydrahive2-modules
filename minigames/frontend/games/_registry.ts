// Spiel-Registry — zentrale Liste aller einbaubaren Spiele.
// Neues Spiel hinzufügen: Datei in games/ anlegen (GameModule exportieren),
// hier importieren + in GAMES eintragen. Sonst nichts anfassen.
import { snake } from "./snake"
import type { GameModule } from "../types"

export const GAMES: GameModule[] = [
  snake,
]

export function gameById(id: string): GameModule | undefined {
  return GAMES.find((g) => g.meta.id === id)
}
