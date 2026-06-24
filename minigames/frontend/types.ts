// Minigames — gemeinsame Typen: Spiel-Vertrag + Score-API.

/** Statische Metadaten eines Spiels (für Auswahl-Grid + Bestenliste). */
export interface GameMeta {
  id: string          // "snake" — muss zur Server-Whitelist passen
  titleKey: string    // i18n-Key, z.B. "mg_game_snake"
  icon: string        // lucide-Icon-Name (lose, per Lookup gerendert)
  accent: string      // rgb-Tripel für Akzentfarbe, z.B. "52 211 153"
}

/** Eine laufende Spiel-Instanz auf einem Canvas. */
export interface GameInstance {
  start(): void
  stop(): void        // muss rAF + Event-Listener sauber abbauen
}

export interface GameMountOpts {
  onScore: (score: number) => void
  onGameOver: (finalScore: number) => void
}

/** Ein einbaubares Spiel. Neue Spiele: Datei anlegen + in _registry.ts eintragen. */
export interface GameModule {
  meta: GameMeta
  mount(canvas: HTMLCanvasElement, opts: GameMountOpts): GameInstance
}

// ---------------------------------------------------------------- Score-API
export interface SubmitResult {
  ok: boolean
  is_personal_best: boolean
}

export interface MyScores {
  best: number
  recent: { score: number; created_at: string }[]
}

export interface LeaderboardEntry {
  rank: number
  user: string
  score: number
  created_at: string
}
