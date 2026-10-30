import { api } from "@/shared/api-client"
import { BASE, type Checks, type LabState, type Limits, type Model } from "./logic"

export const getState = () => api.get<LabState>(`${BASE}/state`)
export const getModels = () => api.get<{ items: Model[] }>(`${BASE}/models`)
export const runChecks = (l: Limits) => api.post<Checks>(`${BASE}/checks`, l)
export const createLab = (model: string, l: Limits) => api.post<{ started: string }>(`${BASE}/create`, { model, ...l })
export const startJob = (job: "reset" | "probe" | "test") => api.post<{ started: string }>(`${BASE}/${job}`, {})
export const removeLab = () => api.post<{ started: string }>(`${BASE}/remove`, { confirm: "LABOR" })
export const power = (a: "start" | "stop") => api.post<{ running: boolean }>(`${BASE}/${a}`, {})
export const openChat = () => api.post<{ session_id: string; url: string }>(`${BASE}/chat`, {})
