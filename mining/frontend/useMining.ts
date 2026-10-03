import { useCallback, useEffect, useState } from "react"
import { miningApi, type Gpu, type MiningConfig, type Overview } from "./api"

const DEFAULT_GPU = "nvidia-rtx-5060-ti-16gb"

export function useMining() {
  const [gpus, setGpus] = useState<Gpu[]>([])
  const [gpu, setGpu] = useState(DEFAULT_GPU)
  const [overview, setOverview] = useState<Overview | null>(null)
  const [config, setConfig] = useState<MiningConfig | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [tick, setTick] = useState(0) // erhöhen = neu laden

  useEffect(() => {
    miningApi.gpus().then(setGpus).catch((e) => setError(String(e)))
  }, [])

  useEffect(() => {
    let alive = true
    Promise.all([miningApi.overview(gpu), miningApi.config()])
      .then(([o, c]) => {
        if (!alive) return
        setOverview(o)
        setConfig(c)
        setError(null)
      })
      .catch((e) => { if (alive) setError(String(e)) })
    return () => { alive = false }
  }, [gpu, tick])

  const reload = useCallback(() => setTick((n) => n + 1), [])

  const refreshNow = useCallback(async () => {
    setBusy(true)
    try { await miningApi.refresh(); reload() } catch (e) { setError(String(e)) } finally { setBusy(false) }
  }, [reload])

  const saveConfig = useCallback(async (c: Partial<MiningConfig>) => {
    try { setConfig(await miningApi.saveConfig(c)); setError(null) } catch (e) { setError(String(e)) }
  }, [])

  return { gpus, gpu, setGpu, overview, config, error, loading: busy, reload, refreshNow, saveConfig }
}
