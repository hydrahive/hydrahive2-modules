// Kleine animierte Equalizer-Balken — reines CSS, animieren nur wenn `active`.
const BARS = [0, 1, 2, 3, 4]
const DELAYS = ["0ms", "180ms", "90ms", "300ms", "140ms"]

export function Equalizer({ active, color }: { active: boolean; color: string }) {
  return (
    <div className="flex items-end gap-[2px] h-4" aria-hidden>
      {BARS.map((i) => (
        <span
          key={i}
          className="w-[3px] rounded-full"
          style={{
            background: color,
            height: active ? undefined : "20%",
            animation: active ? `mp-eq 600ms ease-in-out ${DELAYS[i]} infinite alternate` : "none",
          }}
        />
      ))}
      <style>{`@keyframes mp-eq { from { height: 20%; } to { height: 100%; } }`}</style>
    </div>
  )
}
