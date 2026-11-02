export const Config = {
  DEMO_USERS: {
    lou: { name: 'Lou', city: 'Los Angeles', shortCity: 'Los Angeles', tz: -7, initial: 'L' },
    amanda: { name: 'Amanda', city: 'Turin', shortCity: 'Turin', tz: 1, initial: 'A' },
  },
  VIBE_CHECK: {
    DAILY_CARD_LIMIT: 3,
    CONNECTION_MAX_DAYS: 90,
  },
} as const;

export type UserId = 'lou' | 'amanda';