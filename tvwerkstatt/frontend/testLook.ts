/** Standard-Aussehen wie backend/look.py DEFAULT – für Tests und als Anfangswert. */
import type { TvwLook } from "./api"

export const DEFAULT_LOOK: TvwLook = {
  dock: [], hidden: [], labels: {}, columns: 6, rows_below_dock: 1, background_color: "#000000", wallpaper_dim: 20,
  dock_opacity: 85, rotation_minutes: 0, sky_intensity: 0, clock_format: "24", show_greeting: true, greeting_name: "",
}
