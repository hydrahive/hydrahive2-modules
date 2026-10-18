import { Fragment } from "react"
import { cueAt, type Cue } from "./subtitleLogic"

/** Aktueller Untertitel in der Vorschau – nur im Browser darübergelegt, nie im Bild (Till, 18.10.). */
export function SubtitleOverlay({ cues, time }: { cues: Cue[]; time: number }) {
  const c = cueAt(cues, time)
  if (!c) return null
  const lines = c.text.split("\n")
  return (
    <div className="pointer-events-none absolute inset-x-0 bottom-[6%] flex justify-center px-[6%]" data-sub-overlay={c.id}>
      <span className="rounded-[3px] bg-black/70 px-2 py-0.5 text-center text-[clamp(11px,2.2vw,22px)] font-semibold leading-snug text-white">
        {lines.map((l, i) => <Fragment key={i}>{i > 0 && <br />}{l}</Fragment>)}
      </span>
    </div>
  )
}
