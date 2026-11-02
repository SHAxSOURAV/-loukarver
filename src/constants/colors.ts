export const Colors = {
  ink: '#1A1614',
  ink2: '#2E2722',
  bone: '#EFE7DD',
  cream: '#EAE2D4',
  cream2: '#DED3BF',
  rule: '#C9BDA5',
  muted: '#8A7E6C',
  light: '#B5A995',
  accent: '#B8553E',
  accentDeep: '#8E3F2C',
  sage: '#6B7A5C',
  white: '#FFFFFF',
  transparent: 'transparent',
} as const;

export type ColorKey = keyof typeof Colors;