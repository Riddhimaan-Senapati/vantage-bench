'use client';

import { useTeamMembers, useTasks } from '@/hooks/use-api';
import { useAppStore } from '@/store';
import { cn } from '@/lib/utils';

interface StatBlockProps {
  label: string;
  value: number;
  colorClass?: string;
}

function StatBlock({ label, value, colorClass }: StatBlockProps) {
  return (
    <div className="flex flex-col items-center gap-1 px-6 py-4 bg-bg-surface rounded-xl border border-border flex-1 min-w-[120px]">
      <span
        className={cn(
          'text-[2.5rem] leading-none font-heading font-bold tabular-nums',
          colorClass ?? 'text-foreground'
        )}
      >
        {value}
      </span>
      <span className="text-xs text-muted-foreground text-center leading-tight font-sans">
        {label}
      </span>
    </div>
  );
}

export default function SummaryBar() {
  const { data: members } = useTeamMembers();
  const { data: tasks } = useTasks();
  const { overrides, taskStatusOverrides } = useAppStore();

  // Effective member leave status: Zustand override first, then DB value
  function effectiveMemberStatus(memberId: string, dbLeaveStatus: string) {
    const override = overrides.find((o) => o.memberId === memberId);
    return override?.status ?? dbLeaveStatus;
  }

  // Effective task status: Zustand override first, then DB value
  function effectiveTaskStatus(taskId: string, dbStatus: string) {
    return taskStatusOverrides[taskId] ?? dbStatus;
  }

  const memberList = members ?? [];
  const taskList = tasks ?? [];

  const ooo             = memberList.filter((m) => effectiveMemberStatus(m.id, m.dataSources.leaveStatus) === 'ooo').length;
  const partial         = memberList.filter((m) => effectiveMemberStatus(m.id, m.dataSources.leaveStatus) === 'partial').length;
  const fullyAvailable  = memberList.filter((m) => effectiveMemberStatus(m.id, m.dataSources.leaveStatus) === 'available').length;
  const criticalAtRisk  = taskList.filter((t) => (t.priority === 'P0' || t.priority === 'P1') && effectiveTaskStatus(t.id, t.status) !== 'covered').length;
  const unresolved      = taskList.filter((t) => effectiveTaskStatus(t.id, t.status) !== 'covered').length;

  return (
    <div className="flex gap-3 flex-wrap">
      <StatBlock label="People Out" value={ooo} />
      <StatBlock label="Partially Available" value={partial} colorClass="text-status-yellow" />
      <StatBlock label="Fully Available" value={fullyAvailable} colorClass="text-status-green" />
      <StatBlock
        label="Critical Tasks at Risk"
        value={criticalAtRisk}
        colorClass={criticalAtRisk > 0 ? 'text-status-red' : undefined}
      />
      <StatBlock
        label="Unresolved Reassignments"
        value={unresolved}
        colorClass={unresolved > 0 ? 'text-status-amber' : undefined}
      />
    </div>
  );
}
