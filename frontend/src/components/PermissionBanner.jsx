export default function PermissionBanner({ status }) {
  if (!status || status.demo || status.elevated) return null
  return (
    <div className="flex items-center gap-3 border-b border-amber-600/20 bg-amber-500/[0.05] px-4 py-2 text-[13px] text-amber-200/80">
      <span className="inline-block h-2 w-2 shrink-0 rounded-full" style={{ background: '#e38c2d' }} />
      <span>
        Limited view — seeing only your own connections via{' '}
        <code className="font-mono text-ghost-text">{status.source}</code>. Run with{' '}
        <code className="font-mono text-ghost-text">sudo</code> for system-wide visibility.
      </span>
    </div>
  )
}
