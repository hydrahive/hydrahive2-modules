import { useTranslation } from "react-i18next"
import { CockpitShell } from "@/features/cockpit/CockpitShell"
import { CockpitTopbar } from "@/features/cockpit/CockpitTopbar"
import { BatchDialog } from "./BatchDialog"
import { BatchMenu } from "./BatchMenu"
import { BatchStatus } from "./BatchStatus"
import { DecomposeDialog } from "./DecomposeDialog"
import { DeleteDialog } from "./DeleteDialog"
import { ImportDialog } from "./ImportDialog"
import { InspectorPanel } from "./InspectorPanel"
import { LibraryPanel } from "./LibraryPanel"
import { PlanInspector } from "./PlanInspector"
import { PlanPreview } from "./PlanPreview"
import { PlanSidebar } from "./PlanSidebar"
import { PreviewPanel } from "./PreviewPanel"
import { Splitter } from "./Splitter"
import { StoryboardPanel } from "./StoryboardPanel"
import { CommandPalette, ShortcutHelp } from "./StudioDialogs"
import { StudioHeader } from "./StudioHeader"
import { TimelinePanel } from "./TimelinePanel"
import { useLibrary } from "./useLibrary"
import { usePlan } from "./usePlan"
import { useBatch } from "./useBatch"
import { useJobs } from "./useJobs"
import { useShots } from "./useShots"
import { useStudioState } from "./useStudioState"

const toastCls = "pointer-events-none fixed bottom-6 left-1/2 z-[80] -translate-x-1/2 rounded-[4px] border border-[#46617f] bg-[#0e1420] px-3 py-1.5 text-xs text-[#c3ccdd]"

