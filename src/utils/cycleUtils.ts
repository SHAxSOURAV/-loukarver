export type CyclePhase = 'menstrual' | 'follicular' | 'ovulatory' | 'luteal';

export interface CycleState {
  dayOfCycle: number;
  phase: CyclePhase;
  phaseLabel: string;
  phaseRange: string;
  hormones: string;
}

export function computeCycleState(
  lastPeriodIso: string,
  cycleLength: number,
  periodDuration: number,
): CycleState | null {
  if (!lastPeriodIso) return null;

  const start = new Date(lastPeriodIso + 'T00:00:00');
  const dayOfCycle = (Math.floor((Date.now() - start.getTime()) / 86_400_000) % cycleLength) + 1;

  if (dayOfCycle <= periodDuration) {
    return {
      dayOfCycle, phase: 'menstrual', phaseLabel: 'Menstrual',
      phaseRange: `Days 1–${periodDuration}`, hormones: 'LOW ESTROGEN & PROGESTERONE',
    };
  } else if (dayOfCycle <= 13) {
    return {
      dayOfCycle, phase: 'follicular', phaseLabel: 'Follicular',
      phaseRange: 'Days 6–13', hormones: 'ESTROGEN RISING',
    };
  } else if (dayOfCycle <= 16) {
    return {
      dayOfCycle, phase: 'ovulatory', phaseLabel: 'Ovulatory',
      phaseRange: 'Days 14–16', hormones: 'ESTROGEN PEAK / LH SURGE',
    };
  } else {
    return {
      dayOfCycle, phase: 'luteal', phaseLabel: 'Luteal',
      phaseRange: `Days 17–${cycleLength}`, hormones: 'PROGESTERONE DOMINANT',
    };
  }
}

export const PHASE_DESCRIPTIONS: Record<CyclePhase, string> = {
  menstrual: 'Estrogen and progesterone have dropped to their lowest. The body wants rest. This is a reset.',
  follicular: 'FSH drives follicle development and estrogen climbs. Energy and openness tend to rise.',
  ovulatory: 'LH surges and releases a mature egg. Estrogen peaks. Often the most expressive, confident window.',
  luteal: 'Progesterone dominant. In later days, serotonin can dip, which is why mood can feel more tender.',
};