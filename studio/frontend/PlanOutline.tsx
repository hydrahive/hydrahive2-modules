import { ChevronDown, ChevronUp, Download, FileText, MapPin, Package, Plus, User } from "lucide-react"
import { useTranslation } from "react-i18next"
import { ELEMENT_KINDS, type ElementKind, type ImportPreview, type Plan, type Selection } from "./planApi"
import { importAmounts, showImport } from "./planLogic"

const ICON: Record<ElementKind, typeof User> = { character: User, place: MapPin, object: Package }
const row = (active: boolean) => `flex w-full min-w-0 items-center gap-1.5 rounded-[4px] px-1.5 py-1 text-left text-xs ${active ? "bg-[#1c2940] text-[#69d7ff]" : "text-[#e8eef8] hover:bg-[#111827]"}`
const heading = "flex items-center justify-between px-1 pb-1 text-[10px] font-bold uppercase tracking-wide text-[#68758a]"

interface Props {
  plan: Plan
  preview: ImportPreview | null
  selection: Selection | null
  onSelect: (s: Selection) => void
  onMove: (id: string, dir: -1 | 1) => void
  onAddScene: () => void
  onAddElement: (kind: ElementKind) => void
  onImport: () => void
}

/** Planen, links: Drehbuch-Kopf, Szenen in Reihenfolge (hoch/runter), darunter die Bausteine nach Art. */
export function PlanOutline({ plan, preview, selection, onSelect, onMove, onAddScene, onAddElement, onImport }: Props) {
  const { t } = useTranslation("studio")
  const is = (kind: Selection["kind"], id?: string) => selection?.kind === kind && (!id || ("id" in selection && selection.id === id))
  const elements = ELEMENT_KINDS.flatMap((k) => plan.elements.filter((e) => e.kind === k))
  return (
    <div className="mt-2 min-h-0 flex-1 space-y-3 overflow-y-auto px-2 pb-3" data-plan-outline>
      {showImport(preview) && preview && (
        <div className="space-y-2 rounded-[4px] border border-[#69d7ff]/40 bg-[#69d7ff]/10 p-2 text-[11px] leading-relaxed text-[#c3ccdd]" data-plan-import>
          <p>{t("import_offer", importAmounts(t, preview))}</p>
          <button type="button" onClick={onImport} className="flex items-center gap-1.5 rounded-[4px] bg-[#69d7ff] px-2 py-1 font-black text-[#08111c]">
            <Download size={12} /> {t("import_open")}
          </button>
        </div>
      )}
      <button type="button" onClick={() => onSelect({ kind: "head" })} data-plan-head aria-current={is("head") || undefined} className={row(is("head"))}>
        <FileText size={13} className="shrink-0" />
        <span className="truncate font-bold">{plan.screenplay.title || t("untitled")}</span>
      </button>
      <div>
        <p className={heading}>
          <span>{t("scenes")}</span>
          <button type="button" onClick={onAddScene} data-plan-add="scene" title={t("add_scene")} aria-label={t("add_scene")} className="hover:text-[#e8eef8]"><Plus size={13} /></button>
        </p>
        <ol className="space-y-0.5">
          {plan.scenes.map((s, i) => (
            <li key={s.id} className="group flex items-center gap-0.5">
              <button type="button" onClick={() => onSelect({ kind: "scene", id: s.id })} data-plan-scene={s.id}
                aria-current={is("scene", s.id) || undefined} className={row(is("scene", s.id))}>
                <span className="w-5 shrink-0 text-right text-[10px] text-[#68758a]">{i + 1}</span>
                <span className="truncate">{s.title || t("untitled")}</span>
                <span className="ml-auto shrink-0 text-[10px] text-[#68758a]">{s.shots.length ? t("shot_count", { count: s.shots.length }) : ""}</span>
              </button>
              <button type="button" onClick={() => onMove(s.id, -1)} disabled={i === 0} data-plan-move={`${s.id}:-1`} aria-label={t("move_up")}
                className="rounded p-0.5 text-[#68758a] hover:text-[#e8eef8] disabled:opacity-30"><ChevronUp size={12} /></button>
              <button type="button" onClick={() => onMove(s.id, 1)} disabled={i === plan.scenes.length - 1} data-plan-move={`${s.id}:1`} aria-label={t("move_down")}
                className="rounded p-0.5 text-[#68758a] hover:text-[#e8eef8] disabled:opacity-30"><ChevronDown size={12} /></button>
            </li>
          ))}
        </ol>
        {!plan.scenes.length && <p className="px-1.5 text-[11px] text-[#68758a]" data-plan-no-scenes>{t("no_scenes")}</p>}
      </div>
      <div>
        <p className={heading}>
          <span>{t("elements")}</span>
          <span className="flex gap-1">
            {ELEMENT_KINDS.map((k) => {
              const Icon = ICON[k]
              return <button key={k} type="button" onClick={() => onAddElement(k)} data-plan-add={k} title={t(`add_${k}`)} aria-label={t(`add_${k}`)}
                className="hover:text-[#e8eef8]"><Icon size={12} /></button>
            })}
          </span>
        </p>
        <ul className="space-y-0.5">
          {elements.map((e) => {
            const Icon = ICON[e.kind]
            return (
              <li key={e.id}>
                <button type="button" onClick={() => onSelect({ kind: "element", id: e.id })} data-plan-element={e.id}
                  aria-current={is("element", e.id) || undefined} className={row(is("element", e.id))}>
                  <Icon size={12} className="shrink-0 text-[#8d9ab0]" />
                  <span className="truncate">{e.name}</span>
                </button>
              </li>
            )
          })}
        </ul>
        {!plan.elements.length && <p className="px-1.5 text-[11px] text-[#68758a]">{t("no_elements")}</p>}
      </div>
    </div>
  )
}
