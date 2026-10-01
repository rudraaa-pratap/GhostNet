export default function PermissionBanner({ status }) {
  if (!status || status.demo || status.elevated) return null
  return (
    <div className="flex items-center gap-3 border-b border-amber-500/25 bg-amber-500/[0.07] px-4 py-2 text-[12px] text-amber-200/90">
      <span className="inline-block h-2 w-2 shrink-0 rounded-full bg-amber-400" />
      <span>
        Limited view — seeing only your own connections via{' '}
        <code className="font-mono">{status.source}</code>. Run the backend with{' '}
        <code className="font-mono">sudo</code> for the full system-wide picture.
      </span>
    </div>
  )
}
