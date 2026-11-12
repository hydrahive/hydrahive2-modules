import { useEffect, useState, type RefObject } from "react"

/** Breite eines Elements, laufend gemessen. null vor der ersten Messung und in Browsern ohne ResizeObserver. */
export function useWidth(ref: RefObject<HTMLElement | null>): number | null {
  const [width, setWidth] = useState<number | null>(null)
  useEffect(() => {
    const element = ref.current
    if (!element || typeof ResizeObserver === "undefined") return
    const observer = new ResizeObserver(() => setWidth(Math.round(element.clientWidth)))
    observer.observe(element)
    return () => observer.disconnect()
  }, [ref])
  return width
}
