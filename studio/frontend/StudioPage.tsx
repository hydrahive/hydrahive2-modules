import { useState } from "react"
import { useTranslation } from "react-i18next"
import { CockpitShell } from "@/features/cockpit/CockpitShell"
import { CockpitTopbar } from "@/features/cockpit/CockpitTopbar"
import { BatchDialog } from "./BatchDialog"
import { BatchMenu } from "./BatchMenu"
import { BatchStatus } from "./BatchStatus"
import { followView } from "./cutLogic"
import { CutInspector } from "./CutInspector"
import { CutPreview } from "./CutPreview"
import { CutTimeline } from "./CutTimeline"
import { CutToolbar } from "./CutToolbar"
import { editAction } from "./cutKeys"
import { FromPlanDialog } from "./FromPlanDialog"
import { DecomposeDialog } from "./DecomposeDialog"
import { DeleteDialog } from "./DeleteDialog"
import { DraftDialog } from "./DraftDialog"
import { ImportDialog } from "./ImportDialog"
import { ComingSoon } from "./ComingSoon"
import { GenerateHint } from "./GenerateHint"
import { MediaInfo } from "./MediaInfo"
import { ShotList } from "./ShotList"
import { LibraryPanel } from "./LibraryPanel"
import { PlanInspector } from "./PlanInspector"
import { PlanCenter } from "./PlanCenter"
import { ProgressBar } from "./ProgressBar"
import { PlanSidebar } from "./PlanSidebar"
import { PreviewPanel } from "./PreviewPanel"
import { Splitter } from "./Splitter"
import { StoryboardPanel } from "./StoryboardPanel"
import { CommandPalette, ShortcutHelp } from "./StudioDialogs"
import { StudioHeader } from "./StudioHeader"
import { useLibrary } from "./useLibrary"
import { usePlan } from "./usePlan"
import { useBatch } from "./useBatch"
import { useCut } from "./useCut"
import { useCutEdit } from "./useCutEdit"
import { useCutPlayer } from "./useCutPlayer"
import { useDraft } from "./useDraft"
import { useGuide } from "./useGuide"
import { WorkspaceIntro } from "./WorkspaceIntro"
import { useJobs } from "./useJobs"
import { useShots } from "./useShots"
import { useStudioState } from "./useStudioState"
import type { Workspace } from "./workspaces"

const toastCls = "pointer-events-none fixed bottom-6 left-1/2 z-[80] -translate-x-1/2 rounded-[4px] border border-[#46617f] bg-[#0e1420] px-3 py-1.5 text-xs text-[#c3ccdd]"

