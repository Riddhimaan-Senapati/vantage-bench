export default function Loading() {
  return (
    <div className="p-6 pb-20 md:pb-6 h-full flex flex-col animate-pulse">
      {/* Header */}
      <div className="mb-6 space-y-2">
        <div className="h-8 w-48 rounded-lg bg-bg-surface" />
        <div className="h-4 w-64 rounded bg-bg-surface" />
      </div>

      {/* Two-panel layout */}
      <div className="grid grid-cols-1 md:grid-cols-[2fr_3fr] gap-6 flex-1">
        {/* Left: task list */}
        <div className="space-y-2">
          <div className="flex gap-2 mb-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-7 w-12 rounded-full bg-bg-surface" />
            ))}
          </div>
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-16 rounded-xl bg-bg-surface" />
          ))}
        </div>

        {/* Right: suggestion panel */}
        <div className="h-64 rounded-xl bg-bg-surface" />
      </div>
    </div>
  );
}
