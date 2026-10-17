import { Sparkles } from "lucide-react"
import { useTranslation } from "react-i18next"
import type { LibraryItem } from "./api"
import { DEMO_TRACKS } from "./demoData"
import { formatSize } from "./libraryView"
import type { Workspace } from "./workspaces"

interface Props {
  workspace: Workspace
  clipId: string | null
  item: LibraryItem | null
}

const label = "block text-[10px] font-bold uppercase tracking-wide text-[#68758a]"
const field = "mt-1 w-full rounded-[4px] border border-[#46617f] bg-[#111827] px-2 py-1 text-xs text-[#e8eef8]"

/** Eigenschaften: echtes Medium aus der Bibliothek; „Erzeugen“ und Zeitleisten-Clips noch als Vorschau (Etappe 3/4). */
export function InspectorPanel({ workspace, clipId, item }: Props) {
  const { t } = useTranslation("studio")
  const clip = DEMO_TRACKS.flatMap((tr) => tr.clips).find((c) => c.id === clipId) ?? null
  const showGenerate = workspace === "generate" || clip?.placeholder
  return (
    <section className="flex h-full min-h-0 flex-col overflow-y-auto p-3" data-studio-panel="inspector">
      <h2 className="text-[11px] font-black uppercase tracking-[0.14em] text-[#68758a]">
        {showGenerate ? t("generate") : t("properties")}
      </h2>
      {showGenerate ? <GenerateForm placeholder={clip?.placeholder ? clip.label : null} />
        : item ? <ItemInfo item={item} />
          : clip ? (
            <dl className="mt-3 grid grid-cols-2 gap-x-2 gap-y-1 text-xs text-[#8d9ab0]">
              <dt className="col-span-2 font-bold text-[#e8eef8]">{clip.label}</dt>
              <dt>{t("start")}</dt><dd className="text-right text-[#e8eef8]">{clip.start.toFixed(1)} s</dd>
              <dt>{t("length")}</dt><dd className="text-right text-[#e8eef8]">{clip.length.toFixed(1)} s</dd>
            </dl>
          ) : <p className="mt-3 text-xs text-[#68758a]">{t("nothing_selected")}</p>}
    </section>
  )
}

function ItemInfo({ item }: { item: LibraryItem }) {
  const { t } = useTranslation("studio")
  const rows: [string, string][] = [
    [t("info.kind"), t(`kind.${item.kind}`)],
    [t("info.source"), t(`source.${item.source}`)],
    [t("info.origin"), t(`origin.${item.origin}`)],
    [t("info.created"), item.created_at.slice(0, 16).replace("T", " ")],
    ...(item.kind !== "element" ? [[t("info.size"), formatSize(item.size)] as [string, string]] : []),
    ...(item.duration ? [[t("length"), `${item.duration} s`] as [string, string]] : []),
    ...(item.model ? [[t("model"), item.model] as [string, string]] : []),
  ]
  return (
    <div className="mt-3 space-y-3 text-xs" data-studio-info={item.id}>
      <p className="break-words font-bold text-[#e8eef8]">{item.name}</p>
      <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
        {rows.map(([k, v]) => (
          <div key={k} className="contents"><dt className="text-[#8d9ab0]">{k}</dt><dd className="break-all text-right text-[#e8eef8]">{v}</dd></div>
        ))}
      </dl>
      {item.prompt && (
        <div><span className={label}>{t("prompt")}</span><p className="mt-1 whitespace-pre-wrap rounded-[4px] bg-[#111827] p-2 text-[#c3ccdd]">{item.prompt}</p></div>
      )}
    </div>
  )
}

function GenerateForm({ placeholder }: { placeholder: string | null }) {
  const { t } = useTranslation("studio")
  return (
    <div className="mt-3 space-y-3 text-xs" data-studio-generate>
      <p className="rounded-[4px] border border-[#46617f] bg-[#111827] px-2.5 py-2 text-[11px] leading-relaxed text-[#8d9ab0]">{t("generate_soon")}</p>
      {placeholder && <p className="rounded-[4px] border border-[#ffb86b]/40 bg-[#ffb86b]/10 px-2.5 py-2 leading-relaxed text-[#ffb86b]">{t("fill_placeholder", { name: placeholder })}</p>}
      <div className="flex gap-1">
        {(["image", "video", "voice", "music"] as const).map((k, i) => (
          <button key={k} type="button" disabled className={`flex-1 rounded-[4px] px-1 py-1 text-[11px] font-bold ${i === 1 ? "bg-[#1c2940] text-[#69d7ff]" : "bg-[#111827] text-[#8d9ab0]"}`}>
            {t(`gen.${k}`)}
          </button>
        ))}
      </div>
      <label className="block"><span className={label}>{t("prompt")}</span>
        <textarea rows={4} disabled className={field} defaultValue="Mira steht am Steg, dunkle Wolken ziehen über den Hafen, Wind in den Haaren." /></label>
      <label className="block"><span className={label}>{t("model")}</span>
        <select disabled className={field}><option>Kling 3.0</option><option>Seedance 2.0</option><option>Veo 3.1</option></select></label>
      <button type="button" disabled className="flex w-full items-center justify-center gap-1.5 rounded-[4px] bg-[#69d7ff]/40 py-1.5 text-xs font-black text-[#08111c]">
        <Sparkles size={13} /> {t("generate_now")}
      </button>
    </div>
  )
}
