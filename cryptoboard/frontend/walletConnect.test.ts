// Etappe 2 / Phase 1: MetaMask-Connect — gemockter Provider, kein echter Extension-Zugriff, kein jsdom nötig.
import { readFileSync, readdirSync } from "node:fs"
import { join } from "node:path"
import { describe, expect, it, vi } from "vitest"
import type { Eip1193Provider, Eip6963ProviderDetail } from "./types"
import { discoverWallets, LEGACY_UUID, type WalletWindow } from "./walletDiscovery"
import {
  ALLOWED_METHODS, chainFromId, connectWallet, createChainOfferFlow, evaluateChainChange, guardedRequest,
  normalizeChainId, saveWallet, WalletMethodNotAllowed,
} from "./walletConnect"

const ADDR = "0x52908400098527886E0F7030069857D2E4169EE7"

/** Flow wie im Button verdrahtet; ui-Callbacks als Spies. */
function flowWith(add: (c: string, a: string, l: string) => Promise<unknown>, chain = "base", label = "") {
  const ui = { onOffer: vi.fn(), onUnsupported: vi.fn(), onCleared: vi.fn() }
  const flow = createChainOfferFlow(add, { getChain: () => chain, getAddress: () => ADDR, getLabel: () => label }, ui)
  return { flow, ui }
}

function mockProvider(impl?: (m: string) => unknown) {
  const handlers = new Map<string, Set<(...a: unknown[]) => void>>()
  const request = vi.fn(async ({ method }: { method: string }) => (impl ? impl(method) : [ADDR]))
  const provider: Eip1193Provider = {
    request,
    on: (e, h) => { (handlers.get(e) ?? handlers.set(e, new Set()).get(e)!).add(h) },
    removeListener: (e, h) => { handlers.get(e)?.delete(h) },
  }
  const emit = (e: string, ...a: unknown[]) => handlers.get(e)?.forEach((h) => h(...a))
  return { provider, request, emit, count: (e: string) => handlers.get(e)?.size ?? 0 }
}

function detail(uuid: string, name: string, provider = mockProvider().provider): Eip6963ProviderDetail {
  return { info: { uuid, name, icon: "data:image/svg+xml;base64,AA==" }, provider }
}

/** Fake-Fenster auf Basis von EventTarget; „Wallets“ antworten auf eip6963:requestProvider. */
function fakeWindow(announces: Eip6963ProviderDetail[], ethereum?: Eip1193Provider) {
  const target = new EventTarget()
  const win = Object.assign(target, { ethereum }) as unknown as WalletWindow
  target.addEventListener("eip6963:requestProvider", () => {
    for (const d of announces) target.dispatchEvent(new CustomEvent("eip6963:announceProvider", { detail: d }))
  })
  return win
}

describe("EIP-6963-Discovery", () => {
  it("sammelt mehrere Provider und entfernt Duplikate per info.uuid", async () => {
    const win = fakeWindow([detail("a", "MetaMask"), detail("b", "Rabby"), detail("a", "MetaMask (doppelt)")])
    const res = await discoverWallets(win, 0)
    expect(res.map((r) => r.info.uuid)).toEqual(["a", "b"])
    expect(res[0].info.name).toBe("MetaMask")
  })
  it("Fallback auf window.ethereum, wenn nichts angekündigt wird", async () => {
    const eth = mockProvider().provider
    const res = await discoverWallets(fakeWindow([], eth), 0)
    expect(res).toHaveLength(1)
    expect(res[0].info.uuid).toBe(LEGACY_UUID)
    expect(res[0].provider).toBe(eth)
  })
  it("kein Provider → leere Liste (UI zeigt Hinweis statt Fehler)", async () => {
    expect(await discoverWallets(fakeWindow([]), 0)).toEqual([])
  })
  it("ignoriert kaputte Ankündigungen", async () => {
    const win = fakeWindow([{ info: {}, provider: null } as unknown as Eip6963ProviderDetail])
    expect(await discoverWallets(win, 0)).toEqual([])
  })
})

