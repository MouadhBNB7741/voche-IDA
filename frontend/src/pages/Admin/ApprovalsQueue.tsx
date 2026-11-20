import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';
import {
  AlertTriangle, BookOpen, Calendar, CheckCircle2, Clock, ExternalLink, FileText, Globe, Link2, MapPin, User, XCircle,
} from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Card } from '../../components/ui/card';
import { useErrorHandler } from '../../hooks/useErrorHandler';
import { adminService, type PendingEvent, type PendingResource } from '../../services/adminService';
import { resourceService } from '../../services/resourceService';
import { DecisionDialog, EmptyState, LoadingCards, ToneBadge, type DecisionConfig } from './AdminParts';
import { formatBytes, formatDate, openProtectedFile, timeAgo, USER_TYPE_LABELS } from './adminUtils';

type Kind = 'resource' | 'event';
type Decision = 'approve' | 'reject';

const decisionConfig = (kind: Kind, decision: Decision): DecisionConfig => decision === 'approve'
  ? {
      title: kind === 'resource' ? 'Publish this resource?' : 'Publish this event?',
      description: kind === 'resource'
        ? 'It appears in the Resources hub and the member who shared it is told.'
        : 'It appears in Events and the member who suggested it is told.',
      confirmLabel: 'Approve and publish',
      reason: 'none',
    }
  : {
      title: kind === 'resource' ? 'Reject this resource?' : 'Reject this event?',
      description: 'The member is told why by notification and email.',
      confirmLabel: 'Reject',
      destructive: true,
      reason: 'required',
    };

