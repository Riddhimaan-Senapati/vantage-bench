export default function Loading() {
  return (
    <div className="flex flex-col h-full animate-pulse">
      <div className="flex items-center gap-3 px-6 py-4 border-b border-border bg-bg-surface flex-shrink-0">
        <div className="w-8 h-8 rounded-lg bg-bg-surface2" />
        <div className="space-y-1.5">
          <div className="h-3 w-20 rounded bg-bg-surface2" />
          <div className="h-2.5 w-36 rounded bg-bg-surface2" />
        </div>
      </div>
      <div className="flex-1" />
    </div>
  );
}
