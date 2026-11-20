// Wallet-Connect-Logik (reine Funktionen). NUR LESEN: der Provider darf ausschließlich
// eth_requestAccounts erhalten — alles andere wirft, BEVOR der Provider berührt wird.
import type {
  ChainChangeOutcome, Eip1193Provider, EvmChain, WalletConnectResult, WalletRequestMethod,
} from "./types"

export const ALLOWED_METHODS: readonly WalletRequestMethod[] = ["eth_requestAccounts"]

export class WalletMethodNotAllowed extends Error {
  constructor(method: string) {
    super(`Wallet-Methode nicht erlaubt: ${method}`)
    this.name = "WalletMethodNotAllowed"
  }
}

/** Einziger Weg zum Provider: Whitelist-Prüfung vor jedem request(). */
export function guardedRequest(provider: Eip1193Provider, method: string): Promise<unknown> {
  if (!(ALLOWED_METHODS as readonly string[]).includes(method)) throw new WalletMethodNotAllowed(method)
  return provider.request({ method })
}

const CHAIN_BY_ID: Record<string, EvmChain> = { "0x1": "ethereum", "0x2105": "base" }

/** 0x1 / 0X1 / 0x01 / "1" / 1 / "8453" → "0x1" bzw. "0x2105"; sonst null. */
export function normalizeChainId(raw: unknown): string | null {
  let n: bigint
  try {
    if (typeof raw === "number" && Number.isSafeInteger(raw) && raw >= 0) n = BigInt(raw)
    else if (typeof raw === "string" && /^0x[0-9a-f]+$/i.test(raw.trim())) n = BigInt(raw.trim().toLowerCase())
    else if (typeof raw === "string" && /^\d+$/.test(raw.trim())) n = BigInt(raw.trim())
    else return null
  } catch { return null }
  return "0x" + n.toString(16)
}

export function chainFromId(raw: unknown): EvmChain | null {
  const id = normalizeChainId(raw)
  return id ? CHAIN_BY_ID[id] ?? null : null
}

/** chainChanged → nur ein Angebot (nie automatisch hinzufügen); gleiche Chain wie im Formular: nichts. */
export function evaluateChainChange(raw: unknown, currentChain: string): ChainChangeOutcome {
  const chain = chainFromId(raw)
  if (!chain) return { kind: "unsupported" }
  return chain === currentChain ? { kind: "same" } : { kind: "offer", chain }
}

/** Hängt einen chainChanged-Handler an; die Rückgabe entfernt ihn wieder (Unmount). */
export function subscribeChainChanged(provider: Eip1193Provider, handler: (chainId: unknown) => void): () => void {
  const listener = (...args: unknown[]) => handler(args[0])
  provider.on?.("chainChanged", listener)
  return () => { provider.removeListener?.("chainChanged", listener) }
}

export function classifyWalletError(e: unknown): "rejected" | "pending" | "error" {
  const code = (e as { code?: unknown } | null)?.code
  if (code === 4001) return "rejected"
  if (code === -32002) return "pending"
  return "error"
}

/** eth_requestAccounts → erste Adresse. Wirft nie; Fehler werden zu einem Ergebnis-Grund. */
export async function connectWallet(provider: Eip1193Provider): Promise<WalletConnectResult> {
  try {
    const accounts = await guardedRequest(provider, "eth_requestAccounts")
    const first = Array.isArray(accounts) ? accounts[0] : undefined
    if (typeof first !== "string" || !first.trim()) return { ok: false, reason: "no_account" }
    return { ok: true, address: first.trim() }
  } catch (e) {
    return { ok: false, reason: classifyWalletError(e) }
  }
}

export type AddWalletFn = (chain: string, address: string, label: string) => Promise<unknown>

/** Gemeinsamer Speicherpfad für manuelle Eingabe UND Wallet-Adresse: derselbe addWallet-Aufruf. */
export function saveWallet(addWallet: AddWalletFn, chain: string, address: string, label: string): Promise<unknown> {
  return addWallet(chain, address.trim(), label.trim())
}

export interface ChainOfferUi {
  onOffer: (chain: EvmChain) => void
  onUnsupported: () => void
  onCleared: () => void
}

export interface ChainOfferFlow {
  watch: (provider: Eip1193Provider) => () => void
  /** Nur nach ausdrücklicher Bestätigung: derselbe Speicherpfad wie die manuelle Eingabe. */
  confirm: () => Promise<void>
  dismiss: () => void
}

/**
 * chainChanged → höchstens ein ANGEBOT. addWallet wird ausschließlich in confirm() gerufen,
 * also erst nach dem Klick des Nutzers — niemals automatisch.
 */
export function createChainOfferFlow(
  addWallet: AddWalletFn,
  ctx: { getChain: () => string; getAddress: () => string; getLabel: () => string },
  ui: ChainOfferUi,
): ChainOfferFlow {
  let offered: EvmChain | null = null
  return {
    watch: (provider) => subscribeChainChanged(provider, (raw) => {
      const out = evaluateChainChange(raw, ctx.getChain())
      if (out.kind === "offer") { offered = out.chain; ui.onOffer(out.chain) }
      else if (out.kind === "unsupported") { offered = null; ui.onUnsupported() }
    }),
    confirm: async () => {
      const chain = offered
      if (!chain) return
      offered = null
      ui.onCleared()
      await saveWallet(addWallet, chain, ctx.getAddress(), ctx.getLabel())
    },
    dismiss: () => { offered = null; ui.onCleared() },
  }
}
