import { ArrowRight, Download, Film, Loader2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import { fileUrl } from "@/shared/files"
import { DEFAULT_PRESET, deliverSummary, downloadName, minutes, presetLabel, type Preset } from "./deliverLogic"
import { DeliverPreset } from "./DeliverPreset"
import { QUEUE_MAX, queueFull } from "./queueLogic"
import { RenderQueue } from "./RenderQueue"
import type { Job } from "./planApi"
import type { RenderItem } from "./renderApi"
import type { TimelineClip } from "./timelineApi"

interface Props {
  clips: TimelineClip[]
  aspect: string
  /** null = wird noch geladen */
  renders: RenderItem[] | null
  /** Film-Aufträge der Warteschlange (7c), älteste oben */
  queue?: Job[]
  cancelling?: string | null
  onCancel?: (id: string) => void
  /** Fehler der letzten Aktion (z. B. Warteschlange voll) – sonst sähe man im Reiter „Ausgabe“ nichts */
  error?: string | null
  busy: boolean
  onRender: () => void
  onCut: () => void
  /** Sprachen mit Untertiteln (6c); mitliefern als abschaltbare Spuren, nie eingebrannt */
  subtitleLanguages?: string[]
  withSubtitles?: boolean
  onWithSubtitles?: (on: boolean) => void
  /** Vorlage (7b): Format + Qualität */
  preset?: Preset
  onPreset?: (p: Preset) => void
}

/** Reiter „Ausgabe“ (4d, 7b): Vorlage wählen, Film als MP4 erzeugen, fertige Filme ansehen und herunterladen. */
export function DeliverPanel({ clips, aspect, renders, queue = [], cancelling = null, onCancel = () => {}, error = null, busy, onRender, onCut,
  subtitleLanguages = [], withSubtitles = false, onWithSubtitles, preset = DEFAULT_PRESET, onPreset }: Props) {
  const { t } = useTranslation("studio")
  const sum = deliverSummary(clips)
  const full = queueFull(queue)
  return (
    <section className="flex h-full min-h-0 flex-col gap-3 overflow-y-auto p-4 text-xs text-[#c3ccdd]" data-studio-panel="deliver">
      <div className="space-y-2 rounded-[6px] border border-[#46617f] bg-[#0e1420] p-3">
        {!sum.clips ? (
          <>
            <p data-deliver-empty>{t("deliver_empty")}</p>
            <button type="button" onClick={onCut} className="flex items-center gap-1.5 rounded-[4px] border border-[#46617f] px-2.5 py-1 font-bold text-[#69d7ff] hover:bg-[#1c2940]">
              {t("soon_to_cut")} <ArrowRight size={12} />
            </button>
          </>
        ) : (
          <>
            <p className="text-sm text-[#e8eef8]">{t("deliver_summary", { length: minutes(sum.seconds), clips: sum.clips })}</p>
            {sum.placeholders > 0 && <p className="text-[#ffb86b]">{t("deliver_placeholders", { count: sum.placeholders })}</p>}
            <p className="text-[#8d9ab0]">{t("deliver_hint")}</p>
          </>
        )}
        <DeliverPreset preset={preset} screenplay={aspect} onChange={onPreset} />
        {subtitleLanguages.length ? (
          <label className="flex cursor-pointer items-center gap-2 text-[#c3ccdd]">
            <input type="checkbox" checked={withSubtitles} onChange={(e) => onWithSubtitles?.(e.target.checked)} data-deliver-subtitles className="accent-[#69d7ff]" />
            {t("deliver_subtitles", { names: subtitleLanguages.map((l) => t(`lang.${l}`)).join(", ") })}
          </label>
        ) : <p className="text-[#68758a]">{t("deliver_subtitles_none")}</p>}
        <button type="button" onClick={onRender} disabled={busy || full || !sum.clips} data-deliver-run
          className="flex items-center gap-1.5 rounded-[4px] bg-[#69d7ff] px-3 py-1.5 font-black text-[#08111c] disabled:opacity-50">
          {busy ? <Loader2 size={13} className="animate-spin" /> : <Film size={13} />} {t("deliver_run")}
        </button>
        {full && <p className="text-[#ffb86b]" data-queue-full>{t("queue_full", { max: QUEUE_MAX })}</p>}
        {error && <p className="text-[#ff6b8a]" data-deliver-error>{error}</p>}
        <RenderQueue jobs={queue} cancelling={cancelling} onCancel={onCancel} />
      </div>
      <h3 className="text-[11px] font-black uppercase tracking-[0.14em] text-[#68758a]">{t("deliver_films")}</h3>
      {!renders ? <p className="flex items-center gap-1.5 text-[#68758a]"><Loader2 size={12} className="animate-spin" /> {t("loading")}</p>
        : !renders.length ? <p className="text-[#68758a]">{t("deliver_none")}</p> : (
        <div className="grid grid-cols-[repeat(auto-fill,minmax(260px,1fr))] gap-3">
          {renders.map((r) => (
            <figure key={r.rel} className="space-y-1.5 rounded-[6px] border border-[#2a364b] bg-[#0d1420] p-2" data-deliver-film={r.rel}>
              <video src={fileUrl(r.abs)} controls preload="metadata" className="aspect-video w-full rounded-[3px] bg-black object-contain" />
              <figcaption className="space-y-1">
                <p className="text-[#e8eef8]">{(r.created_at || "").slice(0, 16).replace("T", " ")}</p>
                <p className="text-[#8d9ab0]">{t("deliver_film_info", { length: minutes(r.duration ?? 0), width: r.width, height: r.height })}</p>
                {presetLabel(t, r) && <p className="text-[#8d9ab0]" data-deliver-preset>{presetLabel(t, r)}</p>}
                {!!r.subtitles?.length && <p className="text-[#8d9ab0]">{t("deliver_film_subtitles", { names: r.subtitles.map((l) => t(`lang.${l}`)).join(", ") })}</p>}
                {!!r.missing && <p className="text-[#ffb86b]">{t("deliver_missing", { count: r.missing })}</p>}
                <a href={fileUrl(r.abs)} download={downloadName(r)}
                  className="inline-flex items-center gap-1 rounded-[4px] border border-[#2a364b] px-2 py-1 font-bold text-[#69d7ff] hover:border-[#69d7ff] hover:bg-[#1c2940]">
                  <Download size={12} /> {t("deliver_download")}
                </a>
              </figcaption>
            </figure>
          ))}
        </div>
      )}
    </section>
  )
}
