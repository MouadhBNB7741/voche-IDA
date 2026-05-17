/**
 * Agrovia — Date Utilities
 * 
 * Standardized date formatting and time transformation helpers.
 */

/**
 * Formats a date string according to Agrovia messaging standards:
 * - < 1 min: "X sec"
 * - < 1 hour: "X min"
 * - < 1 day: "X hours"
 * - < 30 days: "X days"
 * - > 30 days: "DD/MM/YYYY HH:MM AM/PM"
 */
export function formatMessageDate(dateString: string | Date | number): string {
  const date = dateString instanceof Date ? dateString : new Date(dateString);
  const now = new Date();
  const diffInSec = Math.floor((now.getTime() - date.getTime()) / 1000);

  // If time is in the future or very close to now
  if (diffInSec < 0) return 'Just now';
  if (diffInSec < 60) return `${diffInSec > 0 ? diffInSec : 1} sec ago`;
  
  const diffInMin = Math.floor(diffInSec / 60);
  if (diffInMin < 60) return `${diffInMin} min ago`;
  
  const diffInHours = Math.floor(diffInMin / 60);
  if (diffInHours < 24) return `${diffInHours} hours ago`;
  
  const diffInDays = Math.floor(diffInHours / 24);
  if (diffInDays < 30) return `${diffInDays} days ago`;

  // Full date for older messages: e.g. 22/03/2026 01:05 PM
  return date.toLocaleString('en-GB', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: true
  }).replace(',', '');
}

/**
 * Standard date-only formatter (DD/MM/YYYY)
 */
export function formatDate(date: string | Date): string {
  const d = new Date(date);
  return d.toLocaleDateString('en-GB');
}

/**
 * Standard time-only formatter (HH:MM AM/PM)
 */
export function formatTime(date: string | Date): string {
  const d = new Date(date);
  return d.toLocaleTimeString('en-GB', { 
    hour: '2-digit', 
    minute: '2-digit', 
    hour12: true 
  });
}

/**
 * Relative time: "2 hours ago", "3 days ago", "just now"
 */
const UNITS: [Intl.RelativeTimeFormatUnit, number][] = [
  ['year', 31536000],
  ['month', 2592000],
  ['week', 604800],
  ['day', 86400],
  ['hour', 3600],
  ['minute', 60],
  ['second', 1],
];

const rtf = new Intl.RelativeTimeFormat('en', { numeric: 'auto' });

export function formatDistanceToNow(dateString: string | Date): string {
  const date = dateString instanceof Date ? dateString : new Date(dateString);
  const now = new Date();
  const diffSec = Math.round((date.getTime() - now.getTime()) / 1000);

  if (Math.abs(diffSec) < 10) return 'just now';

  for (const [unit, seconds] of UNITS) {
    if (Math.abs(diffSec) >= seconds) {
      const value = Math.round(diffSec / seconds);
      return rtf.format(value, unit);
    }
  }

  return 'just now';
}