export default function ApprovalsQueue({ resourceCount, eventCount }: { resourceCount?: number; eventCount?: number }) {
  const queryClient = useQueryClient();
  const { handleError } = useErrorHandler();
  const [kind, setKind] = useState<Kind>('resource');
  const [pending, setPending] = useState<{ kind: Kind; id: string; decision: Decision } | null>(null);

  const resources = useQuery({
    queryKey: ['admin', 'resources'],
    queryFn: () => adminService.getPendingResources(),
  });
  const events = useQuery({
    queryKey: ['admin', 'events'],
    queryFn: () => adminService.getPendingEvents(),
  });

  const decide = useMutation({
    mutationFn: ({ kind, id, decision, reason }: { kind: Kind; id: string; decision: Decision; reason: string }) => {
      const body = decision === 'approve' ? { decision } as const : { decision, reason } as const;
      return kind === 'resource' ? adminService.decideResource(id, body) : adminService.decideEvent(id, body);
    },
    onSuccess: (_, { kind, decision }) => {
      const what = kind === 'resource' ? 'Resource' : 'Event';
      toast.success(decision === 'approve' ? `${what} published. The member has been notified.` : `${what} rejected. The member has been notified.`);
      setPending(null);
      queryClient.invalidateQueries({ queryKey: ['admin'] });
      queryClient.invalidateQueries({ queryKey: [kind === 'resource' ? 'resources' : 'events'] });
    },
    onError: (err) => handleError(err, 'Could not save the decision.'),
  });

  const preview = async (resource: PendingResource) => {
    if (resource.has_file) {
      try {
        await openProtectedFile(() => resourceService.getFile(resource.resource_id), resource.file_name || 'resource');
      } catch (err) {
        handleError(err, 'Could not open the file.');
      }
    } else if (resource.url) {
      window.open(resource.url, '_blank', 'noopener');
    }
  };

  const tabs: { id: Kind; label: string; count?: number }[] = [
    { id: 'resource', label: 'Resources', count: resources.data?.meta.total ?? resourceCount },
    { id: 'event', label: 'Events', count: events.data?.meta.total ?? eventCount },
  ];
  const active = kind === 'resource' ? resources : events;

  return (
    <div className="space-y-4">
      <div className="inline-flex rounded-full border border-[hsl(var(--border))] p-1" role="tablist" aria-label="Submission type">
        {tabs.map(tab => (
          <button
            key={tab.id}
            role="tab"
            aria-selected={kind === tab.id}
            onClick={() => setKind(tab.id)}
            className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors cursor-pointer ${
              kind === tab.id ? 'bg-primary-color text-white' : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            {tab.label}{tab.count ? ` (${tab.count})` : ''}
          </button>
        ))}
      </div>

      {active.isLoading ? (
        <LoadingCards />
      ) : active.isError ? (
        <EmptyState icon={<AlertTriangle size={22} />} title="Could not load the submissions" text="Check your connection and try again." />
      ) : kind === 'resource' ? (
        (resources.data?.data.length ?? 0) === 0
          ? <EmptyState icon={<BookOpen size={22} />} title="No resources waiting" text="Resources shared by doctors and organizations will appear here." />
          : resources.data!.data.map(resource => (
              <ResourceCard
                key={resource.resource_id}
                resource={resource}
                onPreview={() => preview(resource)}
                onDecide={(decision) => setPending({ kind: 'resource', id: resource.resource_id, decision })}
              />
            ))
      ) : (
        (events.data?.data.length ?? 0) === 0
          ? <EmptyState icon={<Calendar size={22} />} title="No events waiting" text="Events that members suggest will appear here." />
          : events.data!.data.map(event => (
              <EventCard
                key={event.event_id}
                event={event}
                onDecide={(decision) => setPending({ kind: 'event', id: event.event_id, decision })}
              />
            ))
      )}

      <DecisionDialog
        config={pending ? decisionConfig(pending.kind, pending.decision) : null}
        pending={decide.isPending}
        onCancel={() => setPending(null)}
        onConfirm={({ reason }) => pending && decide.mutate({ ...pending, reason })}
      />
    </div>
  );
}

function SubmittedBy({ name, type, email, at }: { name?: string | null; type?: string | null; email?: string | null; at?: string }) {
  return (
    <p className="text-sm text-muted-foreground flex flex-wrap items-center gap-1.5">
      <User size={14} />
      <span className="font-medium text-foreground">{name || 'A member'}</span>
      {type && <span>({USER_TYPE_LABELS[type] ?? type})</span>}
      {email && <span>· {email}</span>}
      {at && <span title={formatDate(at)}>· {timeAgo(at)}</span>}
    </p>
  );
}

function DecisionButtons({ onDecide }: { onDecide: (decision: Decision) => void }) {
  return (
    <>
      <Button size="sm" className="gap-1.5 ml-auto" onClick={() => onDecide('approve')}>
        <CheckCircle2 size={14} /> Approve
      </Button>
      <Button size="sm" variant="outline" className="gap-1.5 text-destructive" onClick={() => onDecide('reject')}>
        <XCircle size={14} /> Reject
      </Button>
    </>
  );
}

function ResourceCard({ resource, onPreview, onDecide }: {
  resource: PendingResource; onPreview: () => void; onDecide: (decision: Decision) => void;
}) {
  return (
    <Card className="p-5 space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <ToneBadge tone="blue">{resource.type}</ToneBadge>
        <ToneBadge tone="gray">{resource.category}</ToneBadge>
        <span className="text-xs text-muted-foreground uppercase">{resource.language}</span>
      </div>
      <p className="font-semibold text-lg">{resource.title}</p>
      <p className="text-sm whitespace-pre-wrap break-words line-clamp-6">{resource.description}</p>
      <SubmittedBy name={resource.submitter_name} type={resource.submitter_type} email={resource.submitter_email} at={resource.created_at} />
      <div className="flex flex-wrap items-center gap-2 pt-1">
        {resource.has_file && (
          <Button size="sm" variant="outline" className="gap-1.5" onClick={onPreview}>
            <FileText size={14} /> Open file{resource.file_size ? ` (${formatBytes(resource.file_size)})` : ''}
          </Button>
        )}
        {resource.url && (
          <Button size="sm" variant="outline" className="gap-1.5" onClick={() => window.open(resource.url, '_blank', 'noopener')}>
            <Link2 size={14} /> Open link
          </Button>
        )}
        <Link
          to={`/resources/${resource.resource_id}`}
          target="_blank"
          rel="noopener"
          className="inline-flex items-center gap-1 text-xs font-medium text-primary-color hover:underline"
        >
          See its page <ExternalLink size={12} />
        </Link>
        <DecisionButtons onDecide={onDecide} />
      </div>
    </Card>
  );
}

function EventCard({ event, onDecide }: { event: PendingEvent; onDecide: (decision: Decision) => void }) {
  const online = !!event.virtual_link;
  return (
    <Card className="p-5 space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <ToneBadge tone="blue">{event.type}</ToneBadge>
        <span className="text-sm text-muted-foreground">by {event.organizer}</span>
      </div>
      <p className="font-semibold text-lg">{event.title}</p>
      <div className="flex flex-wrap gap-x-5 gap-y-1 text-sm">
        <span className="flex items-center gap-1.5"><Calendar size={14} /> {formatDate(event.event_date, false)}</span>
        {event.event_time && (
          <span className="flex items-center gap-1.5"><Clock size={14} /> {event.event_time.slice(0, 5)} {event.timezone}</span>
        )}
        {online ? (
          <a href={event.virtual_link} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1.5 text-primary-color hover:underline break-all">
            <Globe size={14} /> {event.virtual_link}
          </a>
        ) : (
          <span className="flex items-center gap-1.5"><MapPin size={14} /> {event.location}</span>
        )}
      </div>
      <p className="text-sm whitespace-pre-wrap break-words line-clamp-6">{event.description}</p>
      <SubmittedBy name={event.suggester_name} type={event.suggester_type} email={event.suggester_email} at={event.created_at} />
      <div className="flex flex-wrap items-center gap-2 pt-1">
        <DecisionButtons onDecide={onDecide} />
      </div>
    </Card>
  );
}
