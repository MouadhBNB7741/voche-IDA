import { useState, type ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Activity, AlertTriangle, Clock, Database, History, Radio, Server, Users } from 'lucide-react';
import { Card } from '../../components/ui/card';
import { adminService, type AdminOverview, type AuditCategory, type AuditLogEntry } from '../../services/adminService';
import { EmptyState, LoadingCards, Pager, ToneBadge } from './AdminParts';
import { formatDate, formatDuration, USER_TYPE_LABELS, type Tone } from './adminUtils';

const CATEGORIES: { id: AuditCategory | 'all'; label: string }[] = [
  { id: 'all', label: 'All' },
  { id: 'moderation', label: 'Moderation' },
  { id: 'verification', label: 'Licences' },
  { id: 'resource', label: 'Resources' },
  { id: 'event', label: 'Events' },
];

const ACTION_LABELS: Record<string, { label: string; tone: Tone }> = {
  'moderation.approve_content': { label: 'Approved reported content', tone: 'green' },
  'moderation.hide_content': { label: 'Hid content', tone: 'amber' },
  'moderation.delete_content': { label: 'Deleted content', tone: 'red' },
  'moderation.warn_user': { label: 'Warned a member', tone: 'amber' },
  'moderation.suspend_user': { label: 'Suspended a member', tone: 'red' },
  'moderation.ban_user': { label: 'Banned a member', tone: 'red' },
  'verification.approved': { label: 'Approved a licence', tone: 'green' },
  'verification.rejected': { label: 'Rejected a licence', tone: 'red' },
  'resource.approved': { label: 'Published a resource', tone: 'green' },
  'resource.rejected': { label: 'Rejected a resource', tone: 'red' },
  'event.approved': { label: 'Published an event', tone: 'green' },
  'event.rejected': { label: 'Rejected an event', tone: 'red' },
};

export default function SystemPanel({ overview, loading }: { overview?: AdminOverview; loading: boolean }) {
  return (
    <div className="space-y-8">
      {loading || !overview ? <LoadingCards /> : <Overview overview={overview} />}
      <AuditLog />
    </div>
  );
}

function Overview({ overview }: { overview: AdminOverview }) {
  const { health, users, activity } = overview;
  return (
    <div className="space-y-4">
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <Stat
          icon={<Server size={18} />}
          label="Platform"
          value={health.status === 'operational' ? 'Operational' : 'Degraded'}
          tone={health.status === 'operational' ? 'green' : 'red'}
        />
        <Stat icon={<Database size={18} />} label="Database" value={capitalize(health.database)} tone={health.database === 'connected' ? 'green' : 'red'} />
        <Stat
          icon={<Radio size={18} />}
          label="Redis (live updates, logout)"
          value={capitalize(health.redis)}
          tone={health.redis === 'connected' ? 'green' : 'amber'}
        />
        <Stat
          icon={<Activity size={18} />}
          label="Open live connections"
          value={String(health.live_connections)}
          note={health.live_via_redis ? 'Shared with other servers through Redis' : 'This server only'}
        />
        <Stat icon={<Clock size={18} />} label="Running for" value={formatDuration(health.uptime_seconds)} />
        <Stat
          icon={<Users size={18} />}
          label="Members"
          value={String(users.total)}
          note={`${users.new_last_7_days} new in the last 7 days · ${users.suspended} suspended`}
        />
      </div>
      <div className="grid md:grid-cols-2 gap-4">
        <Card className="p-5">
          <p className="text-sm font-semibold mb-3">Members by role</p>
          <ul className="space-y-1.5 text-sm">
            {Object.entries(users.by_type).map(([type, count]) => (
              <li key={type} className="flex justify-between">
                <span className="text-muted-foreground">{USER_TYPE_LABELS[type] ?? type}</span>
                <span className="font-medium">{count}</span>
              </li>
            ))}
          </ul>
        </Card>
        <Card className="p-5">
          <p className="text-sm font-semibold mb-3">Last 7 days</p>
          <ul className="space-y-1.5 text-sm">
            <li className="flex justify-between"><span className="text-muted-foreground">Community posts</span><span className="font-medium">{activity.posts_last_7_days}</span></li>
            <li className="flex justify-between"><span className="text-muted-foreground">Moderation actions</span><span className="font-medium">{activity.moderation_actions_last_7_days}</span></li>
            <li className="flex justify-between"><span className="text-muted-foreground">New members</span><span className="font-medium">{users.new_last_7_days}</span></li>
          </ul>
        </Card>
      </div>
    </div>
  );
}

