import { createContext, useContext, useState, type ReactNode } from "react"

const KEY = "hh2.cryptoboard.vs"
const ALLOWED = ["eur", "usd"]

interface VsState {
  vs: string
  setVs: (v: string) => void
}

const Ctx = createContext<VsState>({ vs: "eur", setVs: () => {} })

export function VsProvider({ children }: { children: ReactNode }) {
  const [vs, setVsState] = useState<string>(() => {
    try {
      const v = localStorage.getItem(KEY)
      return v && ALLOWED.includes(v) ? v : "eur"
    } catch {
      return "eur"
    }
  })
  const setVs = (v: string) => {
    try {
      localStorage.setItem(KEY, v)
    } catch {
      /* ignore */
    }
    setVsState(v)
  }
  return <Ctx.Provider value={{ vs, setVs }}>{children}</Ctx.Provider>
}

export const useVs = (): VsState => useContext(Ctx)