/** Studio: Planen und Erzeugen arbeiten auf dem Drehbuch, Schneiden auf der Schnittfassung. Ton, Untertitel, Ausgabe kommen noch. */
export function StudioPage() {
  const { t } = useTranslation("studio")
  const lib = useLibrary()
  const [workspace, setWorkspace] = useState<Workspace>("plan")
  const [stamp, setStamp] = useState("")                        // Drehbuch/Schnitt geändert → Fortschritt neu
  const guide = useGuide(lib.projectId, workspace, setWorkspace, stamp)
  const cut = useCut(lib.projectId, workspace === "edit")
  const cp = useCutPlayer(cut.clips)
  const ed = useCutEdit(lib.projectId, cut.timeline, cut.setTimeline, cut.selected, cut.select, cp.time)
  const editKeys = (a: Parameters<typeof editAction>[0]) => { const x = editAction(a); if (x) ed.run(x); return !!x }
  const changeWs = (w: Workspace) => { if (workspace === "edit" && w !== "edit") void ed.flush(); setWorkspace(w) }   // verlassen → sofort speichern
  // Im Reiter „Schneiden“ steuern die Tasten Film und Schnitt. Ist ein Medium aus der Bibliothek gewählt, spielt die
  // Vorschau das Medium – dann bleibt das Abspielen bei ihm, Teilen/Löschen/Rückgängig wirken weiter auf den Schnitt.
  const s = useStudioState(lib.items, workspace, changeWs,
    (item) => (workspace !== "edit" ? null : item ? { edit: editKeys, toggleSnap: ed.toggleSnap } : { ...cp, edit: editKeys, toggleSnap: ed.toggleSnap }))
  const planning = s.workspace === "plan"
  const generating = s.workspace === "generate"
  const shotsWs = planning || generating                       // beide arbeiten auf dem Drehbuch
  const cutting = s.workspace === "edit" && !s.item
  const soon = s.workspace === "audio" || s.workspace === "subtitles" || s.workspace === "deliver" ? s.workspace : null
  const p = usePlan(lib.projectId, shotsWs)
  const nextStamp = `${p.rev}:${cut.timeline?.revision ?? ""}:${cut.clips.length}`
  if (nextStamp !== stamp) setStamp(nextStamp)                   // beim Rendern abgeglichen, kein Effect nötig
  const plan = { ...p, select: (x: Parameters<typeof p.select>[0]) => { s.clearMedia(); p.select(x) } }   // Auswahl im Drehbuch löst das Medium ab
  const library = <LibraryPanel items={lib.items} loading={lib.loading} error={lib.error} truncated={lib.truncated} selected={s.mediaId} onSelect={s.selectMedia} />
  const jobs = useJobs(lib.projectId, shotsWs, () => { void p.reload(); void lib.reload(); void guide.reload() })   // fertig → Shot + Bibliothek + Fortschritt neu
  const sh = useShots(plan, lib.projectId, () => void jobs.reload())
  const bt = useBatch(plan, lib.projectId, jobs.jobs, () => void jobs.reload())
  const dr = useDraft(plan, lib.projectId, () => void bt.open("decompose_all"))
  const books = guide.overview?.books ?? 0
  const scene = sh.scene
  /** Platzhalter → zum Shot im „Planen“ springen, dort wird er erzeugt. */
  const toPlan = (c: { scene_id: string; shot_id: string }) => {
    s.setWorkspace("plan")
    p.select({ kind: "shot", sceneId: c.scene_id, id: c.shot_id })
  }
  const reload = () => { void lib.reload(); void guide.reload(); if (shotsWs) void p.reload(); if (s.workspace === "edit") void cut.reload() }
  const selShot = p.selection?.kind === "shot" ? p.selection : null
  return (
    <CockpitShell title={t("title")} className="flex h-full min-h-0 flex-col overflow-hidden bg-[#080b11]" hideHeader>
      <CockpitTopbar active="/studio" context={t("title")} />
      <div className="relative flex min-h-0 flex-1 flex-col text-[#e8eef8]" data-studio-root data-studio-ws={s.workspace}>
        <StudioHeader projects={lib.projects} projectId={lib.projectId} onProject={lib.setProjectId} onReload={reload}
          workspace={s.workspace} onWorkspace={s.setWorkspace} onCommand={() => s.setDialog("command")} onHelp={() => s.setDialog("help")} running={jobs.running}
          batch={shotsWs && bt.active ? <BatchStatus job={bt.active} cancelling={bt.cancelling} onCancel={bt.cancel} /> : undefined}
          progress={<ProgressBar overview={guide.overview} onGo={s.setWorkspace} />} />
        <WorkspaceIntro workspace={s.workspace} open={guide.introOpen} onToggle={guide.toggleIntro} />
        <div className="flex min-h-0 flex-col" style={{ flex: `${100 - s.layout.timeline} 1 0` }}>
          <div className="flex min-h-0 flex-1">
            <div className="min-w-0 border-r border-[#2a364b] bg-[#0b111b]" style={{ width: `${s.layout.library}%` }}>
              {planning ? <PlanSidebar p={plan} library={library} books={books} onIdea={dr.openIdea} onBook={dr.openBook} />
                : generating ? <ShotList plan={p.plan} jobs={jobs.jobs} selected={selShot?.id ?? null} onPlan={() => s.setWorkspace("plan")}
                    onSelect={(sceneId, id) => plan.select({ kind: "shot", sceneId, id })} />
                : library}
            </div>
            <Splitter dir="x" label={t("resize_library")} onDrag={(d) => s.drag("library", d)} />
            <div className="min-w-0 flex-1">
              {shotsWs && !s.item
                ? <PlanCenter plan={p.plan} selection={p.selection} atelier={!!guide.overview?.atelier} books={books} busy={p.busy}
                    onStart={() => void p.addScene()} onImport={() => p.setDialog({ kind: "import" })} onHead={() => plan.select({ kind: "head" })}
                    onIdea={dr.openIdea} onBook={dr.openBook} />
                : cutting ? <CutPreview clips={cut.clips} base={cut.timeline?.base ?? ""} fps={cut.timeline?.fps ?? 25} time={cp.time} total={cp.total}
                    playing={cp.playing} current={cp.current} onSeek={cp.seek} onPlay={cp.toggle} bindVideo={cp.bindVideo} />
                : <PreviewPanel item={s.item} bind={s.player.bind} time={s.item ? s.player.time : 0} duration={s.player.duration}
                    playing={s.player.playing} onPlay={s.player.toggle} onSeek={s.seek} />}
            </div>
            <Splitter dir="x" label={t("resize_inspector")} onDrag={(d) => s.drag("inspector", d)} />
            <div className="min-w-0 border-l border-[#2a364b] bg-[#0b111b]" style={{ width: `${s.layout.inspector}%` }}>
              {planning && !s.item ? <PlanInspector p={plan} shots={sh} jobs={jobs.jobs} images={lib.items.filter((i) => i.kind === "image")} />
                : generating && !s.item ? (selShot ? <PlanInspector p={plan} shots={sh} jobs={jobs.jobs} images={lib.items.filter((i) => i.kind === "image")} /> : <GenerateHint />)
                : s.workspace === "edit" ? <CutInspector clip={s.item ? null : cut.clip} onPlan={toPlan} media={s.item}
                    onAppend={() => { if (s.item && ed.addMedia(s.item)) { s.clearMedia(); cut.setNotice(t("cut_notice_appended")) } }} />
                : <MediaInfo item={s.item} />}
            </div>
          </div>
        </div>
        <Splitter dir="y" label={t("resize_timeline")} onDrag={(d) => s.drag("timeline", d)} />
        <div className="min-h-0 border-t border-[#2a364b] bg-[#0b111b]" style={{ flex: `${s.layout.timeline} 1 0` }}>
          {shotsWs
            ? <StoryboardPanel scene={scene} base={p.plan?.base ?? ""} selected={p.selection?.kind === "shot" ? p.selection.id : null} busy={sh.busy}
                runningShots={jobs.jobs.filter((j) => j.status === "running" || j.status === "queued").map((j) => j.target)}
                onSelect={(id) => { if (scene) plan.select({ kind: "shot", sceneId: scene.id, id }) }}
                batchMenu={<BatchMenu running={!!bt.active} onPick={(k) => void bt.open(k)} />}
                onAdd={() => void sh.add()} onMove={(id, d) => void sh.move(id, d)} onDecompose={() => void sh.decompose()} />
            : s.workspace === "edit"
              ? <CutTimeline timeline={cut.timeline} base={cut.timeline?.base ?? ""} time={cp.time} view={followView(cut.view, cp.time, cp.total)}
                  selected={cut.selected} busy={cut.busy} onView={cut.setView} onSeek={cp.seek} onFromPlan={cut.fromPlan}
                  toolbar={<CutToolbar save={ed.save} selected={cut.selected} canUndo={ed.canUndo} canRedo={ed.canRedo} canSplit={ed.canSplit}
                    snap={ed.snap} onAction={ed.run} onSnap={ed.toggleSnap} onReload={() => void cut.reload()} />}
                  edit={{ onMove: ed.move, onTrim: ed.onTrim, dropAt: null, snapTo: ed.snapTo,
                    onDrop: (mediaId, index) => { const it = lib.items.find((i) => i.id === mediaId); if (it && !ed.addMedia(it, index)) cut.setNotice(t("cut_no_audio_yet")) } }}
                  onSelect={(id) => { s.clearMedia(); cut.select(id); const c = cut.clips.find((x) => x.id === id); if (c) cp.seek(c.start) }} />
            : soon ? <ComingSoon workspace={soon} onCut={() => s.setWorkspace("edit")} /> : null}
        </div>
        {s.dialog === "help" && <ShortcutHelp onClose={() => s.setDialog(null)} onGo={s.setWorkspace} />}
        {s.dialog === "command" && <CommandPalette onClose={() => s.setDialog(null)} onRun={s.run} />}
        {p.dialog?.kind === "import" && p.preview && <ImportDialog preview={p.preview} busy={p.busy} onRun={() => void p.runImport()} onClose={() => p.setDialog(null)} />}
        <DraftDialog d={dr} append={!!p.plan?.scenes.length} />
        {bt.dialog && <BatchDialog kind={bt.dialog.kind} preview={bt.dialog.preview} busy={p.busy} onRun={() => void bt.run()} onClose={bt.close} />}
        {cut.confirm && <FromPlanDialog count={cut.clips.length} busy={cut.busy} onConfirm={cut.confirmReplace} onClose={cut.closeConfirm} />}
        {sh.confirm && <DecomposeDialog count={sh.confirm.count} busy={sh.busy !== null} onConfirm={() => void sh.confirmReplace()} onClose={sh.closeConfirm} />}
        {p.dialog?.kind === "delete" && <DeleteDialog name={p.dialog.name} busy={p.busy} onConfirm={p.confirmDelete} onClose={() => p.setDialog(null)} />}
        {s.toast && <div className={toastCls} data-studio-toast>{t("toast_later", { action: t(`action.${s.toast}`) })}</div>}
        {shotsWs && p.notice && <div className={toastCls} data-plan-notice>{p.notice}</div>}
        {s.workspace === "edit" && cut.notice && <div className={toastCls} data-cut-notice>{cut.notice}</div>}
      </div>
    </CockpitShell>
  )
}
