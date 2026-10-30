import type { Checks, LabState, Limits, Model } from "./logic"
export function WizardView(_p: { s: LabState; checks: Checks | null; models: Model[]; model: string; limits: Limits; busy: boolean
  msg: string | null; onCheck: () => void; onModel: (m: string) => void; onLimits: (l: Limits) => void; onCreate: () => void }) {
  return <div />
}
