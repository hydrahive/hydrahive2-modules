// KI-Vorschläge: Datenform und Vergleich alt/neu (die Vorschläge selbst kommen vom Server).
// Grundregel der Spec: Ein Vorschlag ändert nichts, bis er angenommen wird.

export type SuggestAction = "rewrite" | "expand" | "shorten" | "continue"

export interface Suggestion {
  id: string
  sceneId: string
  action: SuggestAction
  /** Markierter Originaltext (bei „continue“ leer). */
  original: string
  proposal: string
  /** Position im Editor (ProseMirror), nur gültig solange die Szene unverändert ist. */
  from: number
  to: number
  createdAt: string
  /** Modell, das den Vorschlag gemacht hat (leer = Standard). */
  model: string
  state: "open" | "accepted" | "rejected"
}

export interface DiffPart { kind: "same" | "del" | "add"; text: string }

/** Wortweiser Vergleich (LCS) für die Anzeige „gelöscht rot / neu grün“. */
export function wordDiff(a: string, b: string): DiffPart[] {
  const x = a.split(/(\s+)/).filter(Boolean)
  const y = b.split(/(\s+)/).filter(Boolean)
  if (x.length * y.length > 250_000) {
    return [{ kind: "del", text: a }, { kind: "add", text: b }].filter((p) => p.text) as DiffPart[]
  }
  const dp: number[][] = Array.from({ length: x.length + 1 }, () => new Array(y.length + 1).fill(0))
  for (let i = x.length - 1; i >= 0; i--) {
    for (let j = y.length - 1; j >= 0; j--) {
      dp[i][j] = x[i] === y[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1])
    }
  }
  const out: DiffPart[] = []
  const push = (kind: DiffPart["kind"], text: string) => {
    const last = out[out.length - 1]
    if (last && last.kind === kind) last.text += text
    else out.push({ kind, text })
  }
  let i = 0
  let j = 0
  while (i < x.length && j < y.length) {
    if (x[i] === y[j]) { push("same", x[i]); i++; j++ }
    else if (dp[i + 1][j] >= dp[i][j + 1]) push("del", x[i++])
    else push("add", y[j++])
  }
  while (i < x.length) push("del", x[i++])
  while (j < y.length) push("add", y[j++])
  return out
}

/** A5: Wie oft ``selection`` im Text VOR der Markierung schon vorkommt (überlappend, wie der Server mit find(at + 1)) –
 *  so findet der Server das richtige Vorkommen statt immer das letzte. */
export function occurrenceBefore(textBefore: string, selection: string): number {
  if (!selection) return 0
  let n = 0
  for (let at = textBefore.indexOf(selection); at >= 0; at = textBefore.indexOf(selection, at + 1)) n++
  return n
}
