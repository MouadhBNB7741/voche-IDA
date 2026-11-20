import type { ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Navigate, useSearchParams } from 'react-router-dom';
import { BadgeCheck, BookOpen, Loader2, ServerCog, ShieldAlert } from 'lucide-react';
import { PageHeader } from '../../components/ui/PageHeader';
import { useAuthContext } from '../../contexts/AuthContext';
import { adminService } from '../../services/adminService';
import ApprovalsQueue from './ApprovalsQueue';
import LicenceQueue from './LicenceQueue';
import ModerationQueue from './ModerationQueue';
import SystemPanel from './SystemPanel';

type TabId = 'moderation' | 'licences' | 'approvals' | 'system';

const TABS: { id: TabId; label: string; icon: ReactNode }[] = [
  { id: 'moderation', label: 'Moderation queue', icon: <ShieldAlert size={16} /> },
  { id: 'licences', label: 'Doctor licences', icon: <BadgeCheck size={16} /> },
  { id: 'approvals', label: 'Resources & events', icon: <BookOpen size={16} /> },
  { id: 'system', label: 'System & audit log', icon: <ServerCog size={16} /> },
];

/** The admin portal at /admin: moderation, licence checks, approvals, and system health with the audit log. */
export default function AdminDashboard() {
  const { user, isAuthenticated, isLoading } = useAuthContext();
  const [params, setParams] = useSearchParams();
  const isAdmin = user?.user_type === 'admin';

  const overview = useQuery({
    queryKey: ['admin', 'overview'],
    queryFn: adminService.getOverview,
    enabled: isAdmin,
    refetchInterval: 60_000,
  });

  if (isLoading) {
    return (
      <div className="min-h-[50vh] flex items-center justify-center" aria-busy="true">
        <Loader2 className="animate-spin text-primary-color" size={32} />
      </div>
    );
  }
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  if (!isAdmin) return <Navigate to="/403" replace />;

  const requested = params.get('tab') as TabId | null;
  const tab: TabId = TABS.some(t => t.id === requested) ? requested! : 'moderation';
  const queues = overview.data?.queues;
  const counts: Partial<Record<TabId, number>> = queues ? {
    moderation: queues.open_reports,
    licences: queues.pending_licences,
    approvals: queues.pending_resources + queues.pending_events,
  } : {};
  const waiting = (counts.moderation ?? 0) + (counts.licences ?? 0) + (counts.approvals ?? 0);

  return (
    <div className="container mx-auto p-4 md:p-8 max-w-6xl animate-in fade-in duration-500">
      <PageHeader
        title="Admin portal"
        description="Review reported content, doctor licences, and what members submit, and keep an eye on the platform."
        badgeText={queues ? (waiting ? `${waiting} waiting for review` : 'All caught up') : 'Administrator'}
      />

      <div className="flex flex-wrap gap-2" role="tablist" aria-label="Admin sections">
        {TABS.map(t => {
          const active = tab === t.id;
          const count = counts[t.id];
          const urgent = t.id === 'moderation' && !!queues?.critical_reports;
          return (
            <button
              key={t.id}
              role="tab"
              aria-selected={active}
              onClick={() => setParams(t.id === 'moderation' ? {} : { tab: t.id }, { replace: true })}
              className={`flex items-center gap-2 whitespace-nowrap rounded-full px-4 py-2 text-sm font-medium border transition-colors cursor-pointer ${
                active
                  ? 'bg-primary-color text-white border-primary-color shadow-sm'
                  : 'border-[hsl(var(--border))] text-muted-foreground hover:text-foreground hover:bg-muted/40'
              }`}
            >
              {t.icon}
              {t.label}
              {!!count && (
                <span
                  className={`min-w-[22px] h-[22px] px-1.5 rounded-full text-xs font-bold flex items-center justify-center ${
                    urgent ? 'bg-red-600 text-white' : active ? 'bg-white/25 text-white' : 'bg-primary-color/15 text-primary-color'
                  }`}
                  title={urgent ? `${queues!.critical_reports} urgent` : undefined}
                >
                  {count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      <div className="mt-6" role="tabpanel">
        {tab === 'moderation' && <ModerationQueue />}
        {tab === 'licences' && <LicenceQueue />}
        {tab === 'approvals' && <ApprovalsQueue resourceCount={queues?.pending_resources} eventCount={queues?.pending_events} />}
        {tab === 'system' && <SystemPanel overview={overview.data} loading={overview.isLoading} />}
      </div>
    </div>
  );
}
