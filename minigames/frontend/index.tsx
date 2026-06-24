import { ArcadeView } from "./ArcadeView"
import { MinigamesBuddyBox } from "./components/MinigamesBuddyBox"

export const routes = [
  { path: "/minigames", element: <ArcadeView /> },
]

export const nav = [
  {
    path: "/minigames",
    icon: "Gamepad2",
    labelKey: "mg_title",
    group: "working",
    roles: [] as ("admin" | "user")[],
  },
]

export const buddyWidgets = [MinigamesBuddyBox]

export const i18n = {
  de: {
    minigames: {
      mg_title: "Minigames",
      mg_subtitle: "Kleine Retro-Spiele — Highscores landen in der Bestenliste.",
      mg_game_snake: "Snake",
      mg_game_invaders: "Space Invaders",
      mg_game_frogger: "Frogger",
      mg_leaderboard: "Bestenliste",
      mg_no_scores: "Noch keine Scores — sei der Erste!",
      mg_personal_best: "Persönlicher Rekord!",
      mg_controls_hint: "Steuerung: Pfeiltasten oder WASD · Neustart: Leertaste · Schließen: ESC",
      mg_close: "Schließen",
    },
  },
  en: {
    minigames: {
      mg_title: "Minigames",
      mg_subtitle: "Small retro games — high scores go on the leaderboard.",
      mg_game_snake: "Snake",
      mg_game_invaders: "Space Invaders",
      mg_game_frogger: "Frogger",
      mg_leaderboard: "Leaderboard",
      mg_no_scores: "No scores yet — be the first!",
      mg_personal_best: "Personal best!",
      mg_controls_hint: "Controls: arrow keys or WASD · Restart: Space · Close: ESC",
      mg_close: "Close",
    },
  },
}
