export interface Program { mode: string; ref_id: string; notice: string; name: string; count: number; position: number; can_moderate: boolean }
export const DECADES: number[] = []
export function programLine(_p: Program): { key: string; opts?: Record<string, unknown> } { throw new Error("NotImplemented") }
export function programErrorKey(_e: unknown): string { throw new Error("NotImplemented") }
export function rulesSummary(_r: unknown): string[] { throw new Error("NotImplemented") }
export function emptyRules(): Record<string, unknown> { throw new Error("NotImplemented") }
