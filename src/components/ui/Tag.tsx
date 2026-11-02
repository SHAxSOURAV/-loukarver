import React from 'react';
import { Pressable, StyleSheet, PressableProps } from 'react-native';
import { Colors } from '../../constants/colors';
import { AppText } from './AppText';

interface TagProps extends PressableProps {
  active?: boolean;
  children: React.ReactNode;
}

export const Tag: React.FC<TagProps> = ({ active = false, children, ...rest }) => (
  <Pressable
    style={[styles.tag, active && styles.tagActive]}
    {...rest}
  >
    <AppText variant="smallCaps" style={[styles.text, active && styles.textActive]}>
      {children}
    </AppText>
  </Pressable>
);

const styles = StyleSheet.create({
  tag: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 99,
    borderWidth: 1,
    borderColor: Colors.rule,
  },
  tagActive: {
    backgroundColor: Colors.ink,
    borderColor: Colors.ink,
  },
  text: { color: Colors.muted },
  textActive: { color: Colors.bone },
});