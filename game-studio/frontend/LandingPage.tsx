import { ArchiveRestore, ArrowRight, FolderGit2, Gamepad2, Plus, Sparkles } from "lucide-react"
import { useTranslation } from "react-i18next"
import { WorkstationPanel } from "./components/WorkstationPanel"
import type { EntryKind, GameDraft, WorkstationStatus } from "./types"

interface Props {
  drafts: GameDraft[]
  workstation: WorkstationStatus
  onStart: (kind: EntryKind) => void
  onOpen: (draft: GameDraft) => void
}

const ENTRY_ICONS = {
  new: Sparkles,
  adopt: FolderGit2,
  archive: ArchiveRestore,
} as const

export function LandingPage({ drafts, workstation, onStart, onOpen }: Props) {
  const { t } = useTranslation("gameStudio")

  return (
    <main className="mx-auto max-w-6xl px-4 py-6 sm:px-6 lg:px-8">
      <header className="mb-7">
        <div className="mb-2 flex items-center gap-2 text-[#69d7ff]">
          <Gamepad2 size={20} aria-hidden="true" />
          <span className="text-xs font-semibold uppercase tracking-[0.18em]">Game Studio</span>
        </div>
        <h1 className="max-w-3xl text-2xl font-semibold leading-tight text-[#e8eef8] sm:text-3xl">{t("landing.title")}</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-[#9aa7bc]">{t("landing.subtitle")}</p>
      </header>

      <section aria-labelledby="entry-title">
        <h2 id="entry-title" className="mb-3 text-sm font-semibold text-[#c8d2df]">{t("landing.chooseStart")}</h2>
        <div className="grid gap-3 md:grid-cols-3">
          {(["new", "adopt", "archive"] as EntryKind[]).map((kind) => {
            const Icon = ENTRY_ICONS[kind]
            return (
              <button
                key={kind}
                type="button"
                onClick={() => onStart(kind)}
                className="group min-h-44 rounded-2xl border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-innen,17_24_39))] p-5 text-left transition hover:border-[#69d7ff]/40 hover:bg-[rgb(var(--hh-s-hebung,27_37_54))] focus:outline-none focus:ring-2 focus:ring-[#69d7ff]/60"
              >
                <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-[#69d7ff]/10 text-[#69d7ff]">
                  <Icon size={22} aria-hidden="true" />
                </span>
                <span className="mt-4 block text-base font-semibold text-[#e8eef8]">{t(`entry.${kind}.title`)}</span>
                <span className="mt-1 block text-xs leading-5 text-[#9aa7bc]">{t(`entry.${kind}.description`)}</span>
                <span className="mt-4 flex items-center gap-1 text-xs font-medium text-[#69d7ff]">
                  {t("entry.open")} <ArrowRight size={14} className="transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
                </span>
              </button>
            )
          })}
        </div>
      </section>

      <div className="mt-7 grid gap-5 lg:grid-cols-[1fr_320px]">
        <section aria-labelledby="drafts-title">
          <div className="mb-3 flex items-center justify-between">
            <h2 id="drafts-title" className="text-sm font-semibold text-[#c8d2df]">{t("drafts.title")}</h2>
            <button type="button" onClick={() => onStart("new")} className="flex items-center gap-1 text-xs text-[#69d7ff] hover:text-[#9ee6ff]">
              <Plus size={14} aria-hidden="true" /> {t("drafts.new")}
            </button>
          </div>
          {drafts.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-box,21_28_43))] px-5 py-8 text-center">
              <p className="text-sm font-medium text-[#c8d2df]">{t("drafts.emptyTitle")}</p>
              <p className="mt-1 text-xs text-[#9aa7bc]">{t("drafts.emptyText")}</p>
            </div>
          ) : (
            <div className="space-y-2">
              {drafts.map((draft) => (
                <button key={draft.draft_id} type="button" onClick={() => onOpen(draft)} className="flex w-full items-center gap-3 rounded-xl border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-innen,17_24_39))] px-4 py-3 text-left hover:bg-[rgb(var(--hh-s-hebung,27_37_54))]">
                  <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#69d7ff]/10 text-[#69d7ff]"><Gamepad2 size={18} aria-hidden="true" /></span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-medium text-[#e8eef8]">{draft.title}</span>
                    <span className="block text-[11px] text-[#9aa7bc]">{t(`entry.${draft.entry_kind}.title`)} · {t("drafts.step", { step: draft.current_step })}</span>
                  </span>
                  <ArrowRight size={16} className="text-[#9aa7bc]" aria-hidden="true" />
                </button>
              ))}
            </div>
          )}
        </section>
        <WorkstationPanel status={workstation} />
      </div>
    </main>
  )
}
