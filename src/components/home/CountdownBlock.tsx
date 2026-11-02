import React, { useState, useEffect } from 'react';
import { View, StyleSheet } from 'react-native';
import { Colors } from '../../constants/colors';
import { AppText } from '../ui/AppText';
import { countdownParts } from '../../utils/dateUtils';

interface CountdownBlockProps {
  targetDate: Date;
  label?: string;
}

export const CountdownBlock: React.FC<CountdownBlockProps> = ({ targetDate, label }) => {
  const [parts, setParts] = useState(countdownParts(targetDate));

  useEffect(() => {
    const t = setInterval(() => setParts(countdownParts(targetDate)), 1_000);
    return () => clearInterval(t);
  }, [targetDate]);

  const blocks = [
    { v: parts.D, l: 'Days' },
    { v: parts.H, l: 'Hours' },
    { v: parts.M, l: 'Minutes' },
    { v: parts.S, l: 'Seconds' },
  ];

  return (
    <View>
      <View style={styles.row}>
        {blocks.map((b, i) => (
          <View key={i} style={[styles.block, i < 3 && styles.blockBorder]}>
            <AppText variant="display" size={34} color={Colors.ink} style={styles.number}>
              {String(b.v).padStart(2, '0')}
            </AppText>
            <AppText variant="smallCaps" color={Colors.muted}>{b.l}</AppText>
          </View>
        ))}
      </View>
      {label && (
        <AppText variant="mono" color={Colors.light} style={{ fontSize: 10, marginTop: 14 }}>
          {label}
        </AppText>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    borderTopWidth: 1,
    borderBottomWidth: 1,
    borderColor: Colors.rule,
  },
  block: {
    flex: 1,
    alignItems: 'center',
    paddingVertical: 16,
  },
  blockBorder: {
    borderRightWidth: 1,
    borderRightColor: Colors.rule,
  },
  number: { lineHeight: 36 },
});