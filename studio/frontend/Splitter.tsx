/** Ziehbarer Trenner zwischen Panels. Meldet die Verschiebung in % der Bezugsgröße. */
export function Splitter({ dir, onDrag, label }: { dir: "x" | "y"; onDrag: (deltaPercent: number) => void; label: string }) {
  function start(e: React.PointerEvent<HTMLDivElement>) {
    const box = e.currentTarget.parentElement?.getBoundingClientRect()
    const size = (dir === "x" ? box?.width : box?.height) || 1
    let last = dir === "x" ? e.clientX : e.clientY
    const move = (ev: PointerEvent) => {
      const now = dir === "x" ? ev.clientX : ev.clientY
      onDrag(((now - last) / size) * 100)
      last = now
    }
    const stop = () => { window.removeEventListener("pointermove", move); window.removeEventListener("pointerup", stop) }
    window.addEventListener("pointermove", move)
    window.addEventListener("pointerup", stop)
  }
  return (
    <div role="separator" aria-orientation={dir === "x" ? "vertical" : "horizontal"} aria-label={label} data-studio-splitter={dir}
      onPointerDown={start}
      className={`shrink-0 bg-[rgb(var(--hh-s-rand,30_39_56))] transition-colors hover:bg-[#69d7ff] ${dir === "x" ? "w-1 cursor-col-resize" : "h-1 cursor-row-resize"}`} />
  )
}
