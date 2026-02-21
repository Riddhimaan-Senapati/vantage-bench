export default function Loading() {
  return (
    <div className="p-6 pb-20 md:pb-6 space-y-6 max-w-[1600px] animate-pulse">
      {/* Header */}
      <div className="space-y-2">
        <div className="h-11 w-72 rounded-lg bg-bg-surface" />
        <div className="h-4 w-48 rounded bg-bg-surface" />
      </div>

      {/* Summary bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-20 rounded-xl bg-bg-surface" />
        ))}
      </div>

      {/* Tasks at risk */}
      <div className="space-y-2">
        <div className="h-3 w-28 rounded bg-bg-surface" />
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="h-10 rounded-lg bg-bg-surface" />
        ))}
      </div>

      {/* Team grid */}
      <div className="space-y-3">
        <div className="h-3 w-36 rounded bg-bg-surface" />
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3">
          {Array.from({ length: 12 }).map((_, i) => (
            <div key={i} className="h-28 rounded-xl bg-bg-surface" />
          ))}
        </div>
      </div>
    </div>
  );
}
