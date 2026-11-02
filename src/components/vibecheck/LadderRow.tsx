import React from 'react';
import { View, Pressable, StyleSheet } from 'react-native';
import { Colors } from '../../constants/colors';
import { AppText } from '../ui/AppText';

export interface LadderStage {
  l: string;
  sub: string;
}

interface LadderRowProps {
  stage: LadderStage;
  index: number;
  isLast: boolean;
  isMine: boolean;
  disabled?: boolean;
  showPartnerBadge?: boolean;
  partnerName?: string;
  onPress: () => void;
}

export const LadderRow: React.FC<LadderRowProps> = ({
  stage, index, isLast, isMine, disabled, showPartnerBadge, partnerName, onPress,
}) => (
  <Pressable
    style={[styles.row, disabled && styles.rowDisabled]}
    onPress={onPress}
    disabled={disabled}
  >
    {/* Connector dot */}
    <View style={[
      styles.dot,
      isMine ? styles.dotMine : disabled ? styles.dotDisabled : styles.dotDefault,
    ]} />
    <View style={{ flex: 1, paddingVertical: 4 }}>
      <View style={{ flexDirection: 'row', alignItems: 'baseline', gap: 8, flexWrap: 'wrap', marginBottom: 3 }}>
        <AppText variant="heading" size={17} color={isMine || isLast ? (disabled ? Colors.light : Colors.ink) : (disabled ? Colors.light : Colors.muted)}>
          {stage.l}
        </AppText>
        {isLast && <AppText variant="mono" color={disabled ? Colors.light : Colors.accent} style={{ fontSize: 9 }}>· GRADUATION</AppText>}
        {isMine && (
          <View style={styles.badge}>
            <AppText variant="mono" style={{ fontSize: 9 }} color={Colors.ink}>YOU</AppText>
          </View>
        )}
        {showPartnerBadge && partnerName && (
          <View style={styles.badgeAccent}>
            <AppText variant="mono" style={{ fontSize: 9 }} color={Colors.bone}>
              {partnerName.toUpperCase().slice(0, 8)}
            </AppText>
          </View>
        )}
      </View>
      <AppText variant="serifItalic" size={13} color={disabled ? '#ccc' : Colors.light} style={{ lineHeight: 19 }}>{stage.sub}</AppText>
    </View>
  </Pressable>
);

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 14,
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: Colors.rule,
  },
  rowDisabled: {
    opacity: 0.4,
  },
  dot: { width: 22, height: 22, borderRadius: 11, marginTop: 2, borderWidth: 2 },
  dotDefault: { backgroundColor: Colors.bone, borderColor: Colors.rule },
  dotMine: { backgroundColor: Colors.ink, borderColor: Colors.ink },
  dotDisabled: { backgroundColor: Colors.bone, borderColor: '#ddd' },
  badge: {
    borderWidth: 1, borderColor: Colors.ink, borderRadius: 99,
    paddingHorizontal: 6, paddingVertical: 1,
  },
  badgeAccent: {
    backgroundColor: Colors.accent, borderRadius: 99,
    paddingHorizontal: 6, paddingVertical: 1,
  },
});