import { useState, useEffect } from 'react';
import { AppState } from 'react-native';

export type TimeOfDay = 'morning' | 'afternoon' | 'evening' | 'night' | 'late';

/**
 * Pure function to calculate time of day based on current hour.
 * Supports optional timezone string (e.g. 'America/New_York', 'Asia/Dhaka').
 */
export function getTimeOfDay(date: Date = new Date(), timezone?: string): TimeOfDay {
  let h = date.getHours();
  if (timezone) {
    try {
      const hourStr = new Intl.DateTimeFormat('en-US', {
        timeZone: timezone,
        hour: 'numeric',
        hour12: false,
      }).format(date);
      const parsed = parseInt(hourStr, 10);
      if (!isNaN(parsed)) {
        h = parsed;
      }
    } catch {}
  }

  if (h < 5) return 'late';
  if (h < 12) return 'morning';
  if (h < 17) return 'afternoon';
  if (h < 21) return 'evening';
  return 'night';
}

/**
 * Reactive hook that updates TimeOfDay dynamically:
 * - Refreshes every 30 seconds
 * - Refreshes immediately when app resumes from background
 */
export function useTimeOfDay(timezone?: string): TimeOfDay {
  const [tod, setTod] = useState<TimeOfDay>(() => getTimeOfDay(new Date(), timezone));

  useEffect(() => {
    const update = () => {
      setTod(getTimeOfDay(new Date(), timezone));
    };

    update();

    // Check every 30 seconds for time-of-day boundary transitions
    const interval = setInterval(update, 30_000);

    // Update immediately when app comes to foreground
    const sub = AppState.addEventListener('change', (nextState) => {
      if (nextState === 'active') {
        update();
      }
    });

    return () => {
      clearInterval(interval);
      sub.remove();
    };
  }, [timezone]);

  return tod;
}