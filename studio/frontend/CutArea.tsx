import type { LibraryItem } from "./api"
import { CutTimeline } from "./CutTimeline"
import { CutToolbar } from "./CutToolbar"
import { cutDrops } from "./cutWiring"
import { followView } from "./cutLogic"
import { MixerPanel } from "./MixerPanel"
import { countsOf, type Mixer } from "./mixLogic"
import type { TimelineClip } from "./timelineApi"
import type { useCutWorkspace } from "./useCutWorkspace"

type W = ReturnType<typeof useCutWorkspace>
interface Props {
  mixing: boolean
  cut: W["cut"]
  cp: W["cp"]
  ed: W["ed"]
  mixer: Mixer
  every: TimelineClip[]
  waves: Record<string, number[] | undefined>
  items: LibraryItem[]
  onNotice: (key: string) => void
  onSelect: (id: string) => void
  onMusic: () => void
  musicRunning: boolean
}

/** Unterer Bereich in „Schneiden“ und „Ton“: Zeitleiste, im Reiter „Ton“ mit dem Mischpult links daneben (5b). */
export function CutArea({ mixing, cut, cp, ed, mixer, every, waves, items, onNotice, onSelect, onMusic, musicRunning }: Props) {
  const timeline = (
    <CutTimeline timeline={cut.timeline} base={cut.timeline?.base ?? ""} time={cp.time} view={followView(cut.view, cp.time, cp.total)}
      selected={cut.selected} busy={cut.busy} onView={cut.setView} onSeek={cp.seek} onFromPlan={cut.fromPlan} mixer={mixer}
      toolbar={<CutToolbar save={ed.save} selected={cut.selected} canUndo={ed.canUndo} canRedo={ed.canRedo} canSplit={ed.canSplit}
        snap={ed.snap} onAction={ed.run} onSnap={ed.toggleSnap} onReload={() => void cut.reload()} />}
      {...cutDrops(items, ed, every, () => onNotice("cut_not_on_timeline"))} waveforms={waves} onSelect={onSelect} />
  )
  if (!mixing) return timeline
  return (
    <div className="flex h-full min-h-0">
      <div className="w-[420px] min-w-[340px] shrink-0 border-r border-[rgb(var(--hh-s-rand,42_54_75))]" data-mixer-area>
        <MixerPanel mixer={mixer} counts={countsOf(cut.timeline)} playing={cp.playing} onTrack={ed.onTrackMix} onDuck={ed.onDuck}
          onMusic={onMusic} musicRunning={musicRunning} />
      </div>
      <div className="min-w-0 flex-1">{timeline}</div>
    </div>
  )
}
