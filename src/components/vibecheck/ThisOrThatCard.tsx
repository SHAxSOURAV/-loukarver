import React from 'react';
import { View, Pressable, StyleSheet } from 'react-native';
import { Colors } from '../../constants/colors';
import { AppText } from '../ui/AppText';
import { ThisOrThatCard as TCard } from '../../types';

interface Props {
  card: TCard;
  myPick: 'a' | 'b' | null;
  theirPick: 'a' | 'b' | null;
  revealed: boolean;
  partnerName: string;
  onPick: (pick: 'a' | 'b') => void;
  allPartnerPicks?: { name: string, pick: 'a' | 'b' }[];
}

export const ThisOrThatCard: React.FC<Props> = ({
  card, myPick, theirPick, revealed, partnerName, onPick, allPartnerPicks
}) => (
  <View style={styles.row}>
    {(['a', 'b'] as const).map(opt => {
      const isMine = myPick === opt;
      const isTheirs = revealed && theirPick === opt;
      const both = isMine && isTheirs;
      
      const picksForThisOpt = allPartnerPicks?.filter(p => p.pick === opt) || [];

      return (
        <Pressable
          key={opt}
          style={[
            styles.option,
            both ? styles.optBoth : isMine ? styles.optMine : isTheirs ? styles.optTheirs : styles.optDefault,
            myPick && !isMine && !isTheirs ? styles.optFaded : undefined,
          ]}
          onPress={() => !myPick && onPick(opt)}
          disabled={!!myPick}
        >
          <AppText
            variant="heading"
            size={22}
            color={both || isMine ? Colors.bone : Colors.ink}
            style={{ textAlign: 'center' }}
          >
            {card[opt]}
          </AppText>
          {revealed && (isMine || picksForThisOpt.length > 0) && (
            <View style={styles.badges}>
              {isMine && (
                <View style={[styles.badge, both ? styles.badgeWhite : styles.badgeAccent]}>
                  <AppText variant="mono" style={{ fontSize: 9 }} color={both ? Colors.accent : Colors.bone}>YOU</AppText>
                </View>
              )}
              {picksForThisOpt.map((p, idx) => (
                <View key={idx} style={both ? styles.badgeWhite : styles.badgeAccent}>
                  <AppText variant="mono" style={{ fontSize: 9 }} color={both ? Colors.accent : Colors.bone}>
                    {p.name.toUpperCase().slice(0, 6)}
                  </AppText>
                </View>
              ))}
            </View>
          )}
        </Pressable>
      );
    })}
  </View>
);

const styles = StyleSheet.create({
  row: { flexDirection: 'row', gap: 12, marginBottom: 24 },
  option: {
    flex: 1, minHeight: 140, borderRadius: 14,
    alignItems: 'center', justifyContent: 'center',
    padding: 16, gap: 14,
  },
  optDefault: { backgroundColor: Colors.cream },
  optMine: { backgroundColor: Colors.ink, borderWidth: 2, borderColor: Colors.ink },
  optTheirs: { backgroundColor: `${Colors.accent}25`, borderWidth: 2, borderColor: Colors.accent },
  optBoth: { backgroundColor: Colors.accent, borderWidth: 2, borderColor: Colors.accent },
  optFaded: { opacity: 0.4 },
  badges: { flexDirection: 'row', gap: 6 },
  badge: { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 99 },
  badgeAccent: { backgroundColor: Colors.accent, paddingHorizontal: 8, paddingVertical: 3, borderRadius: 99 },
  badgeWhite: { backgroundColor: Colors.bone, paddingHorizontal: 8, paddingVertical: 3, borderRadius: 99 },
});