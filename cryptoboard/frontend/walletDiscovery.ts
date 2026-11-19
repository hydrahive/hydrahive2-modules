// EIP-6963-Discovery: sammelt injizierte Wallets (MetaMask, Rabby, Coinbase …). Reine Logik, ohne React.
import type { Eip1193Provider, Eip6963ProviderDetail } from "./types"

export interface WalletWindow {
  addEventListener: (type: string, listener: (e: Event) => void) => void
  removeEventListener: (type: string, listener: (e: Event) => void) => void
  dispatchEvent: (e: Event) => boolean
  ethereum?: Eip1193Provider
}

export const LEGACY_UUID = "window.ethereum"

function asDetail(e: Event): Eip6963ProviderDetail | null {
  const d = (e as CustomEvent<Eip6963ProviderDetail>).detail
  if (!d || typeof d !== "object" || !d.info || typeof d.info.uuid !== "string" || !d.provider) return null
  return d
}

/** Fragt Wallets an, sammelt Ankündigungen (Duplikate per info.uuid raus), fällt auf window.ethereum zurück. */
export async function discoverWallets(win: WalletWindow, waitMs = 200): Promise<Eip6963ProviderDetail[]> {
  const found = new Map<string, Eip6963ProviderDetail>()
  const onAnnounce = (e: Event) => {
    const d = asDetail(e)
    if (d && !found.has(d.info.uuid)) found.set(d.info.uuid, d)
  }
  win.addEventListener("eip6963:announceProvider", onAnnounce)
  try {
    win.dispatchEvent(new Event("eip6963:requestProvider"))
    await new Promise<void>((resolve) => setTimeout(resolve, waitMs))
  } finally {
    win.removeEventListener("eip6963:announceProvider", onAnnounce)
  }
  if (found.size === 0 && win.ethereum && typeof win.ethereum.request === "function") {
    return [{ info: { uuid: LEGACY_UUID, name: "Browser-Wallet", icon: "" }, provider: win.ethereum }]
  }
  return [...found.values()]
}
