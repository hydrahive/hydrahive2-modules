// Brettspiel-Registry — zentrale Liste aller einbaubaren Spiele.
// Neues Spiel: Komponente bauen (BoardGameProps), hier importieren + eintragen.
// Backend-Whitelist (backend/games.py) nicht vergessen.
import { ChessGame } from "../chess/ChessGame"
import type { BoardGameModule } from "../types"

export const BOARD_GAMES: BoardGameModule[] = [
  {
    meta: { id: "chess", titleKey: "bg_game_chess", icon: "Crown", accent: "234 179 8" },
    component: ChessGame,
  },
]
