/** Zeichnet eine QR-Modul-Matrix als SVG (schwarz auf weiß, ruhige Zone 4 Module). */
export function QrCode({ matrix, size = 280 }: { matrix: number[][]; size?: number }) {
  const n = matrix.length
  const border = 4
  const total = n + 2 * border
  return (
    <svg viewBox={`0 0 ${total} ${total}`} width={size} height={size} shapeRendering="crispEdges"
      className="rounded-lg" role="img" aria-label="QR-Code zum Koppeln">
      <rect width={total} height={total} fill="#fff" />
      {matrix.flatMap((row, r) =>
        row.map((v, c) => (v ? <rect key={`${r}-${c}`} x={c + border} y={r + border} width={1} height={1} fill="#000" /> : null)),
      )}
    </svg>
  )
}
