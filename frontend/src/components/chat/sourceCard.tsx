import { CirclePlay } from 'lucide-react'
import type { Source } from '@/lib/schemas'

export function SourceCard({ source }: { source: Source }) {
    const seconds = source.start_time != null ? Math.floor(source.start_time) : null
    const href = seconds != null ? `${source.url}&t=${seconds}s` : source.url
    const timestamp = source.start_time != null
        ? (
            `${Math.floor(source.start_time / 60)}:${Math.floor(source.start_time % 60).toString().padStart(2, '0')}`
        )
        : null
    return (
        <a href={href} target="_blank" rel="noopener noreferrer"
            className="flex gap-3 border rounded-lg p-3 hover:bg-slate-50 transition-colors">
            <CirclePlay className="size-4 text-red-500 mt-0.5 shrink-0" />
            <div className="min-w-0">
                <p className="text-xs text-muted-foreground line-clamp-2 mt-0.5">{source.snippet}</p>
                <p className="text-xs font-medium truncate">{source.title}</p>               
                {timestamp && <p className="text-xs text-slate-400 mt-1">{timestamp}</p>}
            </div>
        </a>
    )
}