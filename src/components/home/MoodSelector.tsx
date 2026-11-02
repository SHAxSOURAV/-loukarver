import React from 'react';
import { View, Pressable, StyleSheet } from 'react-native';
import { Colors } from '../../constants/colors';
import { AppText } from '../ui/AppText';
import { Mood } from '../../types';

interface MoodSelectorProps {
  moods: Mood[];
  selected: number;
  onSelect: (index: number) => void;
}

export const MoodSelector: React.FC<MoodSelectorProps> = ({ moods, selected, onSelect }) => (
  <View>
    {moods.map((m, i) => (
      <Pressable
        key={i}
        onPress={() => onSelect(i)}
        style={[styles.row, i < moods.length - 1 && styles.border]}
      >
        <AppText size={20} color={Colors.accent} style={{ width: 28 }}>{m.mark}</AppText>
        <AppText variant="heading" size={18} style={{ flex: 1 }}>{m.label}</AppText>
        <AppText variant="mono" style={{ fontSize: 10 }}>
          {String(i + 1).padStart(2, '0')}
        </AppText>
        {selected === i && <View style={styles.activeDot} />}
      </Pressable>
    ))}
  </View>
);

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 16,
    gap: 16,
  },
  border: { borderBottomWidth: 1, borderBottomColor: Colors.rule },
  activeDot: {
    width: 8, height: 8, borderRadius: 4,
    backgroundColor: Colors.accent, marginLeft: 8,
  },
});