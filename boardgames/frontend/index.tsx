import { BoardGamesView } from "./BoardGamesView"
import { BoardGamesBuddyBox } from "./components/BoardGamesBuddyBox"

export const routes = [
  { path: "/boardgames", element: <BoardGamesView /> },
]

export const nav = [
  {
    path: "/boardgames",
    icon: "Crown",
    labelKey: "bg_title",
    group: "working",
    roles: [] as ("admin" | "user")[],
  },
]

export const buddyWidgets = [BoardGamesBuddyBox]

export const i18n = {
  de: {
    boardgames: {
      bg_title: "Brettspiele",
      bg_subtitle: "Klassische Brettspiele — gegeneinander oder gegen den Computer.",
      bg_game_chess: "Schach",
      bg_choose_mode: "Spielmodus wählen",
      bg_mode_hotseat: "2 Spieler (ein Gerät)",
      bg_mode_ai: "Gegen Computer",
      bg_mode: "Modus",
      bg_new_game: "Neue Partie",
      bg_white_turn: "Weiß am Zug",
      bg_black_turn: "Schwarz am Zug",
      bg_white_wins: "♔ Weiß gewinnt — Schachmatt!",
      bg_black_wins: "♚ Schwarz gewinnt — Schachmatt!",
      bg_stalemate: "Patt — Remis.",
      bg_ai_thinking: "Computer überlegt…",
      bg_ai_hint: "Du spielst Weiß, der Computer Schwarz. Klick eine Figur, dann ein Zielfeld.",
      bg_leaderboard: "Bestenliste",
      bg_no_wins: "Noch keine Siege — gewinn gegen den Computer!",
      bg_wins_short: "Siege",
      bg_leaderboard_hint: "Zählt Siege gegen den Computer.",
      bg_close: "Schließen",
    },
  },
  en: {
    boardgames: {
      bg_title: "Board Games",
      bg_subtitle: "Classic board games — against each other or the computer.",
      bg_game_chess: "Chess",
      bg_choose_mode: "Choose game mode",
      bg_mode_hotseat: "2 players (one device)",
      bg_mode_ai: "Vs computer",
      bg_mode: "Mode",
      bg_new_game: "New game",
      bg_white_turn: "White to move",
      bg_black_turn: "Black to move",
      bg_white_wins: "♔ White wins — checkmate!",
      bg_black_wins: "♚ Black wins — checkmate!",
      bg_stalemate: "Stalemate — draw.",
      bg_ai_thinking: "Computer thinking…",
      bg_ai_hint: "You play White, the computer Black. Click a piece, then a target square.",
      bg_leaderboard: "Leaderboard",
      bg_no_wins: "No wins yet — beat the computer!",
      bg_wins_short: "wins",
      bg_leaderboard_hint: "Counts wins against the computer.",
      bg_close: "Close",
    },
  },
}
