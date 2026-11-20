import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';
import {
  AlertTriangle, Ban, Bot, CheckCircle2, ExternalLink, EyeOff, Flag, MessageSquare, ShieldCheck, Trash2, UserX,
} from 'lucide-react';
import { Button } from '../../components/ui/button';
import { Card } from '../../components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { useErrorHandler } from '../../hooks/useErrorHandler';
import {
  moderationService, type ModerationAction, type QueueFilters, type QueueItem, type ReportPriority,
} from '../../services/moderationService';
import { DecisionDialog, EmptyState, LoadingCards, Pager, ToneBadge, type DecisionConfig } from './AdminParts';
import { formatDate, timeAgo, useDialogClasses, USER_TYPE_LABELS, type Tone } from './adminUtils';

const REASONS: Record<string, string> = {
  misinformation: 'Misinformation',
  harassment: 'Harassment',
  self_harm: 'Possible self-harm',
  spam: 'Spam',
  inappropriate_content: 'Inappropriate content',
  medical_advice: 'Unsafe medical advice',
  other: 'Other',
};

const PRIORITY_TONE: Record<ReportPriority, Tone> = { critical: 'red', high: 'amber', normal: 'gray' };

const CONTENT_STATUS: Record<string, { label: string; tone: Tone }> = {
  approved: { label: 'Visible', tone: 'green' },
  flagged: { label: 'Visible, flagged', tone: 'amber' },
  pending: { label: 'Held for review', tone: 'amber' },
  hidden: { label: 'Hidden', tone: 'red' },
  removed: { label: 'Removed', tone: 'red' },
};

const DECISION_LABELS: Record<string, string> = {
  approve_content: 'Approved',
  hide_content: 'Hidden',
  delete_content: 'Deleted',
  warn_user: 'Author warned',
  suspend_user: 'Author suspended',
  ban_user: 'Author banned',
};

const DECISIONS: Record<ModerationAction, DecisionConfig> = {
  approve_content: {
    title: 'Approve this content?',
    description: 'It stays visible (or is published if it was held) and every open report on it is dismissed.',
    confirmLabel: 'Approve',
    reason: 'optional',
    reasonHint: 'Note for the author, if any',
  },
  hide_content: {
    title: 'Hide this content?',
    description: 'Members no longer see it. The author is told why.',
    confirmLabel: 'Hide',
    reason: 'optional',
  },
  delete_content: {
    title: 'Delete this content?',
    description: 'It is removed for everyone. The author is told why.',
    confirmLabel: 'Delete',
    destructive: true,
    reason: 'optional',
  },
  warn_user: {
    title: 'Warn the author?',
    description: 'The author gets a warning with your reason. It is kept in their record.',
    confirmLabel: 'Send warning',
    reason: 'required',
    offerRemoveContent: true,
  },
  suspend_user: {
    title: 'Suspend the author?',
    description: 'They are signed out and cannot use the platform until the suspension ends.',
    confirmLabel: 'Suspend',
    destructive: true,
    reason: 'required',
    askDuration: true,
    offerRemoveContent: true,
  },
  ban_user: {
    title: 'Ban the author?',
    description: 'They are signed out and cannot come back unless an admin lifts the ban.',
    confirmLabel: 'Ban',
    destructive: true,
    reason: 'required',
    offerRemoveContent: true,
  },
};

const ALL = 'all';

