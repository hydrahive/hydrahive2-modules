import { ExternalLink } from "lucide-react"
import { timeAgo } from "../format"
import type { NewsItem } from "../types"

export function NewsList({ items }: { items: NewsItem[] }) {
  return (
    <div className="space-y-2">
      {items.map((n) => (
        <a
          key={n.id}
          href={n.url}
          target="_blank"
          rel="noopener noreferrer"
          className="group flex gap-3 p-3 rounded-xl border border-white/[6%] bg-white/[2%] hover:bg-white/[4%] hover:border-white/[12%] transition-colors"
        >
          {n.image && (
            <img src={n.image} alt="" loading="lazy" className="hidden sm:block w-24 h-20 rounded-lg object-cover shrink-0" />
          )}
          <div className="min-w-0">
            <div className="text-sm font-medium text-zinc-100 group-hover:text-white line-clamp-2">{n.title}</div>
            <p className="mt-1 text-xs text-zinc-500 line-clamp-2">{n.body}</p>
            <div className="mt-1.5 flex items-center gap-2 text-[10px] text-zinc-600">
              {n.source && <span className="text-zinc-400">{n.source}</span>}
              {n.published_at && <span>· {timeAgo(n.published_at)}</span>}
              <ExternalLink size={10} className="opacity-0 group-hover:opacity-100 transition-opacity" />
            </div>
          </div>
        </a>
      ))}
    </div>
  )
}
