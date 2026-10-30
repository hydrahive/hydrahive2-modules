import { useState } from "react"
import { useTranslation } from "react-i18next"
import { CockpitShell } from "@/features/cockpit/CockpitShell"
import { CockpitTopbar } from "@/features/cockpit/CockpitTopbar"
import { BatchDialog } from "./BatchDialog"
import { BatchMenu } from "./BatchMenu"
import { BatchStatus } from "./BatchStatus"
import { CutInspector } from "./CutInspector"
import { CutPreview } from "./CutPreview"
import { CutSound } from "./CutSound"
import { editAction } from "./cutKeys"
import { FromPlanDialog } from "./FromPlanDialog"
import { FreeForm } from "./FreeForm"
import { FreeGallery } from "./FreeGallery"
import { GenerateSideBar } from "./GenerateSideBar"
import { DecomposeDialog } from "./DecomposeDialog"
import { DeleteDialog } from "./DeleteDialog"
import { DeliverPanel } from "./DeliverPanel"
import { DraftDialog } from "./DraftDialog"
import { ImportDialog } from "./ImportDialog"
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
import { appendNotice } from "./cutWiring"
import { CutArea } from "./CutArea"
import { CutTimeline } from "./CutTimeline"
import { followView } from "./cutLogic"
import { MusicForm } from "./MusicForm"
import { useMusic } from "./useMusic"
import { MixInspector } from "./MixInspector"
import { editing, filmWs, useCutWorkspace } from "./useCutWorkspace"
import { useSubtitleWorkspace } from "./useSubtitleWorkspace"
import { clipsOf, findClip } from "./timelineApi"
import { useDeliver } from "./useDeliver"
import { useMediaTools } from "./useMediaTools"
import { useDraft } from "./useDraft"
import { useFree } from "./useFree"
import { useModelCatalogs } from "./modelCatalog"
import { useGuide } from "./useGuide"
import { WorkspaceIntro } from "./WorkspaceIntro"
import { useJobs } from "./useJobs"
import { useShots } from "./useShots"
import { useUploads } from "./useUploads"
import { useStudioState } from "./useStudioState"
import type { Workspace } from "./workspaces"

const toastCls = "pointer-events-none fixed bottom-6 left-1/2 z-[80] -translate-x-1/2 rounded-[4px] border border-[rgb(var(--hh-s-rand-hover,70_97_127))] bg-[rgb(var(--hh-s-tief,14_20_32))] px-3 py-1.5 text-xs text-[#c3ccdd]"

