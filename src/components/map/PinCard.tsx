import React from 'react';
import { View, Pressable, StyleSheet } from 'react-native';
import { Colors } from '../../constants/colors';
import { AppText } from '../ui/AppText';
import { MapPin } from '../../types';

const PIN_META = {
  home: { label: 'Home', color: Colors.muted },
  together: { label: 'Together', color: Colors.accent },
  upcoming: { label: 'Upcoming', color: Colors.sage },
  bucket: { label: 'Bucket', color: Colors.light },
};

interface PinCardProps {
  pin: MapPin & { deletion_request?: any };
  onPress: () => void;
}

export const PinCard: React.FC<PinCardProps> = ({ pin: p, onPress }) => {
  const meta = PIN_META[p.type];
  return (
    <Pressable style={[styles.card, p.deletion_request && { borderColor: '#D9534F' }]} onPress={onPress}>
      <View style={[styles.dot, { backgroundColor: p.deletion_request ? '#D9534F' : meta.color }]} />
      <View style={{ flex: 1 }}>
        <AppText variant="heading" size={17} style={{ marginBottom: 2 }}>{p.city}</AppText>
        <View style={{ flexDirection: 'row', gap: 10, flexWrap: 'wrap' }}>
          <AppText variant="mono" color={Colors.muted} style={{ fontSize: 9 }}>{p.country.toUpperCase()}</AppText>
          <AppText variant="mono" color={p.deletion_request ? '#D9534F' : meta.color} style={{ fontSize: 9 }}>· {p.deletion_request ? 'PENDING REMOVAL' : meta.label.toUpperCase()}</AppText>
          {p.dates && <AppText variant="mono" color={Colors.accent} style={{ fontSize: 9 }}>· {p.dates.toUpperCase()}</AppText>}
        </View>
      </View>
    </Pressable>
  );
};

const styles = StyleSheet.create({
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
    backgroundColor: Colors.bone,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: Colors.rule,
    padding: 16,
    marginBottom: 10,
    shadowColor: Colors.ink2,
    shadowOpacity: 0.04,
    shadowRadius: 6,
    elevation: 1,
  },
  dot: {
    width: 12, height: 12, borderRadius: 6,
    borderWidth: 2, borderColor: Colors.bone,
  },
});