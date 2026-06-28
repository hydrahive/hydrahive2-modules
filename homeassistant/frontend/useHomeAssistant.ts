import { useCallback, useEffect, useState } from "react"
import { haApi, type HAState, type HATestResult } from "./api"
import { toggleCall } from "./entityControl"

export function useHomeAssistant() {
  const [test, setTest] = useState<HATestResult | null>(null)
  const [states, setStates] = useState<HAState[]>([])
  const [favorites, setFavorites] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState<Set<string>>(new Set())

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    Promise.all([haApi.test(), haApi.states(), haApi.favorites()])
      .then(([t, s, favs]) => {
        setTest(t)
        setStates(s)
        setFavorites(new Set(favs.map((f) => f.entity_id)))
      })
      .catch((e) => setError(String(e?.message ?? e)))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { load() }, [load])

  const refreshOne = useCallback((entityId: string) => {
    haApi.state(entityId).then((fresh) => {
      setStates((prev) => prev.map((s) => (s.entity_id === entityId ? fresh : s)))
    }).catch(() => { /* still ok — voller reload via load() möglich */ })
  }, [])

  const toggle = useCallback((entity: HAState) => {
    const { domain, service } = toggleCall(entity)
    setBusy((prev) => new Set(prev).add(entity.entity_id))
    haApi.callService(domain, service, entity.entity_id)
      .then(() => refreshOne(entity.entity_id))
      .catch((e) => setError(String(e?.message ?? e)))
      .finally(() =>
        setBusy((prev) => {
          const next = new Set(prev)
          next.delete(entity.entity_id)
          return next
        }),
      )
  }, [refreshOne])

  const toggleFavorite = useCallback((entityId: string) => {
    const isFav = favorites.has(entityId)
    const optimistic = new Set(favorites)
    isFav ? optimistic.delete(entityId) : optimistic.add(entityId)
    setFavorites(optimistic)
    const op = isFav ? haApi.removeFavorite(entityId) : haApi.addFavorite(entityId)
    op.catch(() => setFavorites(favorites)) // rollback bei Fehler
  }, [favorites])

  return { test, states, favorites, loading, error, busy, load, toggle, toggleFavorite }
}
