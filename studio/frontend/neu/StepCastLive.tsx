/** G2 Schritt 2 „Figuren & Orte“: Karten je Baustein, Hinzufügen, Löschen mit eigenem Dialog. */
import { MapPin, User } from "lucide-react"
import { useTranslation } from "react-i18next"
import { DeleteDialog } from "../DeleteDialog"
import { PersonCard } from "./PersonCard"
import { StepHead } from "./ui"
import type { GuidedState } from "./useGuided"
import type { CastActions } from "./useCast"

export function CastIntro({ names, open, onAdd }: { names: string[]; open: number; onAdd: (k: "character" | "place") => void }) {
  const { t } = useTranslation("studio")
  const btn = "inline-flex items-center justify-center gap-2 rounded-[8px] border border-[rgb(var(--hh-s-rand-hover,70_97_127))] px-4 py-2.5 text-sm font-bold text-[#e8eef8] hover:bg-[#1c2940]"
  return (
    <div className="mb-4 space-y-3" data-guided-open={open}>
      <p className="rounded-[10px] border border-[#69d7ff]/30 bg-[#69d7ff]/5 p-3 text-sm text-[#cdeeff]">
        {names.length ? t("guided.cast_found", { names: names.join(", ") }) : t("guided.cast_none")}
      </p>
      <div className="flex flex-wrap items-center gap-2">
        <button type="button" className={btn} onClick={() => onAdd("character")}><User size={16} /> {t("guided.add_character")}</button>
        <button type="button" className={btn} onClick={() => onAdd("place")}><MapPin size={16} /> {t("guided.add_place")}</button>
        <span className="text-xs text-[#9aa7bc]">{t("guided.add_hint")}</span>
      </div>
    </div>
  )
}

export function StepCastLive({ g, c }: { g: GuidedState; c: CastActions }) {
  const { t } = useTranslation("studio")
  const els = g.plan?.elements ?? []
  return (
    <div>
      <StepHead n={2} title={t("guided.step.2.title")} text={t("guided.cast_head")} />
      <CastIntro names={els.map((e) => e.name)} open={c.open} onAdd={c.add} />
      {g.error && <p className="mb-3 rounded-[8px] border border-[#ffb86b]/40 bg-[#ffb86b]/10 px-3 py-2 text-sm text-[#ffd9ad]">{g.error}</p>}
      <div className="grid gap-4 lg:grid-cols-2">
        {els.map((e) => (
          <PersonCard key={e.id} el={e} base={g.plan?.base ?? ""} jobs={c.jobs} uploading={c.uploading === e.id} busy={g.busy}
            imageModel={g.plan?.screenplay.models.image ?? ""}
            onName={(name) => c.save(e, { name })} onDescription={(description) => c.save(e, { description })}
            onPhoto={(f) => void c.photo(e, f)} onProbe={() => void c.probe(e.id)} onApprove={() => c.save(e, { approved: true })}
            onReopen={() => c.save(e, { approved: false })} onNoPhoto={(v) => c.save(e, { no_photo: v })}
            onOtherPhoto={() => c.save(e, { references: [], probe_rel: "", approved: false })} onDelete={() => c.setDeleting(e)}
            onRedescribe={() => void c.redescribe(e.id)} />
        ))}
      </div>
      {c.deleting && <DeleteDialog name={c.deleting.name} busy={g.busy} onConfirm={c.confirmDelete} onClose={() => c.setDeleting(null)} />}
    </div>
  )
}
