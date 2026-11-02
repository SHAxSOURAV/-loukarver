import React from 'react';
import { View, StyleSheet, ViewStyle } from 'react-native';
import { Colors } from '../../constants/colors';

interface RuleProps {
  color?: string;
  style?: ViewStyle;
}

export const Rule: React.FC<RuleProps> = ({ color = Colors.rule, style }) => (
  <View style={[styles.rule, { backgroundColor: color }, style]} />
);

const styles = StyleSheet.create({
  rule: { height: 1, width: '100%' },
});