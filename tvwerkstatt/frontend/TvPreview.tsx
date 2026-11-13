import { useTranslation } from "react-i18next"
import type { Mood, TvwApp, TvwLook } from "./api"
import { clockText, greetingKey, textOn, type Tile, tiles } from "./desktopLogic"
import { useAuthImage } from "./useAuthImage"

const SKY: Record<Mood, string> = {
  morning: "radial-gradient(120% 90% at 20% 105%, #ffb36b 0%, #e2705f 28%, #6b5a9a 58%, #26365e 100%)",
  evening: "radial-gradient(120% 90% at 80% 105%, #ff8a5c 0%, #b0477a 30%, #45306f 60%, #151b3a 100%)",
  night: "radial-gradient(120% 90% at 50% 110%, #1d3a66 0%, #101d3d 45%, #05070f 100%)",
}

/** Vorschau des Startbildschirms (Muster: Demo). Kein echtes Bild vom Fernseher, sondern aus Aussehen und Apps. */
export function TvPreview({ apps, look, mood, wallpaper, imagePath, now }: {
  apps: TvwApp[]; look: TvwLook; mood: Mood; wallpaper: string | null; imagePath: (pkg: string) => string; now: Date
}) {
  const { t } = useTranslation("tvwerkstatt")
  const { dock, grid } = tiles(apps, look)
  const bg = useAuthImage(wallpaper)
  const focus = dock[0]
  const date = now.toLocaleDateString("de-DE", { weekday: "long", day: "numeric", month: "long" })
  return (
    <div className="rounded-xl border border-[rgb(var(--hh-s-rand,52_66_92))] bg-black p-2">
      <div className="relative aspect-video overflow-hidden rounded-md text-white"
        style={{ background: bg ? `center/cover url(${bg})` : look.sky_intensity > 0 ? SKY[mood] : look.background_color }}
        data-testid="tv">
        {bg && <div className="absolute inset-0 bg-black" style={{ opacity: look.wallpaper_dim / 100 }} />}
        <div className="absolute left-[4%] right-[4%] top-[5%] flex items-center gap-2">
          <div>
            {look.show_greeting && (
              <div className="text-[10px] uppercase tracking-wider opacity-80">
                {t(greetingKey(now.getHours()))}{look.greeting_name ? `, ${look.greeting_name}` : ""}
              </div>
            )}
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-light">{clockText(now, look.clock_format)}</span>
              <span className="text-xs opacity-80">{date}</span>
            </div>
          </div>
          <div className="ml-auto flex gap-1.5 text-[10px]">
            {["desk.pill_inputs", "desk.pill_network", "desk.pill_settings"].map((k) => (
              <span key={k} className="rounded-full px-2 py-0.5" style={{ background: "rgba(255,255,255,.14)" }}>
                {t(k)}</span>
            ))}
          </div>
        </div>
        {focus && <div className="absolute left-[4%] top-[36%] text-xl font-semibold drop-shadow">{focus.label}</div>}
        <div className="absolute inset-x-0 top-[50%] grid gap-2 px-[4%] py-2"
          style={{ gridTemplateColumns: `repeat(${look.columns}, minmax(0,1fr))`,
            background: `rgba(8,11,17,${(look.dock_opacity / 100) * 0.55})` }}>
          {dock.map((x, i) => <TileView key={x.pkg} tile={x} focus={i === 0} src={imagePath(x.pkg)} />)}
        </div>
        <div className="absolute inset-x-[4%] top-[78%] grid gap-2"
          style={{ gridTemplateColumns: `repeat(${look.columns}, minmax(0,1fr))` }}>
          {grid.map((x) => <TileView key={x.pkg} tile={x} focus={false} src={imagePath(x.pkg)} />)}
        </div>
        {dock.length === 0 && (
          <div className="absolute inset-x-0 top-[55%] text-center text-xs opacity-80">{t("desk.no_apps")}</div>
        )}
      </div>
    </div>
  )
}

function TileView({ tile, focus, src }: { tile: Tile; focus: boolean; src: string }) {
  const img = useAuthImage(tile.hasImage ? src : null)
  return (
    <div className={`flex aspect-video items-center justify-center overflow-hidden rounded-md text-[10px] font-bold
      shadow-md ${focus ? "scale-105 outline outline-2 outline-white" : ""}`}
      style={{ background: tile.color, color: textOn(tile.color) }} title={tile.label}>
      {img ? <img src={img} alt={tile.label} className="h-full w-full object-contain" /> : <span>{tile.label}</span>}
    </div>
  )
}
