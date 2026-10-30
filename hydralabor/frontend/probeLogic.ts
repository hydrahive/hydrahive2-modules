export interface ProbeState { built: boolean; running: boolean; user: string; password: string; port: number; open: boolean }
export const PROBE_JOBS: string[] = []
export function probeView(_p: ProbeState, _job: string): string { throw new Error("NotImplemented") }
