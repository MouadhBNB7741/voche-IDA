import { useTheme } from '../../contexts/ThemeContext';

export type Tone = 'red' | 'amber' | 'green' | 'blue' | 'gray';

const TONES: Record<Tone, { light: string; dark: string }> = {
  red: { light: 'bg-red-50 text-red-700 border-red-200', dark: 'bg-red-500/15 text-red-300 border-red-500/30' },
  amber: { light: 'bg-amber-50 text-amber-800 border-amber-200', dark: 'bg-amber-500/15 text-amber-300 border-amber-500/30' },
  green: { light: 'bg-emerald-50 text-emerald-700 border-emerald-200', dark: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30' },
  blue: { light: 'bg-sky-50 text-sky-700 border-sky-200', dark: 'bg-sky-500/15 text-sky-300 border-sky-500/30' },
  gray: { light: 'bg-zinc-100 text-zinc-700 border-zinc-200', dark: 'bg-zinc-500/15 text-zinc-300 border-zinc-500/30' },
};

/** Colours that follow the app's own light/dark switch (Tailwind's dark: follows the computer instead). */
export function useToneClass() {
  const { theme } = useTheme();
  const isDark = theme === 'dark';
  return (tone: Tone) => (isDark ? TONES[tone].dark : TONES[tone].light);
}

export function useDialogClasses() {
  const { theme } = useTheme();
  const isDark = theme === 'dark';
  return {
    isDark,
    content: isDark ? 'bg-zinc-900 text-white border-zinc-800' : 'bg-white text-zinc-950 border-zinc-200',
    menu: `border opacity-100 ${isDark ? 'bg-zinc-900 border-zinc-800 text-white' : 'bg-white border-zinc-200 text-zinc-950'}`,
    option: isDark
      ? 'text-white hover:bg-zinc-800 focus:bg-zinc-800 focus:text-white'
      : 'text-zinc-900 hover:bg-zinc-100 focus:bg-zinc-100 focus:text-zinc-900',
    muted: isDark ? 'text-zinc-400' : 'text-zinc-600',
  };
}

export function formatDate(value?: string | null, withTime = true): string {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(undefined, withTime
    ? { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }
    : { day: 'numeric', month: 'short', year: 'numeric' });
}

export function timeAgo(value?: string | null): string {
  if (!value) return '';
  const seconds = Math.round((Date.now() - new Date(value).getTime()) / 1000);
  if (Number.isNaN(seconds)) return '';
  if (seconds < 60) return 'just now';
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} h ago`;
  const days = Math.round(hours / 24);
  if (days < 30) return `${days} day${days === 1 ? '' : 's'} ago`;
  return formatDate(value, false);
}

export function formatBytes(size?: number | null): string {
  if (!size) return '';
  if (size < 1024 * 1024) return `${Math.max(1, Math.round(size / 1024))} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

export function formatDuration(seconds: number): string {
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (days) return `${days} d ${hours} h`;
  if (hours) return `${hours} h ${minutes} min`;
  return `${minutes} min`;
}

/**
 * Open a file that needs the login token (licences, uploaded resources) in a new tab.
 * The tab is opened before the download so the browser doesn't block it as a pop-up;
 * if pop-ups are blocked anyway, the file is downloaded instead.
 */
export async function openProtectedFile(load: () => Promise<Blob>, fileName = 'document'): Promise<void> {
  const tab = window.open('', '_blank');
  try {
    const blob = await load();
    const url = URL.createObjectURL(blob);
    if (tab) {
      tab.location.href = url;
    } else {
      const link = document.createElement('a');
      link.href = url;
      link.download = fileName;
      document.body.appendChild(link);
      link.click();
      link.remove();
    }
    window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
  } catch (error) {
    tab?.close();
    throw error;
  }
}

export const USER_TYPE_LABELS: Record<string, string> = {
  patient: 'Patient',
  caregiver: 'Caregiver',
  hcp: 'Doctor',
  org_member: 'Organization member',
  admin: 'Admin',
  no_role: 'No role yet',
};
