import { SafeAreaView } from 'react-native-safe-area-context';
import React from 'react';
import { View, ScrollView, StyleSheet, Pressable } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { StackNavigationProp } from '@react-navigation/stack';
import { Colors } from '../constants/colors';
import { AppText } from '../components/ui/AppText';
import { RootStackParamList } from '../types';

type Nav = StackNavigationProp<RootStackParamList>;

export const Welcome: React.FC = () => {
  const nav = useNavigation<Nav>();

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.container}>
        <View style={styles.top}>
          <AppText variant="smallCaps" color={Colors.muted}>Vol. III · Issue 001</AppText>
          <AppText variant="smallCaps" color={Colors.muted}>MMXXVI</AppText>
        </View>

        <View style={styles.middle}>
          <AppText variant="smallCaps" color={Colors.accent} style={{ marginBottom: 22 }}>
            ⟡  A Private Journal For Two
          </AppText>
          <AppText variant="display" size={72} color={Colors.ink} style={{ lineHeight: 68, marginBottom: 24 }}>
            aligned<AppText size={72} color={Colors.accent}>.</AppText>
          </AppText>
          <AppText variant="serifItalic" size={21} color={Colors.ink2} style={{ lineHeight: 32, maxWidth: 320 }}>
            Rituals for two people choosing each other —{' '}
            <AppText variant="serifItalic" size={21} color={Colors.accent}>every day, on purpose.</AppText>
          </AppText>
        </View>

        <View style={styles.bottom}>
          <Pressable style={styles.row} onPress={() => nav.navigate('AlignedOnboarding')}>
            <AppText variant="smallCaps" color={Colors.ink}>Begin</AppText>
            <AppText size={18} color={Colors.accent}>→</AppText>
          </Pressable>
          <Pressable style={styles.row} onPress={() => nav.navigate('AlignedApp')}>
            <AppText variant="smallCaps" color={Colors.muted}>Preview the Edition</AppText>
            <AppText size={18} color={Colors.muted}>◇</AppText>
          </Pressable>
          <AppText variant="mono" color={Colors.light} style={{ textAlign: 'center', fontSize: 10, marginTop: 14 }}>
            SEVEN DAYS COMPLIMENTARY · NO CARD REQUIRED
          </AppText>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Colors.bone },
  container: { flexGrow: 1, padding: 32 },
  top: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 80 },
  middle: { flex: 1, justifyContent: 'center', paddingBottom: 40 },
  bottom: { borderTopWidth: 1, borderTopColor: Colors.rule, paddingTop: 20, gap: 0 },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 18,
    borderBottomWidth: 1,
    borderBottomColor: Colors.rule,
  },
});