import { api } from "@/shared/api-client"

export interface ScratchpadData {
  user_content: string
  agent_content: string
}

const BASE = "/modules/scratchpad"

export const scratchpadApi = {
  get: () => api.get<ScratchpadData>(BASE),
  saveUser: (content: string) => api.put<{ saved: boolean }>(BASE, { content }),
  clearAgent: () => api.delete<{ cleared: boolean }>(`${BASE}/agent`),
}
