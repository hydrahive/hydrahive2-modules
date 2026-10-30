import { useTranslation } from "react-i18next"
import { Tv, VolumeX } from "lucide-react"
import type { TvStatus } from "./api"

/** Karte „Läuft gerade“: Sender, Sendung, Lautstärke – oder „aus“. */
export function NowPlaying({ status }: { status: TvStatus }) {
  const { t } = useTranslation("fernseher")
  if (status.power !== "on") {
    return <section className="rounded-xl border border-white/10 bg-zinc-900 p-4 text-sm text-zinc-400">{t("now.off")}</section>
  }
  return (
    <section className="rounded-xl border border-white/10 bg-zinc-900 p-4" data-tv-now>
      <h2 className="text-xs uppercase tracking-wide text-zinc-500">{t("now.heading")}</h2>
      {status.channel ? (
        <div className="mt-1 flex items-baseline gap-2">
          <Tv size={16} className="shrink-0 text-zinc-400" />
          <span className="text-lg font-semibold text-zinc-100">{status.channel.name}</span>
          {status.channel.number !== null && <span className="text-sm text-zinc-500">{status.channel.number}</span>}
        </div>
      ) : (
        <p className="mt-1 text-zinc-300">{t("now.app")}</p>
      )}
      {status.program && <p className="mt-0.5 text-sm text-zinc-300">{status.program}</p>}
      <p className="mt-2 flex items-center gap-1 text-sm text-zinc-400">
        {status.muted ? <><VolumeX size={14} /> {t("now.muted")}</> : t("now.volume", { volume: status.volume })}
        {status.output === "receiver" && <span className="text-zinc-500">· {t("now.receiver")}</span>}
      </p>
    </section>
  )
}
