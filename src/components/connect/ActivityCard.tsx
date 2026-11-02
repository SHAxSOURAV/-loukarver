import React from 'react';
import { View, Pressable, StyleSheet } from 'react-native';
import { Colors } from '../../constants/colors';
import { AppText } from '../ui/AppText';
import { Activity } from '../../types';

interface ActivityCardProps {
  activity: Activity;
  onPress: () => void;
}

export const ActivityCard: React.FC<ActivityCardProps> = ({ activity: a, onPress }) => {
  const statusColor = a.status === 'active' ? Colors.accent : a.status === 'completed' ? Colors.sage : Colors.muted;
  const statusLabel = a.status === 'active' ? '● ACTIVE' : a.status === 'completed' ? '✓ DONE' : '○ PROPOSED';

  return (
    <Pressable style={styles.card} onPress={onPress}>
      <View style={styles.iconWrap}>
        <AppText size={22} color={Colors.accent}>{a.mark}</AppText>
      </View>
      <View style={{ flex: 1 }}>
        <View style={styles.titleRow}>
          <AppText variant="heading" size={17} style={{ flex: 1 }}>{a.label}</AppText>
          <AppText variant="mono" color={Colors.light} style={{ fontSize: 9 }}>{a.duration.toUpperCase()}</AppText>
        </View>
        <AppText variant="serifItalic" size={13} color={Colors.muted} style={{ lineHeight: 19, marginBottom: 10 }}>
          {a.description}
        </AppText>
        <View style={{ flexDirection: 'row', gap: 8 }}>
          <AppText variant="mono" color={statusColor} style={{ fontSize: 9 }}>{statusLabel}</AppText>
        </View>
      </View>
    </Pressable>
  );
};

const styles = StyleSheet.create({
  card: {
    flexDirection: 'row',
    gap: 14,
    backgroundColor: Colors.bone,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: Colors.rule,
    padding: 18,
    shadowColor: Colors.ink2,
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
    marginBottom: 10,
  },
  iconWrap: {
    width: 48, height: 48, borderRadius: 10,
    backgroundColor: Colors.cream,
    alignItems: 'center', justifyContent: 'center',
  },
  titleRow: { flexDirection: 'row', alignItems: 'baseline', gap: 10, marginBottom: 4 },
});