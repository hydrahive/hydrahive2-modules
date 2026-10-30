import type { LabState } from "./logic"
export function LabPanel(_p: { s: LabState; busy: boolean; msg: string | null; onJob: (j: string) => void
  onPower: (a: "start" | "stop") => void; onAskReset: () => void; onAskRemove: () => void }) {
  return <div />
}
