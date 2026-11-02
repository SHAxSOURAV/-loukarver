/**
 * Format a Date to "h:mm AM/PM"
 */
export function formatTime(date: Date): string {
  const h = date.getHours();
  const m = date.getMinutes();
  const period = h >= 12 ? 'PM' : 'AM';
  const h12 = ((h + 11) % 12) + 1;
  return `${h12}:${String(m).padStart(2, '0')} ${period}`;
}

/**
 * Format "2026-04-25" → "Fri · Apr 25"
 */
export function formatDateShort(iso: string): string {
  if (!iso) return '';
  const dt = new Date(iso.replace(/\./g, '-') + 'T00:00:00');
  return dt.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
}

/**
 * Format 24hr time "19:30" → "7:30 PM"
 */
export function format24to12(t24: string): string {
  if (!t24) return '';
  const [h, m] = t24.split(':').map(Number);
  const period = h >= 12 ? 'PM' : 'AM';
  const h12 = ((h + 11) % 12) + 1;
  return `${h12}:${String(m).padStart(2, '0')} ${period}`;
}

/**
 * Days between two dates
 */
export function daysBetween(a: Date, b: Date): number {
  return Math.floor(Math.abs(b.getTime() - a.getTime()) / 86_400_000);
}

/**
 * Countdown parts from now to a target date
 */
export function countdownParts(target: Date): { D: number; H: number; M: number; S: number } {
  const diff = Math.max(target.getTime() - Date.now(), 0);
  return {
    D: Math.floor(diff / 86_400_000),
    H: Math.floor((diff % 86_400_000) / 3_600_000),
    M: Math.floor((diff % 3_600_000) / 60_000),
    S: Math.floor((diff % 60_000) / 1_000),
  };
}

/**
 * Today's ISO date string "YYYY-MM-DD"
 */
export function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}