export default function ModerationQueue() {
  const queryClient = useQueryClient();
  const { handleError } = useErrorHandler();
  const classes = useDialogClasses();
  const [status, setStatus] = useState<'open' | 'closed'>('open');
  const [priority, setPriority] = useState<string>(ALL);
  const [targetType, setTargetType] = useState<string>(ALL);
  const [page, setPage] = useState(1);
  const [pendingDecision, setPendingDecision] = useState<{ item: QueueItem; action: ModerationAction } | null>(null);

  const filters: QueueFilters = {
    status,
    page,
    limit: 10,
    ...(priority !== ALL && { priority: priority as ReportPriority }),
    ...(targetType !== ALL && { target_type: targetType as 'post' | 'comment' }),
  };
  const queue = useQuery({
    queryKey: ['admin', 'moderation', filters],
    queryFn: () => moderationService.getQueue(filters),
  });

  const decide = useMutation({
    mutationFn: ({ item, action, reason, durationHours, removeContent }: {
      item: QueueItem; action: ModerationAction; reason: string; durationHours?: number; removeContent: boolean;
    }) => moderationService.decide(item.report_id, {
      action,
      ...(reason && { reason }),
      ...(action === 'suspend_user' && { duration_hours: durationHours }),
      ...(removeContent && { remove_content: true }),
    }),
    onSuccess: (_, { action }) => {
      toast.success(`${DECISION_LABELS[action]}. The author has been notified.`);
      setPendingDecision(null);
      queryClient.invalidateQueries({ queryKey: ['admin'] });
    },
    onError: (err) => handleError(err, 'Could not save the decision.'),
  });

  const changeFilter = (setter: (v: any) => void) => (value: any) => { setter(value); setPage(1); };
  const items = queue.data?.data ?? [];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <div className="inline-flex rounded-full border border-[hsl(var(--border))] p-1" role="tablist" aria-label="Report status">
          {(['open', 'closed'] as const).map(value => (
            <button
              key={value}
              role="tab"
              aria-selected={status === value}
              onClick={() => changeFilter(setStatus)(value)}
              className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors cursor-pointer ${
                status === value ? 'bg-primary-color text-white' : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              {value === 'open' ? 'To review' : 'Decided'}
            </button>
          ))}
        </div>
        <Select value={priority} onValueChange={changeFilter(setPriority)}>
          <SelectTrigger className="w-[150px]" aria-label="Priority"><SelectValue /></SelectTrigger>
          <SelectContent className={classes.menu}>
            <SelectItem value={ALL} className={`cursor-pointer ${classes.option}`}>All priorities</SelectItem>
            <SelectItem value="critical" className={`cursor-pointer ${classes.option}`}>Critical</SelectItem>
            <SelectItem value="high" className={`cursor-pointer ${classes.option}`}>High</SelectItem>
            <SelectItem value="normal" className={`cursor-pointer ${classes.option}`}>Normal</SelectItem>
          </SelectContent>
        </Select>
        <Select value={targetType} onValueChange={changeFilter(setTargetType)}>
          <SelectTrigger className="w-[150px]" aria-label="Content type"><SelectValue /></SelectTrigger>
          <SelectContent className={classes.menu}>
            <SelectItem value={ALL} className={`cursor-pointer ${classes.option}`}>All content</SelectItem>
            <SelectItem value="post" className={`cursor-pointer ${classes.option}`}>Posts</SelectItem>
            <SelectItem value="comment" className={`cursor-pointer ${classes.option}`}>Replies</SelectItem>
          </SelectContent>
        </Select>
        {queue.data && (
          <span className="text-sm text-muted-foreground ml-auto">
            {queue.data.meta.total} report{queue.data.meta.total === 1 ? '' : 's'}
          </span>
        )}
      </div>

      {queue.isLoading ? (
        <LoadingCards />
      ) : queue.isError ? (
        <EmptyState icon={<AlertTriangle size={22} />} title="Could not load the queue" text="Check your connection and try again." />
      ) : items.length === 0 ? (
        <EmptyState
          icon={<ShieldCheck size={22} />}
          title={status === 'open' ? 'Nothing to review' : 'No decisions yet'}
          text={status === 'open' ? 'Reported and flagged content will appear here, most urgent first.' : 'Decided reports will appear here.'}
        />
      ) : (
        <div className="space-y-4">
          {items.map(item => (
            <ReportCard
              key={item.report_id}
              item={item}
              onDecide={(action) => setPendingDecision({ item, action })}
            />
          ))}
          <Pager page={page} pages={queue.data?.meta.pages ?? 1} onChange={setPage} />
        </div>
      )}

      <DecisionDialog
        config={pendingDecision ? DECISIONS[pendingDecision.action] : null}
        pending={decide.isPending}
        onCancel={() => setPendingDecision(null)}
        onConfirm={(values) => pendingDecision && decide.mutate({ item: pendingDecision.item, action: pendingDecision.action, ...values })}
      />
    </div>
  );
}

