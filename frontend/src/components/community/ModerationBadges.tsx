import { BadgeCheck, Clock, EyeOff } from 'lucide-react';
import { Badge } from '../ui/badge';
import { useTheme } from '../../contexts/ThemeContext';
import type { ModerationStatus } from '../../types/db';

type Tone = 'amber' | 'red' | 'sky';

const STATUS_LABELS: Partial<Record<ModerationStatus, { label: string; hint: string; tone: Tone }>> = {
  pending: {
    label: 'Pending review',
    hint: 'Only you can see this until a moderator reviews it.',
    tone: 'amber',
  },
  flagged: {
    label: 'Pending review',
    hint: 'Members reported this. Only you can see it until a moderator reviews it.',
    tone: 'amber',
  },
  hidden: { label: 'Hidden by a moderator', hint: 'Members can no longer see this.', tone: 'red' },
  removed: { label: 'Removed by a moderator', hint: 'Members can no longer see this.', tone: 'red' },
};

// The app switches themes with a class Tailwind's dark: variant doesn't follow, so pick colors here
const TONES: Record<Tone, { light: string; dark: string }> = {
  amber: {
    light: 'bg-amber-100 text-amber-800 border-amber-300',
    dark: 'bg-amber-500/15 text-amber-300 border-amber-500/40',
  },
  red: {
    light: 'bg-red-100 text-red-800 border-red-300',
    dark: 'bg-red-500/15 text-red-300 border-red-500/40',
  },
  sky: {
    light: 'bg-sky-100 text-sky-800 border-sky-300',
    dark: 'bg-sky-500/15 text-sky-300 border-sky-500/40',
  },
};

function useToneClass(tone: Tone): string {
  const { theme } = useTheme();
  return TONES[tone][theme === 'dark' ? 'dark' : 'light'];
}

/**
 * Shown on content that isn't public: the author's own held posts, or anything an admin is looking at.
 */
export function ModerationStatusBadge({ status }: { status?: ModerationStatus | null }) {
  const info = status ? STATUS_LABELS[status] : undefined;
  const toneClass = useToneClass(info?.tone ?? 'amber');
  if (!info) return null;
  const Icon = info.tone === 'amber' ? Clock : EyeOff;
  return (
    <Badge variant="outline" title={info.hint} className={`gap-1 text-[10px] py-0 px-2 font-semibold ${toneClass}`}>
      <Icon size={11} aria-hidden="true" />
      {info.label}
    </Badge>
  );
}

export function moderationHint(status?: ModerationStatus | null): string | null {
  return (status && STATUS_LABELS[status]?.hint) || null;
}

/**
 * Next to the name of a doctor whose medical license an admin has approved.
 */
export function VerifiedHcpBadge({ show }: { show?: boolean }) {
  const toneClass = useToneClass('sky');
  if (!show) return null;
  return (
    <Badge
      variant="outline"
      title="Healthcare professional with a verified medical license"
      className={`gap-1 text-[10px] py-0 px-2 font-semibold ${toneClass}`}
    >
      <BadgeCheck size={11} aria-hidden="true" />
      Verified HCP
    </Badge>
  );
}
