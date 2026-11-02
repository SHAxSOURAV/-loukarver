import React from 'react';
import { Text, TextProps, StyleSheet, TextStyle, Platform } from 'react-native';
import { Fonts } from '../../constants/fonts';
import { Colors } from '../../constants/colors';

type Variant = 'heading' | 'display' | 'serif' | 'serifItalic' | 'mono' | 'smallCaps' | 'body';

interface AppTextProps extends TextProps {
  variant?: Variant;
  color?: string;
  size?: number;
  children: React.ReactNode;
}

export const AppText: React.FC<AppTextProps> = ({
  variant = 'body',
  color = Colors.ink,
  size,
  style,
  children,
  ...rest
}) => {
  const variantStyle = styles[variant] as TextStyle;
  const dynamicLineHeight = size && variantStyle.lineHeight && variantStyle.fontSize
    ? Math.round(size * (variantStyle.lineHeight / variantStyle.fontSize))
    : undefined;

  return (
    <Text
      style={[
        variantStyle,
        { color },
        size ? { fontSize: size, ...(dynamicLineHeight ? { lineHeight: dynamicLineHeight } : {}) } : undefined,
        style,
      ]}
      {...rest}
    >
      {children}
    </Text>
  );
};

const fontPaddingStyle: TextStyle = Platform.OS === 'android' ? { includeFontPadding: false } : {};

const styles = StyleSheet.create({
  heading: {
    fontFamily: Fonts.fraunces,
    fontSize: 32,
    fontWeight: '300',
    letterSpacing: -0.8,
    color: Colors.ink,
    ...fontPaddingStyle,
  },
  display: {
    fontFamily: Fonts.frauncesLight,
    fontSize: 64,
    fontWeight: '200',
    letterSpacing: -2,
    lineHeight: 64,
    color: Colors.ink,
    ...fontPaddingStyle,
  },
  serif: {
    fontFamily: Fonts.instrumentSerif,
    fontSize: 16,
    color: Colors.ink,
    ...fontPaddingStyle,
  },
  serifItalic: {
    fontFamily: Fonts.instrumentSerifItalic,
    fontSize: 16,
    color: Colors.ink,
    ...fontPaddingStyle,
  },
  mono: {
    fontFamily: Fonts.mono,
    fontSize: 11,
    color: Colors.muted,
    ...fontPaddingStyle,
  },
  smallCaps: {
    fontFamily: Fonts.mono,
    fontSize: 10,
    lineHeight: 14,
    letterSpacing: 1.4,
    textTransform: 'uppercase',
    color: Colors.muted,
    ...fontPaddingStyle,
  },
  body: {
    fontFamily: Fonts.instrumentSerif,
    fontSize: 15,
    lineHeight: 22,
    color: Colors.ink2,
    ...fontPaddingStyle,
  },
});