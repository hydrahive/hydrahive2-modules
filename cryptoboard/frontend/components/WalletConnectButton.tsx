import { useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import type { Eip1193Provider, Eip6963ProviderDetail, EvmChain } from "../types"
import { discoverWallets, type WalletWindow } from "../walletDiscovery"
import { connectWallet, createChainOfferFlow, type AddWalletFn, type ChainOfferFlow } from "../walletConnect"

interface Props {
  chain: string
  /** Die verbundene Adresse landet im normalen Adressfeld — gespeichert wird über denselben Pfad wie von Hand. */
  onAddress: (address: string) => void
  /** Speicherpfad (der addWallet-Aufruf des Formulars) — wird nur nach ausdrücklicher Bestätigung eines Chain-Angebots gerufen. */
  addWallet: AddWalletFn
  /** Wird nach dem Speichern für ein bestätigtes Chain-Angebot gerufen (Fehler: wl_err_invalid in der Form). */
  onOfferSaved: () => void
  onOfferError: () => void
  label: string
  disabled?: boolean
}

const btnCls = "px-3 py-1.5 rounded-lg bg-[rgb(var(--hh-s-innen,17_24_39))] text-[#c8d2df] text-xs hover:text-[#e8eef8] disabled:opacity-50"

export function WalletConnectButton({ chain, onAddress, addWallet, onOfferSaved, onOfferError, label, disabled }: Props) {
  const { t } = useTranslation("cryptoboard")
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState("")
  const [choices, setChoices] = useState<Eip6963ProviderDetail[]>([])
  const [active, setActive] = useState<Eip1193Provider | null>(null)
  const [address, setAddress] = useState("")
  const [offer, setOffer] = useState<EvmChain | null>(null)
  // Aktuelle Werte per Ref, damit der Flow (und ein offenes Angebot) über Renders hinweg stabil bleibt.
  const live = useRef({ chain, address, label, addWallet, unsupported: t("wl_chain_unsupported") })
  live.current = { chain, address, label, addWallet, unsupported: t("wl_chain_unsupported") }
  const flowRef = useRef<ChainOfferFlow | null>(null)
  if (!flowRef.current) {
    flowRef.current = createChainOfferFlow((...a) => live.current.addWallet(...a), {
      getChain: () => live.current.chain, getAddress: () => live.current.address, getLabel: () => live.current.label,
    }, {
      onOffer: (c) => { setOffer(c); setMsg("") },
      onUnsupported: () => { setOffer(null); setMsg(live.current.unsupported) },
      onCleared: () => setOffer(null),
    })
  }

  // chainChanged nur beobachten, solange eine Wallet verbunden ist; beim Unmount sauber entfernen.
  useEffect(() => {
    if (!active) return
    return flowRef.current?.watch(active)
  }, [active])

  async function connect(p: Eip1193Provider) {
    setBusy(true); setChoices([]); setMsg("")
    const res = await connectWallet(p)
    setBusy(false)
    if (res.ok) { setActive(p); setAddress(res.address); onAddress(res.address); return }
    setMsg(t(`wl_connect_${res.reason}`))
  }

  async function start() {
    setBusy(true); setMsg(""); setOffer(null)
    const found = await discoverWallets(window as unknown as WalletWindow)
    setBusy(false)
    if (found.length === 0) { setMsg(t("wl_connect_none")); return }
    if (found.length === 1) { await connect(found[0].provider); return }
    setChoices(found)
  }

  async function confirm() {
    try {
      await flowRef.current?.confirm()
      onOfferSaved()
    } catch {
      onOfferError()
    }
  }

  return (
    <div className="space-y-1.5">
      <button type="button" disabled={busy || disabled} onClick={start} className={btnCls}>
        {busy ? t("wl_connect_busy") : t("wl_connect")}
      </button>
      <p className="text-[11px] text-[#9aa7bc]">{t("wl_connect_readonly")}</p>
      {choices.length > 1 && (
        <div className="space-y-1">
          <p className="text-xs text-[#9aa7bc]">{t("wl_connect_pick")}</p>
          {choices.map((c) => (
            <button key={c.info.uuid} type="button" onClick={() => connect(c.provider)} className={`${btnCls} flex items-center gap-2 w-full`}>
              {c.info.icon && <img src={c.info.icon} alt="" className="w-4 h-4" />}
              {c.info.name}
            </button>
          ))}
        </div>
      )}
      {msg && <p className="text-xs text-amber-300">{msg}</p>}
      {offer && (
        <div className="flex items-center gap-2 text-xs text-[#c8d2df]">
          <span>{t("wl_chain_offer", { chain: t(`wl_chain_${offer}`) })}</span>
          <button type="button" onClick={confirm} className={btnCls}>{t("wl_chain_offer_yes")}</button>
          <button type="button" onClick={() => flowRef.current?.dismiss()} className={btnCls}>{t("wl_chain_offer_no")}</button>
        </div>
      )}
    </div>
  )
}