/** Studio: Bibliothek + Vorschau (Etappe 1), „Planen“ mit echten Planungsdaten (Etappe 2a). Zeitleiste noch Beispiel. */
export function StudioPage() {
  const { t } = useTranslation("studio")
  const lib = useLibrary()
  const s = useStudioState(lib.items)
  const planning = s.workspace === "plan"
  const p = usePlan(lib.projectId, planning)
  const plan = { ...p, select: (x: Parameters<typeof p.select>[0]) => { s.clearMedia(); p.select(x) } }   // Auswahl im Drehbuch löst das Medium ab
  const focus = s.workspace === "audio" ? "audio" : s.workspace === "subtitles" ? "subtitles" : "all"
  const library = <LibraryPanel items={lib.items} loading={lib.loading} error={lib.error} truncated={lib.truncated} selected={s.mediaId} onSelect={s.selectMedia} />
  const jobs = useJobs(lib.projectId, planning, () => { void p.reload(); void lib.reload() })   // fertig → Shot + Bibliothek neu
  const sh = useShots(plan, lib.projectId, () => void jobs.reload())
  const bt = useBatch(plan, lib.projectId, jobs.jobs, () => void jobs.reload())
  const scene = sh.scene
  const reload = () => { void lib.reload(); if (planning) void p.reload() }
  return (
    <CockpitShell title={t("title")} className="flex h-full min-h-0 flex-col overflow-hidden bg-[#080b11]" hideHeader>
      <CockpitTopbar active="/studio" context={t("title")} />
      <div className="flex min-h-0 flex-1 flex-col text-[#e8eef8]" data-studio-root data-studio-ws={s.workspace}>
        <StudioHeader projects={lib.projects} projectId={lib.projectId} onProject={lib.setProjectId} onReload={reload}
          workspace={s.workspace} onWorkspace={s.setWorkspace} onCommand={() => s.setDialog("command")} onHelp={() => s.setDialog("help")} running={jobs.running}
          batch={planning && bt.active ? <BatchStatus job={bt.active} cancelling={bt.cancelling} onCancel={bt.cancel} /> : undefined} />
        <div className="flex min-h-0 flex-col" style={{ flex: `${100 - s.layout.timeline} 1 0` }}>
          <div className="flex min-h-0 flex-1">
            <div className="min-w-0 border-r border-[#2a364b] bg-[#0b111b]" style={{ width: `${s.layout.library}%` }}>
              {planning ? <PlanSidebar p={plan} library={library} /> : library}
            </div>
            <Splitter dir="x" label={t("resize_library")} onDrag={(d) => s.drag("library", d)} />
            <div className="min-w-0 flex-1">
              {planning && !s.item
                ? <div className="flex h-full min-h-0 items-center justify-center p-3" data-studio-panel="preview"><PlanPreview plan={p.plan} selection={p.selection} /></div>
                : <PreviewPanel item={s.item} bind={s.player.bind} time={s.item ? s.player.time : 0} duration={s.player.duration}
                    playing={s.player.playing} onPlay={s.player.toggle} onSeek={s.seek} />}
            </div>
            <Splitter dir="x" label={t("resize_inspector")} onDrag={(d) => s.drag("inspector", d)} />
            <div className="min-w-0 border-l border-[#2a364b] bg-[#0b111b]" style={{ width: `${s.layout.inspector}%` }}>
              {planning && !s.item ? <PlanInspector p={plan} shots={sh} jobs={jobs.jobs} images={lib.items.filter((i) => i.kind === "image")} />
                : <InspectorPanel workspace={s.workspace} clipId={s.clipId} item={s.item} />}
            </div>
          </div>
        </div>
        <Splitter dir="y" label={t("resize_timeline")} onDrag={(d) => s.drag("timeline", d)} />
        <div className="min-h-0 border-t border-[#2a364b] bg-[#0b111b]" style={{ flex: `${s.layout.timeline} 1 0` }}>
          {planning
            ? <StoryboardPanel scene={scene} base={p.plan?.base ?? ""} selected={p.selection?.kind === "shot" ? p.selection.id : null} busy={sh.busy}
                runningShots={jobs.jobs.filter((j) => j.status === "running" || j.status === "queued").map((j) => j.target)}
                onSelect={(id) => { if (scene) plan.select({ kind: "shot", sceneId: scene.id, id }) }}
                batchMenu={<BatchMenu running={!!bt.active} onPick={(k) => void bt.open(k)} />}
                onAdd={() => void sh.add()} onMove={(id, d) => void sh.move(id, d)} onDecompose={() => void sh.decompose()} />
            : <TimelinePanel time={s.time} view={s.view} snap={s.snap} selected={s.clipId} focus={focus}
                onView={s.setView} onSeek={s.seek} onSelect={s.selectClip} onSnap={s.toggleSnap} />}
        </div>
        {s.dialog === "help" && <ShortcutHelp onClose={() => s.setDialog(null)} />}
        {s.dialog === "command" && <CommandPalette onClose={() => s.setDialog(null)} onRun={s.run} />}
        {p.dialog?.kind === "import" && p.preview && <ImportDialog preview={p.preview} busy={p.busy} onRun={() => void p.runImport()} onClose={() => p.setDialog(null)} />}
        {bt.dialog && <BatchDialog kind={bt.dialog.kind} preview={bt.dialog.preview} busy={p.busy} onRun={() => void bt.run()} onClose={bt.close} />}
        {sh.confirm && <DecomposeDialog count={sh.confirm.count} busy={sh.busy !== null} onConfirm={() => void sh.confirmReplace()} onClose={sh.closeConfirm} />}
        {p.dialog?.kind === "delete" && <DeleteDialog name={p.dialog.name} busy={p.busy} onConfirm={p.confirmDelete} onClose={() => p.setDialog(null)} />}
        {s.toast && <div className={toastCls} data-studio-toast>{t("toast_later", { action: t(`action.${s.toast}`) })}</div>}
        {planning && p.notice && <div className={toastCls} data-plan-notice>{p.notice}</div>}
      </div>
    </CockpitShell>
  )
}
