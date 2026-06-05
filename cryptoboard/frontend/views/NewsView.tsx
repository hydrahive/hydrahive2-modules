import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { cryptoApi } from "../api"
import { NewsList } from "../components/NewsList"
import type { NewsItem } from "../types"

export function NewsView() {
  const { t } = useTranslation("cryptoboard")
  const [items, setItems] = useState<NewsItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    cryptoApi.news().then(setItems).catch(() => setItems([])).finally(() => setLoading(false))
  }, [])

  return (
    <div className="p-5 max-w-4xl mx-auto">
      <h2 className="text-lg font-bold text-white mb-3">{t("news_title")}</h2>
      {loading ? (
        <p className="text-sm text-zinc-500">{t("loading")}</p>
      ) : items.length === 0 ? (
        <p className="text-sm text-zinc-500">{t("news_empty")}</p>
      ) : (
        <NewsList items={items} />
      )}
    </div>
  )
}
