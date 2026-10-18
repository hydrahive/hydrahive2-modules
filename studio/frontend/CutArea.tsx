/** Unterer Bereich in „Schneiden“ und „Ton“: Zeitleiste, im Reiter „Ton“ mit dem Mischpult links daneben (5b). */
export function CutArea({ mixer, children }: { mixer: React.ReactNode; children: React.ReactNode }) {
  if (!mixer) return <>{children}</>
  return (
    <div className="flex h-full min-h-0">
      <div className="w-[420px] min-w-[340px] shrink-0 border-r border-[#2a364b]" data-mixer-area>{mixer}</div>
      <div className="min-w-0 flex-1">{children}</div>
    </div>
  )
}