/** Studio: Planen und Erzeugen arbeiten auf dem Drehbuch, Schneiden, Ton, Untertitel und Ausgabe auf der Schnittfassung. */
export function StudioPage() {
  const { t } = useTranslation("studio")
  const lib = useLibrary()
  const [workspace, setWorkspace] = useState<Workspace>("plan")
  const [stamp, setStamp] = useState("")                        // Drehbuch/Schnitt geändert → Fortschritt neu
  const guide = useGuide(lib.projectId, workspace, setWorkspace, stamp)
  const mixing = workspace === "audio"
  const { cut, every, mixer, cp, waves, ed } = useCutWorkspace(lib.projectId, workspace)
  const editKeys = (a: Parameters<typeof editAction>[0]) => { const x = editAction(a); if (x) ed.run(x); return !!x }
  const changeWs = (w: Workspace) => { if (editing(workspace) && !editing(w)) void ed.flush(); if (workspace === "subtitles" && w !== "subtitles") void sub.flush(); setWorkspace(w) }   // verlassen → sofort speichern
  // Im Reiter „Schneiden“ steuern die Tasten Film und Schnitt. Ist ein Medium aus der Bibliothek gewählt, spielt die
  // Vorschau das Medium – dann bleibt das Abspielen bei ihm, Teilen/Löschen/Rückgängig wirken weiter auf den Schnitt.
  const subbing = workspace === "subtitles"
  const p = usePlan(lib.projectId, workspace === "plan" || workspace === "generate" || workspace === "deliver" || subbing)  // Format, Sprache
  const { st, sub } = useSubtitleWorkspace(lib.projectId, subbing, p.plan, { time: cp.time, view: followView(cut.view, cp.time, cp.total),
    onSeek: cp.seek }, (x) => cut.setNotice(x))
  const s = useStudioState(lib.items, workspace, changeWs, (item) => (subbing ? (item ? { edit: st.keys } : { ...cp, edit: st.keys })
    : !editing(workspace) ? null : item ? { edit: editKeys, toggleSnap: ed.toggleSnap } : { ...cp, edit: editKeys, toggleSnap: ed.toggleSnap }))
  const planning = s.workspace === "plan"
  const generating = s.workspace === "generate"
  const shotsWs = planning || generating                       // beide arbeiten auf dem Drehbuch
  const cutting = filmWs(s.workspace) && !s.item
  const delivering = s.workspace === "deliver"
  const nextStamp = `${p.rev}:${cut.timeline?.revision ?? ""}:${every.length}`
  if (nextStamp !== stamp) setStamp(nextStamp)                   // beim Rendern abgeglichen, kein Effect nötig
  const plan = { ...p, select: (x: Parameters<typeof p.select>[0]) => { s.clearMedia(); p.select(x) } }   // Auswahl im Drehbuch löst das Medium ab
  const up = useUploads(lib.projectId, p, () => void lib.reload(), (x) => (shotsWs ? p.setNotice(x) : cut.setNotice(x)))
  const library = <LibraryPanel items={lib.items} loading={lib.loading} error={lib.error} truncated={lib.truncated} selected={s.mediaId}
    onSelect={s.selectMedia} onUpload={lib.projectId ? up.library : undefined} uploading={up.busy} />
  const jobs = useJobs(lib.projectId, shotsWs || delivering, () => { void p.reload(); void lib.reload(); void guide.reload() })   // fertig → Shot + Bibliothek + Fortschritt neu
  const sh = useShots(plan, lib.projectId, () => void jobs.reload())
  const bt = useBatch(plan, lib.projectId, jobs.jobs, () => void jobs.reload())
  const dv = useDeliver(plan, lib.projectId, delivering, jobs.jobs, jobs.reload, () => void lib.reload())
  const dr = useDraft(plan, lib.projectId, () => void bt.open("decompose_all"))
  const books = guide.overview?.books ?? 0
  const fr = useFree(plan, lib.projectId, p.plan, () => { void jobs.reload(); void lib.reload(); void p.reload(); void guide.reload() })
  const freeOpen = generating && fr.open && !s.item
  const imageCatalog = useModelCatalogs(freeOpen).image
  const freeJob = jobs.jobs.find((j) => j.kind === "free_images") ?? null
  const scene = sh.scene
  /** Platzhalter → zum Shot im „Planen“ springen, dort wird er erzeugt. */
  const toPlan = (c: { scene_id: string; shot_id: string }) => {
    s.setWorkspace("plan")
    p.select({ kind: "shot", sceneId: c.scene_id, id: c.shot_id })
  }
  const md = useMediaTools({ projectId: lib.projectId, item: s.item, clearMedia: s.clearMedia, reloadAll: () => [lib, p, guide, cut, dv].forEach((x) => void x.reload()),
    openElement: (id) => { s.setWorkspace("plan"); void p.reload(); p.select({ kind: "element", id }) }, notice: (x) => (shotsWs || delivering ? p.setNotice(x) : cut.setNotice(x)), planNotice: p.setNotice })
  const reload = () => { void lib.reload(); void guide.reload(); if (shotsWs) void p.reload(); if (editing(s.workspace)) void cut.reload() }
  const mu = useMusic(lib.projectId, editing(s.workspace), ed.addMusic, (x) => cut.setNotice(x), () => void lib.reload())
  const selShot = p.selection?.kind === "shot" ? p.selection : null
  return (
    <CockpitShell title={t("title")} className="flex h-full min-h-0 flex-col overflow-hidden bg-[rgb(var(--hh-s-grund,8_11_17))]" hideHeader>
      <CockpitTopbar active="/studio" context={t("title")} />
      <div className="relative flex min-h-0 flex-1 flex-col text-[#e8eef8]" data-studio-root data-studio-ws={s.workspace}>
        <StudioHeader projects={lib.projects} projectId={lib.projectId} onProject={lib.setProjectId} onReload={reload}
          workspace={s.workspace} onWorkspace={s.setWorkspace} onCommand={() => s.setDialog("command")} onHelp={() => s.setDialog("help")} running={jobs.running}
          batch={shotsWs && bt.active ? <BatchStatus job={bt.active} cancelling={bt.cancelling} onCancel={bt.cancel} /> : undefined}
          progress={<ProgressBar overview={guide.overview} onGo={s.setWorkspace} />} />
        <WorkspaceIntro workspace={s.workspace} open={guide.introOpen} onToggle={guide.toggleIntro} onGo={s.setWorkspace} />
        {delivering ? (
          <div className="min-h-0 flex-1">
            <DeliverPanel clips={every} aspect={p.plan?.screenplay.aspect_ratio ?? "16:9"} renders={dv.renders} queue={dv.queue} cancelling={dv.cancelling} onCancel={dv.cancel} error={p.error}
              busy={p.busy} onRender={() => void dv.start()} onCut={() => s.setWorkspace("edit")}
              subtitleLanguages={dv.subtitleLanguages} withSubtitles={dv.withSubtitles} onWithSubtitles={dv.setWithSubtitles}
              preset={dv.preset} onPreset={dv.setPreset} onDeleteFilm={(r) => md.ask(r.rel, (r.created_at || r.name).slice(0, 16).replace("T", " "))} />
          </div>
        ) : <>
        <div className="flex min-h-0 flex-col" style={{ flex: `${100 - s.layout.timeline} 1 0` }}>
          <div className="flex min-h-0 flex-1">
            <div className="min-w-0 border-r border-[rgb(var(--hh-s-rand,42_54_75))] bg-[#0b111b]" style={{ width: `${s.layout.library}%` }}>
              {subbing ? st.left : planning ? <PlanSidebar p={plan} library={library} books={books} onIdea={dr.openIdea} onBook={dr.openBook} />
                : generating ? (
                  <div className="flex h-full min-h-0 flex-col">
                    <GenerateSideBar plan={p.plan} free={fr.open} busy={p.busy} onFree={fr.toggle} />
                    <div className="min-h-0 flex-1">
                      <ShotList plan={p.plan} jobs={jobs.jobs} selected={fr.open ? null : selShot?.id ?? null} onPlan={() => s.setWorkspace("plan")}
                        onSelect={(sceneId, id) => { fr.close(); plan.select({ kind: "shot", sceneId, id }) }} />
                    </div>
                  </div>
                )
                : library}
            </div>
            <Splitter dir="x" label={t("resize_library")} onDrag={(d) => s.drag("library", d)} />
            <div className="min-w-0 flex-1">
              {freeOpen
                ? <div className="flex h-full min-h-0 justify-center overflow-y-auto p-3" data-studio-panel="preview">
                    <FreeGallery items={lib.items} plan={p.plan} busy={p.busy} onAssign={(sc, sh, rel) => void fr.assign(sc, sh, rel)} onTimeline={(rel) => void fr.timeline(rel)} onDelete={md.askItem} />
                  </div>
                : shotsWs && !s.item
                ? <PlanCenter plan={p.plan} selection={p.selection} atelier={!!guide.overview?.atelier} books={books} busy={p.busy}
                    onStart={() => void p.addScene()} onImport={() => p.setDialog({ kind: "import" })} onHead={() => plan.select({ kind: "head" })}
                    onIdea={dr.openIdea} onBook={dr.openBook} />
                : cutting ? <CutPreview clips={cut.clips} base={cut.timeline?.base ?? ""} fps={cut.timeline?.fps ?? 25} time={cp.time} total={cp.total}
                    playing={cp.playing} current={cp.current} onSeek={cp.seek} onPlay={cp.toggle} bindVideo={cp.bindVideo}
                    overlay={subbing ? st.overlay : undefined} sound={<CutSound voice={clipsOf(cut.timeline, "A1")} music={clipsOf(cut.timeline, "A2")} mixer={mixer} base={cut.timeline?.base ?? ""}
                      time={cp.time} playing={cp.playing} rate={cp.rate} />} />
                : <PreviewPanel item={s.item} bind={s.player.bind} time={s.item ? s.player.time : 0} duration={s.player.duration}
                    playing={s.player.playing} onPlay={s.player.toggle} onSeek={s.seek} />}
            </div>
            <Splitter dir="x" label={t("resize_inspector")} onDrag={(d) => s.drag("inspector", d)} />
            <div className="min-w-0 border-l border-[rgb(var(--hh-s-rand,42_54_75))] bg-[#0b111b]" style={{ width: `${s.layout.inspector}%` }}>
              {subbing && !s.item ? st.right : planning && !s.item ? <PlanInspector p={plan} shots={sh} jobs={jobs.jobs} images={lib.items.filter((i) => i.kind === "image")} upload={up} onDeleteMedia={md.ask} />
                : freeOpen ? <FreeForm form={fr.form} catalog={imageCatalog} images={lib.items.filter((i) => i.kind === "image")} job={freeJob}
                    busy={p.busy} onChange={fr.setForm} onRun={() => void fr.run()} />
                : generating && !s.item ? (selShot ? <PlanInspector p={plan} shots={sh} jobs={jobs.jobs} images={lib.items.filter((i) => i.kind === "image")} onDeleteMedia={md.ask} /> : <GenerateHint />)
                : mixing && !s.item ? <MixInspector clip={cut.clip} onChange={(v) => cut.clip && ed.onClipMix(cut.clip.id, v)} />
                : editing(s.workspace) ? <CutInspector clip={s.item ? null : cut.clip} onPlan={toPlan} media={s.item}
                    mix={cut.clip?.kind === "audio" ? (v) => cut.clip && ed.onClipMix(cut.clip.id, v) : undefined}
                    onUnbind={() => cut.clip && ed.unbindVoice(cut.clip.id)} onDeleteMedia={md.askItem} onCreateElement={md.createElement}
                    onAppend={() => { const k = appendNotice(s.item, ed.addMedia); if (k) { s.clearMedia(); cut.setNotice(t(k)) } }} />
                : <MediaInfo item={s.item} onDelete={md.askItem} onCreateElement={md.createElement} />}
            </div>
          </div>
        </div>
        <Splitter dir="y" label={t("resize_timeline")} onDrag={(d) => s.drag("timeline", d)} />
        <div className="min-h-0 border-t border-[rgb(var(--hh-s-rand,42_54_75))] bg-[#0b111b]" style={{ flex: `${s.layout.timeline} 1 0` }}>
          {shotsWs
            ? <StoryboardPanel scene={scene} base={p.plan?.base ?? ""} selected={p.selection?.kind === "shot" ? p.selection.id : null} busy={sh.busy}
                runningShots={jobs.jobs.filter((j) => j.status === "running" || j.status === "queued").map((j) => j.target)}
                onSelect={(id) => { if (scene) plan.select({ kind: "shot", sceneId: scene.id, id }) }}
                batchMenu={<BatchMenu running={!!bt.active} onPick={(k) => void bt.open(k)} />}
                onAdd={() => void sh.add()} onMove={(id, d) => void sh.move(id, d)} onDecompose={() => void sh.decompose()} />
            : editing(s.workspace)
              ? <CutArea mixing={mixing} cut={cut} cp={cp} ed={ed} mixer={mixer} every={every} waves={waves.peaks} items={lib.items}
                  onNotice={(k) => cut.setNotice(t(k))} onSelect={(id) => { s.clearMedia(); cut.select(id); const c = findClip(cut.timeline, id); if (c) cp.seek(c.start) }}
                  onMusic={mu.show} musicRunning={mu.running} />
            : subbing ? <CutTimeline timeline={cut.timeline} base={cut.timeline?.base ?? ""} time={cp.time} view={followView(cut.view, cp.time, cp.total)}
                selected={null} busy={cut.busy} onView={cut.setView} onSeek={cp.seek} onSelect={() => {}} onFromPlan={cut.fromPlan} mixer={mixer} extra={st.track} />
            : null}
        </div>
        </>}
        {s.dialog === "help" && <ShortcutHelp onClose={() => s.setDialog(null)} onGo={s.setWorkspace} />}
        {s.dialog === "command" && <CommandPalette onClose={() => s.setDialog(null)} onRun={s.run} />}
        {p.dialog?.kind === "import" && p.preview && <ImportDialog preview={p.preview} busy={p.busy} onRun={() => void p.runImport()} onClose={() => p.setDialog(null)} />}
        {mu.open && <MusicForm defaults={mu.defaults} job={mu.job} busy={mu.busy} onRun={(r) => void mu.run(r)} onClose={mu.close} />}
        <DraftDialog d={dr} append={!!p.plan?.scenes.length} />
        {bt.dialog && <BatchDialog kind={bt.dialog.kind} preview={bt.dialog.preview} busy={p.busy} onRun={() => void bt.run()} onClose={bt.close} />}
        {st.dialog}
        {md.dialogs}
        {cut.confirm && <FromPlanDialog count={cut.clips.length} busy={cut.busy} onConfirm={cut.confirmReplace} onClose={cut.closeConfirm} />}
        {sh.confirm && <DecomposeDialog count={sh.confirm.count} busy={sh.busy !== null} onConfirm={() => void sh.confirmReplace()} onClose={sh.closeConfirm} />}
        {p.dialog?.kind === "delete" && <DeleteDialog name={p.dialog.name} busy={p.busy} onConfirm={p.confirmDelete} onClose={() => p.setDialog(null)} />}
        {s.toast && <div className={toastCls} data-studio-toast>{t("toast_later", { action: t(`action.${s.toast}`) })}</div>}
        {(shotsWs || delivering) && p.notice && <div className={toastCls} data-plan-notice>{p.notice}</div>}
        {filmWs(s.workspace) && cut.notice && <div className={toastCls} data-cut-notice>{cut.notice}</div>}
      </div>
    </CockpitShell>
  )
}
