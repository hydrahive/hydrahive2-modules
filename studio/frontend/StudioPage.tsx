import { useTranslation } from "react-i18next"
import { CockpitShell } from "@/features/cockpit/CockpitShell"
import { CockpitTopbar } from "@/features/cockpit/CockpitTopbar"
import { InspectorPanel } from "./InspectorPanel"
import { LibraryPanel } from "./LibraryPanel"
import { PreviewPanel } from "./PreviewPanel"
import { Splitter } from "./Splitter"
import { StoryboardPanel } from "./StoryboardPanel"
import { CommandPalette, ShortcutHelp } from "./StudioDialogs"
import { StudioHeader } from "./StudioHeader"
import { TimelinePanel } from "./TimelinePanel"
import { useLibrary } from "./useLibrary"
import { useStudioState } from "./useStudioState"

/** Studio (Etappe 1): echte Bibliothek + Vorschau. Zeitleiste und Storyboard sind noch Beispieldaten. */
export function StudioPage() {
  const { t } = useTranslation("studio")
  const lib = useLibrary()
  const s = useStudioState(lib.items)
  const focus = s.workspace === "audio" ? "audio" : s.workspace === "subtitles" ? "subtitles" : "all"
  return (
    <CockpitShell title={t("title")} className="flex h-full min-h-0 flex-col overflow-hidden bg-[#080b11]" hideHeader>
      <CockpitTopbar active="/studio" context={t("title")} />
      <div className="flex min-h-0 flex-1 flex-col text-[#e8eef8]" data-studio-root data-studio-ws={s.workspace}>
        <StudioHeader projects={lib.projects} projectId={lib.projectId} onProject={lib.setProjectId} onReload={() => void lib.reload()}
          workspace={s.workspace} onWorkspace={s.setWorkspace} onCommand={() => s.setDialog("command")} onHelp={() => s.setDialog("help")} />
        <div className="flex min-h-0 flex-col" style={{ flex: `${100 - s.layout.timeline} 1 0` }}>
          <div className="flex min-h-0 flex-1">
            <div className="min-w-0 border-r border-[#2a364b] bg-[#0b111b]" style={{ width: `${s.layout.library}%` }}>
              <LibraryPanel items={lib.items} loading={lib.loading} error={lib.error} truncated={lib.truncated}
                selected={s.mediaId} onSelect={s.selectMedia} />
            </div>
            <Splitter dir="x" label={t("resize_library")} onDrag={(d) => s.drag("library", d)} />
            <div className="min-w-0 flex-1">
              <PreviewPanel item={s.item} bind={s.player.bind} time={s.item ? s.player.time : 0} duration={s.player.duration}
                playing={s.player.playing} onPlay={s.player.toggle} onSeek={s.seek} />
            </div>
            <Splitter dir="x" label={t("resize_inspector")} onDrag={(d) => s.drag("inspector", d)} />
            <div className="min-w-0 border-l border-[#2a364b] bg-[#0b111b]" style={{ width: `${s.layout.inspector}%` }}>
              <InspectorPanel workspace={s.workspace} clipId={s.clipId} item={s.item} />
            </div>
          </div>
        </div>
        <Splitter dir="y" label={t("resize_timeline")} onDrag={(d) => s.drag("timeline", d)} />
        <div className="min-h-0 border-t border-[#2a364b] bg-[#0b111b]" style={{ flex: `${s.layout.timeline} 1 0` }}>
          {s.workspace === "plan"
            ? <StoryboardPanel selected={s.clipId} onSelect={s.selectClip} />
            : <TimelinePanel time={s.time} view={s.view} snap={s.snap} selected={s.clipId} focus={focus}
                onView={s.setView} onSeek={s.seek} onSelect={s.selectClip} onSnap={s.toggleSnap} />}
        </div>
        {s.dialog === "help" && <ShortcutHelp onClose={() => s.setDialog(null)} />}
        {s.dialog === "command" && <CommandPalette onClose={() => s.setDialog(null)} onRun={s.run} />}
        {s.toast && (
          <div className="pointer-events-none fixed bottom-6 left-1/2 z-[80] -translate-x-1/2 rounded-[4px] border border-[#46617f] bg-[#0e1420] px-3 py-1.5 text-xs text-[#c3ccdd]" data-studio-toast>
            {t("toast_later", { action: t(`action.${s.toast}`) })}
          </div>
        )}
      </div>
    </CockpitShell>
  )
}
