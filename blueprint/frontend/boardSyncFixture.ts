// Gestellter Server für die Tests des Abgleichs (boardSync.test.ts, boardSyncRemote.test.ts).
import { vi } from "vitest"
import { graphSignature } from "./boardGraph"
import { BoardSync } from "./boardSync"
import type { Board, BPNode, Graph, SyncApi, SyncStatus } from "./types"

export const node = (id: string, label = id): BPNode =>
  ({ id, type: "flowNode", position: { x: 0, y: 0 }, data: { kind: "flow", subtype: "action", label, note: "" } }) as BPNode
export const graph = (...ids: string[]): Graph => ({ nodes: ids.map((id) => node(id)), edges: [] })
export const raw = (...ids: string[]) => graphSignature(graph(...ids))
export const failure = (status: number, code?: string) => Object.assign(new Error(code ?? "kaputt"), { status, code })
export const tick = (ms: number) => vi.advanceTimersByTimeAsync(ms)

export function setup(start: Partial<Board> = {}) {
  const server: Board = {
    id: 7, name: "Board", project_id: null, created_at: "", updated_at: "", revision: 3, graph_json: raw("a"),
    proposal_json: null, proposal_note: null, proposal_at: null, ...start,
  }
  const fail: { get?: unknown; update?: unknown; state?: unknown } = {}
  const api = {
    get: vi.fn(async () => { if (fail.get) throw fail.get; return { ...server } }),
    state: vi.fn(async () => {
      if (fail.state) throw fail.state
      return { revision: server.revision, proposal_at: server.proposal_at }
    }),
    update: vi.fn(async (_id: number, patch: { graph_json?: string; base_revision?: number; keep_previous?: boolean }) => {
      if (fail.update) throw fail.update
      if (patch.base_revision !== undefined && patch.base_revision !== server.revision) throw failure(409, "board_changed")
      if (patch.graph_json !== undefined && patch.graph_json !== server.graph_json) {
        server.graph_json = patch.graph_json
        server.revision += 1
      }
      return { ...server }
    }),
  } satisfies SyncApi
  const seen = { graphs: [] as string[], status: [] as SyncStatus[], boards: [] as Board[] }
  let visible = true
  const sync = new BoardSync(7, api, {
    onGraph: (g) => seen.graphs.push(g.nodes.map((n) => n.id).join(",")),
    onStatus: (s) => seen.status.push(s),
    onBoard: (b) => seen.boards.push(b),
  }, { isVisible: () => visible })
  /** Der Agent oder ein anderes Fenster ändert die Fassung auf dem Server. */
  const elsewhere = (...ids: string[]) => { server.graph_json = raw(...ids); server.revision += 1 }
  return { server, api, fail, seen, sync, elsewhere, hide: (hidden: boolean) => { visible = !hidden } }
}
