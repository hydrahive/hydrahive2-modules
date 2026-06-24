import { Bell, CandlestickChart, GitCompareArrows, LayoutGrid, Newspaper, Receipt, TrendingUp, Wallet } from "lucide-react"
import { useEffect, useState, type CSSProperties } from "react"
import { NavLink, Route, Routes } from "react-router-dom"
import { useTranslation } from "react-i18next"
import { rgbFor } from "@/shared/colors"
import { cryptoApi } from "./api"
import { CoinSearch } from "./components/CoinSearch"
import { AlertsView } from "./views/AlertsView"
import { CoinDetailView } from "./views/CoinDetailView"
import { AnalyticsView } from "./views/AnalyticsView"
import { CompareView } from "./views/CompareView"
import { DashboardView } from "./views/DashboardView"
import { NewsView } from "./views/NewsView"
import { PortfolioView } from "./views/PortfolioView"
import { TradeLogView } from "./views/TradeLogView"
import { useVs, VsProvider } from "./vsContext"

const C = rgbFor("/cryptoboard")

function CurrencyToggle() {
  const { vs, setVs } = useVs()
  return (
    <div className="flex rounded-lg border border-white/10 overflow-hidden text-xs">
      {["eur", "usd"].map((c) => (
        <button
          key={c}
          onClick={() => setVs(c)}
          className={`px-2.5 py-1 font-medium uppercase transition-colors ${vs === c ? "bg-white/10 text-zinc-100" : "text-zinc-500 hover:text-zinc-300"}`}
        >
          {c}
        </button>
      ))}
    </div>
  )
}

function Header() {
  const { t } = useTranslation("cryptoboard")
  const tab = "px-3 py-1.5 rounded-lg text-sm font-medium transition-colors"
  const [unseen, setUnseen] = useState(0)

  useEffect(() => {
    let alive = true
    const poll = () => cryptoApi.alertEvents(1).then((r) => { if (alive) setUnseen(r.unseen) }).catch(() => {})
    poll()
    const h = setInterval(poll, 60000)
    return () => { alive = false; clearInterval(h) }
  }, [])
  return (
    <div className="border-b border-white/[6%] px-5 py-4">
      <div className="flex items-center gap-3 flex-wrap">
        <CandlestickChart size={20} style={{ color: `rgb(${C})` }} />
        <div>
          <h1 className="text-lg font-bold text-white leading-tight">{t("title")}</h1>
          <p className="text-xs text-zinc-500">{t("subtitle")}</p>
        </div>
        <div className="ml-auto flex items-center gap-3">
          <CoinSearch />
          <CurrencyToggle />
        </div>
      </div>
      <div className="mt-3 flex items-center gap-1">
        <NavLink end to="/cryptoboard" className={({ isActive }) => `${tab} ${isActive ? "bg-white/10 text-white" : "text-zinc-400 hover:text-zinc-200"}`}>
          <span className="flex items-center gap-1.5"><LayoutGrid size={14} />{t("nav_dashboard")}</span>
        </NavLink>
        <NavLink to="/cryptoboard/portfolio" className={({ isActive }) => `${tab} ${isActive ? "bg-white/10 text-white" : "text-zinc-400 hover:text-zinc-200"}`}>
          <span className="flex items-center gap-1.5"><Wallet size={14} />{t("nav_portfolio")}</span>
        </NavLink>
        <NavLink to="/cryptoboard/analytics" className={({ isActive }) => `${tab} ${isActive ? "bg-white/10 text-white" : "text-zinc-400 hover:text-zinc-200"}`}>
          <span className="flex items-center gap-1.5"><TrendingUp size={14} />{t("nav_analytics")}</span>
        </NavLink>
        <NavLink to="/cryptoboard/trades" className={({ isActive }) => `${tab} ${isActive ? "bg-white/10 text-white" : "text-zinc-400 hover:text-zinc-200"}`}>
          <span className="flex items-center gap-1.5"><Receipt size={14} />{t("nav_tradelog")}</span>
        </NavLink>
        <NavLink to="/cryptoboard/compare" className={({ isActive }) => `${tab} ${isActive ? "bg-white/10 text-white" : "text-zinc-400 hover:text-zinc-200"}`}>
          <span className="flex items-center gap-1.5"><GitCompareArrows size={14} />{t("nav_compare")}</span>
        </NavLink>
        <NavLink to="/cryptoboard/alerts" className={({ isActive }) => `${tab} ${isActive ? "bg-white/10 text-white" : "text-zinc-400 hover:text-zinc-200"}`}>
          <span className="flex items-center gap-1.5 relative">
            <Bell size={14} />{t("nav_alerts")}
            {unseen > 0 && (
              <span className="absolute -top-1.5 -right-2.5 min-w-[16px] h-4 px-1 grid place-items-center rounded-full bg-rose-500 text-white text-[10px] font-bold tabular-nums">{unseen}</span>
            )}
          </span>
        </NavLink>
        <NavLink to="/cryptoboard/news" className={({ isActive }) => `${tab} ${isActive ? "bg-white/10 text-white" : "text-zinc-400 hover:text-zinc-200"}`}>
          <span className="flex items-center gap-1.5"><Newspaper size={14} />{t("nav_news")}</span>
        </NavLink>
      </div>
    </div>
  )
}

export function CryptoboardApp() {
  return (
    <VsProvider>
      <div className="flex flex-col h-full" style={{ "--c": C } as CSSProperties}>
        <Header />
        <div className="flex-1 overflow-y-auto">
          <Routes>
            <Route index element={<DashboardView />} />
            <Route path="portfolio" element={<PortfolioView />} />
            <Route path="analytics" element={<AnalyticsView />} />
            <Route path="trades" element={<TradeLogView />} />
            <Route path="compare" element={<CompareView />} />
            <Route path="alerts" element={<AlertsView />} />
            <Route path="coin/:id" element={<CoinDetailView />} />
            <Route path="news" element={<NewsView />} />
          </Routes>
        </div>
      </div>
    </VsProvider>
  )
}
