import { SafeAreaView } from 'react-native-safe-area-context';
import React, { useEffect } from 'react';
import { View, ScrollView, StyleSheet, Pressable, Alert } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { StackNavigationProp } from '@react-navigation/stack';
import { Colors } from '../../constants/colors';
import { AppText } from '../../components/ui/AppText';
import { RootStackParamList } from '../../types';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { getMe } from '../../services/authApi';

type Nav = StackNavigationProp<RootStackParamList>;

export const VCWelcome: React.FC = () => {
  const nav = useNavigation<Nav>();

  useEffect(() => {
    const checkAlignment = async () => {
      try {
        const token = await AsyncStorage.getItem('access_token');
        if (token) {
          const user = await getMe();
          if (user?.is_aligned || user?.partner) {
            Alert.alert(
              'Access Restricted',
              'You are currently in an aligned relationship. Access to Vibe Check is locked unless your aligned connection is broken.'
            );
            nav.reset({
              index: 0,
              routes: [{ name: 'AlignedApp' }],
            });
          }
        }
      } catch (e) {
        // ignore
      }
    };
    checkAlignment();
  }, [nav]);

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.container}>
        <View style={styles.top}>
          <AppText variant="smallCaps" color={Colors.muted}>vibe check</AppText>
          <Pressable onPress={() => nav.navigate('ModeSelector')}>
            <AppText variant="mono" color={Colors.accent} style={{ fontSize: 10 }}>SWITCH MODE →</AppText>
          </Pressable>
        </View>

        <View style={styles.middle}>
          <AppText variant="smallCaps" color={Colors.accent} style={{ marginBottom: 18 }}>A daily card for two</AppText>
          <AppText variant="display" size={64} style={{ lineHeight: 60, marginBottom: 24 }}>
            vibe{'\n'}check<AppText size={64} color={Colors.accent}>.</AppText>
          </AppText>
          <AppText variant="serifItalic" size={20} color={Colors.ink2} style={{ lineHeight: 30, maxWidth: 320 }}>
            One question. Both pick.{' '}
            <AppText variant="serifItalic" size={20} color={Colors.accent}>See if you match.</AppText>
          </AppText>
        </View>

        {/* Preview card */}
        <View style={styles.previewCard}>
          <AppText variant="smallCaps" color={Colors.muted} style={{ textAlign: 'center', marginBottom: 12 }}>TODAY</AppText>
          <View style={styles.previewRow}>
            <View style={styles.previewOpt}>
              <AppText variant="heading" size={18}>Beach</AppText>
            </View>
            <AppText variant="mono" color={Colors.light} style={{ fontSize: 10 }}>OR</AppText>
            <View style={[styles.previewOpt, styles.previewOptActive]}>
              <AppText variant="heading" size={18}>Mountains</AppText>
            </View>
          </View>
          <AppText variant="serifItalic" size={13} color={Colors.muted} style={{ textAlign: 'center', marginTop: 14 }}>
            5 seconds. Reveals together.
          </AppText>
        </View>

        {/* Actions */}
        <View style={styles.bottom}>
          <Pressable style={styles.row} onPress={() => nav.navigate('VibeOnboarding')}>
            <AppText variant="smallCaps" color={Colors.ink}>Start playing</AppText>
            <AppText size={18} color={Colors.accent}>→</AppText>
          </Pressable>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Colors.bone },
  container: { flexGrow: 1, padding: 32 },
  top: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 80 },
  middle: { flex: 1, justifyContent: 'center', paddingBottom: 32 },
  previewCard: {
    padding: 20, borderRadius: 14, backgroundColor: Colors.bone,
    borderWidth: 1, borderColor: Colors.rule,
    shadowColor: Colors.ink2, shadowOpacity: 0.07, shadowRadius: 12, elevation: 3,
    marginBottom: 28,
  },
  previewRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  previewOpt: { flex: 1, padding: 22, borderRadius: 10, backgroundColor: Colors.cream, alignItems: 'center' },
  previewOptActive: { backgroundColor: `${Colors.accent}20` },
  bottom: { borderTopWidth: 1, borderTopColor: Colors.rule, paddingTop: 18 },
  row: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    paddingVertical: 18, borderBottomWidth: 1, borderBottomColor: Colors.rule,
  },
});