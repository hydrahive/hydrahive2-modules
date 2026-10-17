import { Sparkles } from "lucide-react"
import { useTranslation } from "react-i18next"
import { DEMO_MEDIA, DEMO_TRACKS } from "./demoData"
import type { Workspace } from "./workspaces"

interface Props {
  workspace: Workspace
  clipId: string | null
  mediaId: string | null
}

const label = "block text-[10px] font-bold uppercase tracking-wide text-[#68758a]"
const field = "mt-1 w-full rounded-[4px] border border-[#46617f] bg-[#111827] px-2 py-1 text-xs text-[#e8eef8]"

/** Eigenschaften: zeigt je nach Arbeitsbereich und Auswahl das Passende (Attrappe). */
export function InspectorPanel({ workspace, clipId, mediaId }: Props) {
  const { t } = useTranslation("studio")
  const clip = DEMO_TRACKS.flatMap((tr) => tr.clips).find((c) => c.id === clipId) ?? null
  const media = DEMO_MEDIA.find((m) => m.id === (mediaId ?? clip?.mediaId)) ?? null
  const showGenerate = workspace === "generate" || clip?.placeholder
  return (
    <section className="flex h-full min-h-0 flex-col overflow-y-auto p-3" data-studio-panel="inspector">
      <h2 className="text-[11px] font-black uppercase tracking-[0.14em] text-[#68758a]">
        {showGenerate ? t("generate") : t("properties")}
      </h2>
      {showGenerate ? <GenerateForm placeholder={clip?.placeholder ? clip.label : null} /> : (
        clip || media ? (
          <div className="mt-3 space-y-3 text-xs">
            <p className="font-bold text-[#e8eef8]">{clip?.label ?? media?.name}</p>
            {clip && (
              <dl className="grid grid-cols-2 gap-x-2 gap-y-1 text-[#8d9ab0]">
                <dt>{t("start")}</dt><dd className="text-right text-[#e8eef8]">{clip.start.toFixed(1)} s</dd>
                <dt>{t("length")}</dt><dd className="text-right text-[#e8eef8]">{clip.length.toFixed(1)} s</dd>
              </dl>
            )}
            <div><span className={label}>{t("volume")}</span><input type="range" className="mt-1 w-full" defaultValue={80} /></div>
            <div><span className={label}>{t("opacity")}</span><input type="range" className="mt-1 w-full" defaultValue={100} /></div>
            {media && <p className="text-[11px] text-[#68758a]">{t(`origin.${media.origin}`)}</p>}
          </div>
        ) : <p className="mt-3 text-xs text-[#68758a]">{t("nothing_selected")}</p>
      )}
    </section>
  )
}

function GenerateForm({ placeholder }: { placeholder: string | null }) {
  const { t } = useTranslation("studio")
  return (
    <div className="mt-3 space-y-3 text-xs" data-studio-generate>
      {placeholder && <p className="rounded-[4px] border border-[#ffb86b]/40 bg-[#ffb86b]/10 px-2.5 py-2 leading-relaxed text-[#ffb86b]">{t("fill_placeholder", { name: placeholder })}</p>}
      <div className="flex gap-1">
        {(["image", "video", "voice", "music"] as const).map((k, i) => (
          <button key={k} type="button" className={`flex-1 rounded-[4px] px-1 py-1 text-[11px] font-bold ${i === 1 ? "bg-[#1c2940] text-[#69d7ff]" : "bg-[#111827] text-[#8d9ab0]"}`}>
            {t(`gen.${k}`)}
          </button>
        ))}
      </div>
      <label className="block"><span className={label}>{t("prompt")}</span>
        <textarea rows={4} className={field} defaultValue="Mira steht am Steg, dunkle Wolken ziehen über den Hafen, Wind in den Haaren." /></label>
      <label className="block"><span className={label}>{t("elements")}</span>
        <div className="mt-1 flex flex-wrap gap-1">{["Mira", "Hafen"].map((n) => <span key={n} className="rounded-full bg-[#111827] px-2 py-0.5 text-[#c3ccdd]">{n}</span>)}</div></label>
      <label className="block"><span className={label}>{t("model")}</span>
        <select className={field}><option>Kling 3.0</option><option>Seedance 2.0</option><option>Veo 3.1</option></select></label>
      <div className="grid grid-cols-2 gap-2">
        <label className="block"><span className={label}>{t("length")}</span><select className={field}><option>5 s</option><option>10 s</option></select></label>
        <label className="block"><span className={label}>{t("variants")}</span><select className={field}><option>2</option><option>1</option><option>4</option></select></label>
      </div>
      <button type="button" className="flex w-full items-center justify-center gap-1.5 rounded-[4px] bg-[#69d7ff] py-1.5 text-xs font-black text-[#08111c]">
        <Sparkles size={13} /> {t("generate_now")}
      </button>
      <p className="text-[10px] text-[#68758a]">{t("generate_hint")}</p>
    </div>
  )
}
