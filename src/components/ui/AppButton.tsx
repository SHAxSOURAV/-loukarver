import React from 'react';
import {
  Pressable,
  StyleSheet,
  ViewStyle,
  TextStyle,
  ActivityIndicator,
  PressableProps,
} from 'react-native';
import { Colors } from '../../constants/colors';
import { Fonts } from '../../constants/fonts';
import { AppText } from './AppText';

type Variant = 'solid' | 'outline' | 'accent' | 'ghost' | 'bone' | 'link';
type Size = 'sm' | 'md' | 'lg';

interface AppButtonProps extends PressableProps {
  children: React.ReactNode;
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  full?: boolean;
  style?: ViewStyle;
  textStyle?: TextStyle;
}

export const AppButton: React.FC<AppButtonProps> = ({
  children,
  variant = 'solid',
  size = 'md',
  loading = false,
  full = false,
  disabled,
  style,
  textStyle,
  ...rest
}) => {
  const isDisabled = disabled || loading;

  return (
    <Pressable
      style={({ pressed }) => [
        styles.base,
        styles[variant],
        styles[`size_${size}`],
        full && { width: '100%' },
        isDisabled && styles.disabled,
        pressed && styles.pressed,
        style,
      ]}
      disabled={isDisabled}
      {...rest}
    >
      {loading ? (
        <ActivityIndicator
          color={variant === 'solid' || variant === 'accent' ? Colors.bone : Colors.ink}
          size="small"
        />
      ) : (
        <AppText
          variant="smallCaps"
          style={[styles.text, styles[`text_${variant}`], textStyle]}
        >
          {children}
        </AppText>
      )}
    </Pressable>
  );
};

const styles = StyleSheet.create({
  base: {
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 10,
    flexDirection: 'row',
    gap: 8,
  },
  pressed: { opacity: 0.8, transform: [{ scale: 0.98 }] },
  disabled: { opacity: 0.4 },

  // Variants
  solid: { backgroundColor: Colors.ink },
  outline: { backgroundColor: Colors.transparent, borderWidth: 1, borderColor: Colors.ink },
  accent: { backgroundColor: Colors.accent },
  ghost: { backgroundColor: Colors.transparent },
  bone: { backgroundColor: Colors.bone },
  link: { backgroundColor: Colors.transparent },

  // Sizes
  size_sm: { paddingHorizontal: 14, paddingVertical: 8 },
  size_md: { paddingHorizontal: 22, paddingVertical: 13 },
  size_lg: { paddingHorizontal: 28, paddingVertical: 16 },

  // Text colors
  text: { fontFamily: Fonts.mono, letterSpacing: 1 },
  text_solid: { color: Colors.bone },
  text_outline: { color: Colors.ink },
  text_accent: { color: Colors.bone },
  text_ghost: { color: Colors.muted },
  text_bone: { color: Colors.ink },
  text_link: { color: Colors.accent, textDecorationLine: 'underline' },
});