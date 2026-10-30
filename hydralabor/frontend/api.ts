import { api } from "@/shared/api-client"
import { BASE, type Checks, type LabState, type Limits, type Model } from "./logic"
import type { ProbeState } from "./probeLogic"
import type { DeviceCode, GitHubState, Submission, Target } from "./githubLogic"

export const getState = () => api.get<LabState>(`${BASE}/state`)
export const getModels = () => api.get<{ items: Model[] }>(`${BASE}/models`)
export const runChecks = (l: Limits) => api.post<Checks>(`${BASE}/checks`, l)
export const createLab = (model: string, l: Limits) => api.post<{ started: string }>(`${BASE}/create`, { model, ...l })
export const startJob = (job: "reset" | "probe" | "test") => api.post<{ started: string }>(`${BASE}/${job}`, {})
export const removeLab = () => api.post<{ started: string }>(`${BASE}/remove`, { confirm: "LABOR" })
export const power = (a: "start" | "stop") => api.post<{ running: boolean }>(`${BASE}/${a}`, {})
export const openChat = () => api.post<{ session_id: string; url: string }>(`${BASE}/chat`, {})
export const getGitHub = () => api.get<GitHubState>(`${BASE}/github`)
export const connectGitHub = () => api.post<DeviceCode>(`${BASE}/github/connect`, {})
export const disconnectGitHub = () => api.post<GitHubState>(`${BASE}/github/disconnect`, {})
export const suggestTarget = () => api.get<{ target: Target | "" }>(`${BASE}/submit/target`)
export const startSubmit = (target: Target, title: string, body: string) =>
  api.post<{ started: string }>(`${BASE}/submit`, { target, title, body })
export const reportBug = (v: { target: Target; title: string; what: string; expected: string; steps: string }) =>
  api.post<{ number: number; url: string }>(`${BASE}/report`, v)
export const getSubmissions = () => api.get<{ items: Submission[] }>(`${BASE}/submissions`)
export const refreshSubmissions = () => api.post<{ items: Submission[] }>(`${BASE}/submissions/refresh`, {})
export const getProbe = () => api.get<ProbeState>(`${BASE}/probe`)
export const probeJob = (a: "build" | "start" | "stop") => api.post<{ started: string }>(`${BASE}/probe/${a}`, {})
export const openProbe = () => api.post<{ url: string }>(`${BASE}/probe/open`, {})