describe("Whitelist (nur eth_requestAccounts)", () => {
  it("erlaubt genau eine Methode", () => {
    expect([...ALLOWED_METHODS]).toEqual(["eth_requestAccounts"])
  })
  it.each(["personal_sign", "eth_sign", "eth_signTypedData_v4", "eth_sendTransaction", "eth_chainId", "wallet_switchEthereumChain"])(
    "Wrapper wirft bei %s, bevor der Provider berührt wird", (m) => {
      const { provider, request } = mockProvider()
      expect(() => guardedRequest(provider, m)).toThrow(WalletMethodNotAllowed)
      expect(request).not.toHaveBeenCalled()
    })
  it("kompletter Ablauf (Connect + chainChanged + Bestätigung): Provider sieht NIE etwas anderes als eth_requestAccounts", async () => {
    const { provider, request, emit } = mockProvider()
    const add = vi.fn(async () => ({ ok: true }))
    await connectWallet(provider)
    const { flow } = flowWith(add)
    const stop = flow.watch(provider)
    emit("chainChanged", "0x1"); emit("chainChanged", "0x89"); emit("chainChanged", "0x1")
    await flow.confirm()
    stop()
    for (const call of request.mock.calls) expect(call[0]).toEqual({ method: "eth_requestAccounts" })
    expect(request).toHaveBeenCalledTimes(1)
  })
  it("Quellcode: keine verbotenen Methoden und kein direkter provider.request außerhalb des Wrappers", () => {
    const files = ["walletConnect.ts", "walletDiscovery.ts", join("components", "WalletConnectButton.tsx"), join("components", "AddressForm.tsx")]
    for (const f of files) {
      const src = readFileSync(join(__dirname, f), "utf8")
      expect(src, f).not.toMatch(/personal_sign|eth_sign|signTypedData|eth_sendTransaction|eth_chainId|wallet_switchEthereumChain|wallet_addEthereumChain/)
      if (f !== "walletConnect.ts") expect(src, f).not.toMatch(/\.request\s*\(/)
    }
  })
})

describe("connectWallet", () => {
  it("liefert nur die erste Adresse", async () => {
    const { provider } = mockProvider(() => [ADDR, "0x0000000000000000000000000000000000000001"])
    expect(await connectWallet(provider)).toEqual({ ok: true, address: ADDR })
  })
  it("Ablehnung (4001) → ruhige Meldung statt Absturz", async () => {
    const { provider } = mockProvider(() => { throw Object.assign(new Error("User rejected"), { code: 4001 }) })
    expect(await connectWallet(provider)).toEqual({ ok: false, reason: "rejected" })
  })
  it("laufende Anfrage (-32002) → pending", async () => {
    const { provider } = mockProvider(() => { throw Object.assign(new Error("pending"), { code: -32002 }) })
    expect(await connectWallet(provider)).toEqual({ ok: false, reason: "pending" })
  })
  it("sonstige Fehler → allgemein, leere Liste → no_account", async () => {
    expect(await connectWallet(mockProvider(() => { throw new Error("boom") }).provider)).toEqual({ ok: false, reason: "error" })
    expect(await connectWallet(mockProvider(() => []).provider)).toEqual({ ok: false, reason: "no_account" })
    expect(await connectWallet(mockProvider(() => null).provider)).toEqual({ ok: false, reason: "no_account" })
  })
})

describe("gemeinsamer addWallet-Pfad", () => {
  it("Wallet-Adresse und manuelle Eingabe rufen addWallet mit derselben Argumentform", async () => {
    const add = vi.fn(async () => ({ ok: true, id: 1 }))
    const res = await connectWallet(mockProvider().provider)
    if (!res.ok) throw new Error("Connect fehlgeschlagen")
    await saveWallet(add, "base", res.address, " Meine Wallet ")   // Wallet-Weg
    await saveWallet(add, "base", `  ${ADDR} `, "Meine Wallet")    // manueller Weg (Feld mit Leerraum)
    expect(add.mock.calls[0]).toEqual(add.mock.calls[1])
    expect(add).toHaveBeenNthCalledWith(1, "base", ADDR, "Meine Wallet")
  })
  it("AddressForm: genau EIN Speicherpfad (saveWallet) und der Button bekommt dieselbe addWallet-Funktion", () => {
    const src = readFileSync(join(__dirname, "components", "AddressForm.tsx"), "utf8")
    expect(src.match(/saveWallet\(cryptoApi\.addWallet, chain, address, label\)/g)).toHaveLength(1)
    expect(src.match(/addWallet=\{cryptoApi\.addWallet\}/g)).toHaveLength(1)
    expect(src).not.toMatch(/cryptoApi\.addWallet\(/)
    expect(src.match(/cryptoApi\.addWallet/g)).toHaveLength(2)
  })
  it("Button nur bei EVM-Chains eingebunden", () => {
    const src = readFileSync(join(__dirname, "components", "AddressForm.tsx"), "utf8")
    expect(src).toMatch(/isEvm = chain === "base" \|\| chain === "ethereum"/)
    expect(src).toMatch(/\{isEvm && \(\s*<WalletConnectButton/)
  })
})

describe("chainChanged", () => {
  it("Chain-ID-Mapping tolerant (Groß-/Kleinschreibung, Dezimal, führende Nullen)", () => {
    for (const v of ["0x1", "0X1", "0x01", "1", 1]) expect(chainFromId(v)).toBe("ethereum")
    for (const v of ["0x2105", "0X2105", "0x02105", "8453", 8453]) expect(chainFromId(v)).toBe("base")
    for (const v of ["0x89", "137", "", "abc", null, undefined, {}, -1, 1.5]) expect(chainFromId(v)).toBeNull()
    expect(normalizeChainId("0xAbC")).toBe("0xabc")
  })
  it("Angebot statt Auto-Übernahme: addWallet erst nach Bestätigung", async () => {
    const { provider, emit } = mockProvider()
    const add = vi.fn(async () => ({ ok: true }))
    const { flow, ui } = flowWith(add, "base", "x")
    flow.watch(provider)
    emit("chainChanged", "0x1")
    expect(ui.onOffer).toHaveBeenCalledWith("ethereum")
    expect(add).not.toHaveBeenCalled()
    await flow.confirm()
    expect(add).toHaveBeenCalledOnce()
    expect(add).toHaveBeenCalledWith("ethereum", ADDR, "x")
  })
  it("ohne Angebot oder nach Ablehnen speichert confirm() nichts; ein Angebot gilt nur einmal", async () => {
    const { provider, emit } = mockProvider()
    const add = vi.fn(async () => ({ ok: true }))
    const { flow } = flowWith(add)
    flow.watch(provider)
    await flow.confirm()
    emit("chainChanged", "0x1"); flow.dismiss()
    await flow.confirm()
    emit("chainChanged", "0x1")
    await flow.confirm(); await flow.confirm()
    expect(add).toHaveBeenCalledOnce()
  })
  it("unbekannte Chain nach einem Angebot nimmt das Angebot zurück", async () => {
    const { provider, emit } = mockProvider()
    const add = vi.fn(async () => ({ ok: true }))
    const { flow } = flowWith(add)
    flow.watch(provider)
    emit("chainChanged", "0x1"); emit("chainChanged", "0x89")
    await flow.confirm()
    expect(add).not.toHaveBeenCalled()
  })
  it("gleiche Chain wie im Formular → kein Angebot", () => {
    expect(evaluateChainChange("0x2105", "base")).toEqual({ kind: "same" })
    expect(evaluateChainChange("0x2105", "ethereum")).toEqual({ kind: "offer", chain: "base" })
  })
  it("unbekannte Chain → Hinweis, kein Angebot", () => {
    const { provider, emit } = mockProvider()
    const { flow, ui } = flowWith(vi.fn(async () => ({})))
    flow.watch(provider)
    emit("chainChanged", "0x89")
    expect(ui.onUnsupported).toHaveBeenCalledOnce()
    expect(ui.onOffer).not.toHaveBeenCalled()
  })
  it("Listener wird beim Abmelden (Unmount) entfernt", () => {
    const { provider, emit, count } = mockProvider()
    const { flow, ui } = flowWith(vi.fn(async () => ({})))
    const stop = flow.watch(provider)
    expect(count("chainChanged")).toBe(1)
    stop()
    expect(count("chainChanged")).toBe(0)
    emit("chainChanged", "0x1")
    expect(ui.onOffer).not.toHaveBeenCalled()
  })
  it("Provider ohne on/removeListener stürzt nicht ab", () => {
    const { flow } = flowWith(vi.fn(async () => ({})))
    const stop = flow.watch({ request: async () => [] })
    expect(() => stop()).not.toThrow()
  })
  it("Button-Quelltext: addWallet nur über den Flow, nie direkt", () => {
    const src = readFileSync(join(__dirname, "components", "WalletConnectButton.tsx"), "utf8")
    expect(src.match(/addWallet/g)!.length).toBeGreaterThan(0)
    expect(src).not.toMatch(/saveWallet|cryptoApi/)
    expect(src).toMatch(/flowRef\.current\?\.confirm\(\)/)
  })
})

describe("i18n", () => {
  it("alle wl_connect*/wl_chain_*-Keys in de und en vorhanden", () => {
    const src = readFileSync(join(__dirname, "index.tsx"), "utf8")
    const keys = ["wl_connect", "wl_connect_busy", "wl_connect_readonly", "wl_connect_pick", "wl_connect_none", "wl_connect_rejected",
      "wl_connect_pending", "wl_connect_error", "wl_connect_no_account", "wl_chain_unsupported", "wl_chain_offer", "wl_chain_offer_yes", "wl_chain_offer_no"]
    for (const k of keys) expect(src.match(new RegExp(`^\\s+${k}:`, "gm")), k).toHaveLength(2)
    expect(readdirSync(__dirname)).toContain("walletConnect.ts")
  })
})
