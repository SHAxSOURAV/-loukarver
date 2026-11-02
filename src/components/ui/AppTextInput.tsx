import React, { useState } from 'react';
import {
  View,
  TextInput,
  StyleSheet,
  ViewStyle,
  TextInputProps,
  Pressable,
  Platform,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Colors } from '../../constants/colors';
import { Fonts } from '../../constants/fonts';
import { AppText } from './AppText';

interface AppTextInputProps extends TextInputProps {
  label?: string;
  n?: string;
  containerStyle?: ViewStyle;
  multiline?: boolean;
  isPassword?: boolean;
}

export const AppTextInput: React.FC<AppTextInputProps> = ({
  label,
  n,
  containerStyle,
  style,
  multiline = false,
  isPassword = false,
  secureTextEntry,
  ...rest
}) => {
  const [showPassword, setShowPassword] = useState(false);

  const _secureTextEntry = isPassword ? !showPassword : secureTextEntry;

  return (
    <View style={[styles.container, containerStyle]}>
      {label && (
        <View style={styles.labelRow}>
          {n && <AppText variant="mono" style={styles.n}>{n}</AppText>}
          <AppText variant="smallCaps" color={Colors.ink2}>{label}</AppText>
        </View>
      )}
      <View style={styles.inputContainer}>
        <TextInput
          style={[styles.input, multiline && styles.multiline, style, isPassword && { paddingRight: 40 }]}
          placeholderTextColor={'#b3b3b3'}
          multiline={multiline}
          textAlignVertical={multiline ? 'top' : 'center'}
          secureTextEntry={_secureTextEntry}
          {...rest}
        />
        {isPassword && (
          <Pressable 
            style={styles.eyeIcon} 
            onPress={() => setShowPassword(!showPassword)}
          >
            <Ionicons name={showPassword ? 'eye-off' : 'eye'} size={20} color={Colors.ink2} />
          </Pressable>
        )}
      </View>
      <View style={styles.underline} />
    </View>
  );
};

const styles = StyleSheet.create({
  container: { marginBottom: 22 },
  labelRow: { flexDirection: 'row', alignItems: 'baseline', gap: 8, marginBottom: 6 },
  n: { fontSize: 9, color: Colors.light, letterSpacing: 2 },
  inputContainer: {
    position: 'relative',
    justifyContent: 'center',
  },
  input: {
    fontFamily: Fonts.fraunces,
    fontSize: 15,
    ...Platform.select({
      ios: {
        lineHeight: 24,
      },
      android: {
        includeFontPadding: false,
      },
    }),
    color: Colors.ink,
    paddingVertical: 8,
    paddingHorizontal: 0,
  },
  multiline: { minHeight: 80, paddingTop: 8 },
  eyeIcon: {
    position: 'absolute',
    right: 0,
    height: '100%',
    justifyContent: 'center',
    paddingHorizontal: 8,
  },
  underline: { height: 1, backgroundColor: Colors.rule, marginTop: 2 },
});