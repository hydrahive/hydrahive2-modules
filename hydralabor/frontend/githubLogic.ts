/** Platzhalter. */
export interface GitHubState { connected: boolean; login: string; pending: boolean; configured: boolean }
export interface DeviceCode { user_code: string; verification_uri: string; expires_in: number }
export interface Submission { id: number; kind: "pr" | "issue"; target: string; title: string; number: number; url: string; state: string; created_at: string }
export const SUBMIT_STEPS: string[] = []
export const submitProgress = (_k: string) => -1
export const submitResult = (_o: Record<string, unknown>): { number: number; url: string } | null => ({ number: -1, url: "" })