function ReportCard({ item, onDecide }: { item: QueueItem; onDecide: (action: ModerationAction) => void }) {
  const isOpen = ['pending', 'under_review'].includes(item.status);
  const content = item.current_content ?? item.reported_content;
  const editedSinceReport = !!item.reported_content && !!item.current_content && item.reported_content !== item.current_content;
  const contentStatus = item.content_deleted ? CONTENT_STATUS.removed : item.content_status ? CONTENT_STATUS[item.content_status] : null;
  const history = item.author_history;
  const postLink = item.post_id && item.community_id ? `/community/${item.community_id}/posts/${item.post_id}` : null;
  const authorIsAdmin = item.author_type === 'admin';

  return (
    <Card className={`p-5 space-y-4 ${item.priority === 'critical' && isOpen ? 'border-red-400/60' : ''}`}>
      <div className="flex flex-wrap items-center gap-2">
        <ToneBadge tone={PRIORITY_TONE[item.priority] ?? 'gray'}>
          {item.priority === 'critical' && <AlertTriangle size={12} />}
          {item.priority[0].toUpperCase() + item.priority.slice(1)}
        </ToneBadge>
        <span className="font-semibold">{REASONS[item.reason] ?? item.reason}</span>
        <span className="text-sm text-muted-foreground flex items-center gap-1">
          {item.source === 'auto_filter'
            ? <><Bot size={14} /> Automatic filter</>
            : <><Flag size={14} /> Reported by {item.reporter_name || 'a member'}</>}
        </span>
        {item.open_reports_on_target > 1 && (
          <ToneBadge tone="amber">{item.open_reports_on_target} open reports</ToneBadge>
        )}
        <span className="text-xs text-muted-foreground ml-auto" title={formatDate(item.created_at)}>{timeAgo(item.created_at)}</span>
      </div>

      {item.description && <p className="text-sm text-muted-foreground italic">"{item.description}"</p>}

      <div className="rounded-xl border border-[hsl(var(--border))] bg-muted/20 p-4 space-y-2">
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <MessageSquare size={14} className="text-muted-foreground" />
          <span className="font-medium">
            {item.target_type === 'post' ? 'Post' : item.target_type === 'comment' ? 'Reply' : item.target_type}
            {item.post_title && <>{item.target_type === 'comment' ? ' on ' : ': '}<span className="italic">{item.post_title}</span></>}
          </span>
          {contentStatus && <ToneBadge tone={contentStatus.tone}>{contentStatus.label}</ToneBadge>}
          {!!item.moderation_score && item.moderation_score > 0 && (
            <ToneBadge tone={item.moderation_score >= 0.7 ? 'red' : item.moderation_score >= 0.3 ? 'amber' : 'gray'}>
              Filter score {item.moderation_score.toFixed(2)}
            </ToneBadge>
          )}
        </div>
        {content
          ? <p className="text-sm whitespace-pre-wrap break-words max-h-48 overflow-y-auto">{content}</p>
          : <p className="text-sm text-muted-foreground">The content is no longer available.</p>}
        {editedSinceReport && (
          <details className="text-xs text-muted-foreground">
            <summary className="cursor-pointer">Edited since it was reported: see the reported version</summary>
            <p className="mt-2 whitespace-pre-wrap break-words">{item.reported_content}</p>
          </details>
        )}
        {item.flagged_reason && item.flagged_reason !== item.description && (
          <p className="text-xs text-muted-foreground">{item.flagged_reason}</p>
        )}
        {postLink && (
          <Link to={postLink} target="_blank" rel="noopener" className="inline-flex items-center gap-1 text-xs font-medium text-primary-color hover:underline">
            Open in the community <ExternalLink size={12} />
          </Link>
        )}
      </div>

      {item.author_name && (
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <span className="text-muted-foreground">Author:</span>
          <span className="font-medium">{item.author_name}</span>
          {item.author_type && <span className="text-muted-foreground">({USER_TYPE_LABELS[item.author_type] ?? item.author_type})</span>}
          {item.author_status === 'suspended' && (
            <ToneBadge tone="red">
              {item.author_suspended_until ? `Suspended until ${formatDate(item.author_suspended_until)}` : 'Banned'}
            </ToneBadge>
          )}
          {history && (
            <span className="text-xs text-muted-foreground">
              {[
                history.warnings && `${history.warnings} warning${history.warnings === 1 ? '' : 's'}`,
                history.suspensions && `${history.suspensions} suspension${history.suspensions === 1 ? '' : 's'}`,
                history.bans && `${history.bans} ban${history.bans === 1 ? '' : 's'}`,
                history.content_removed && `${history.content_removed} removed`,
                `${history.reports_upheld} of ${history.reports_received} reports upheld`,
              ].filter(Boolean).join(' · ')}
            </span>
          )}
        </div>
      )}

      {isOpen ? (
        <div className="flex flex-wrap gap-2 pt-1">
          <Button size="sm" variant="outline" className="gap-1.5" onClick={() => onDecide('approve_content')}>
            <CheckCircle2 size={14} /> Approve
          </Button>
          <Button size="sm" variant="outline" className="gap-1.5" onClick={() => onDecide('hide_content')}>
            <EyeOff size={14} /> Hide
          </Button>
          <Button size="sm" variant="outline" className="gap-1.5 text-destructive" onClick={() => onDecide('delete_content')}>
            <Trash2 size={14} /> Delete
          </Button>
          {!authorIsAdmin && item.author_id && (
            <>
              <span className="w-px bg-[hsl(var(--border))] mx-1" aria-hidden />
              <Button size="sm" variant="outline" className="gap-1.5" onClick={() => onDecide('warn_user')}>
                <AlertTriangle size={14} /> Warn
              </Button>
              <Button size="sm" variant="outline" className="gap-1.5 text-destructive" onClick={() => onDecide('suspend_user')}>
                <UserX size={14} /> Suspend
              </Button>
              <Button size="sm" variant="outline" className="gap-1.5 text-destructive" onClick={() => onDecide('ban_user')}>
                <Ban size={14} /> Ban
              </Button>
            </>
          )}
        </div>
      ) : (
        <p className="text-sm text-muted-foreground border-t border-[hsl(var(--border))] pt-3">
          <span className="font-medium text-foreground">{DECISION_LABELS[item.action_taken ?? ''] ?? item.status}</span>
          {item.moderator_name && <> by {item.moderator_name}</>}
          {item.resolved_at && <> on {formatDate(item.resolved_at)}</>}
          {item.resolution_notes && <>: {item.resolution_notes}</>}
        </p>
      )}
    </Card>
  );
}
