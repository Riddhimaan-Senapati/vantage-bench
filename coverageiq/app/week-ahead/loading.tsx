export default function Loading() {
  return (
    <div className="p-6 pb-20 md:pb-6 space-y-6 max-w-[900px] animate-pulse">
      {/* Header */}
      <div className="space-y-2">
        <div className="h-8 w-40 rounded-lg bg-bg-surface" />
        <div className="h-4 w-56 rounded bg-bg-surface" />
      </div>

      {/* Chart */}
      <div className="h-40 rounded-xl bg-bg-surface" />

      {/* Member rows */}
      <div className="space-y-2">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="h-14 rounded-xl bg-bg-surface" />
        ))}
      </div>
    </div>
  );
}