function Stat({ icon, label, value, tone, note }: { icon: ReactNode; label: string; value: string; tone?: Tone; note?: string }) {
  return (
    <Card className="p-5 space-y-2">
      <p className="text-sm text-muted-foreground flex items-center gap-2">{icon} {label}</p>
      {tone ? <ToneBadge tone={tone}>{value}</ToneBadge> : <p className="text-2xl font-bold">{value}</p>}
      {note && <p className="text-xs text-muted-foreground">{note}</p>}
    </Card>
  );
}

function AuditLog() {
  const [category, setCategory] = useState<AuditCategory | 'all'>('all');
  const [page, setPage] = useState(1);
  const logs = useQuery({
    queryKey: ['admin', 'audit', category, page],
    queryFn: () => adminService.getAuditLogs({ category: category === 'all' ? undefined : category, page, limit: 20 }),
  });

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <h2 className="text-lg font-semibold flex items-center gap-2"><History size={18} /> Audit log</h2>
        <div className="flex flex-wrap gap-1.5 ml-auto" role="tablist" aria-label="Audit log category">
          {CATEGORIES.map(c => (
            <button
              key={c.id}
              role="tab"
              aria-selected={category === c.id}
              onClick={() => { setCategory(c.id); setPage(1); }}
              className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors cursor-pointer ${
                category === c.id ? 'bg-primary-color text-white border-primary-color' : 'border-[hsl(var(--border))] text-muted-foreground hover:text-foreground'
              }`}
            >
              {c.label}
            </button>
          ))}
        </div>
      </div>

      {logs.isLoading ? (
        <LoadingCards />
      ) : logs.isError ? (
        <EmptyState icon={<AlertTriangle size={22} />} title="Could not load the audit log" text="Check your connection and try again." />
      ) : (logs.data?.data.length ?? 0) === 0 ? (
        <EmptyState icon={<History size={22} />} title="No entries yet" text="Admin decisions are recorded here." />
      ) : (
        <Card className="divide-y divide-[hsl(var(--border))]">
          {logs.data!.data.map(entry => <AuditRow key={entry.log_id} entry={entry} />)}
        </Card>
      )}
      <Pager page={page} pages={logs.data?.meta.total_pages ?? 1} onChange={setPage} />
    </div>
  );
}

function AuditRow({ entry }: { entry: AuditLogEntry }) {
  const known = ACTION_LABELS[entry.action];
  const meta = entry.metadata ?? {};
  const details = [
    typeof meta.title === 'string' && `"${meta.title}"`,
    typeof meta.license_number === 'string' && `Licence ${meta.license_number}`,
    typeof meta.duration_hours === 'number' && `${meta.duration_hours} hours`,
    typeof meta.reason === 'string' && meta.reason && `Reason: ${meta.reason}`,
  ].filter(Boolean).join(' · ');

  return (
    <div className="p-4 flex flex-wrap items-start gap-x-4 gap-y-1">
      <span className="text-xs text-muted-foreground w-36 shrink-0 pt-0.5">{formatDate(entry.created_at)}</span>
      <div className="flex-1 min-w-[200px] space-y-1">
        <div className="flex flex-wrap items-center gap-2">
          {known ? <ToneBadge tone={known.tone}>{known.label}</ToneBadge> : <ToneBadge tone="gray">{entry.action}</ToneBadge>}
          <span className="text-sm">by <span className="font-medium">{entry.actor_name || 'System'}</span></span>
        </div>
        {details && <p className="text-sm text-muted-foreground break-words">{details}</p>}
      </div>
    </div>
  );
}

function capitalize(value: string): string {
  return value ? value[0].toUpperCase() + value.slice(1) : value;
}
