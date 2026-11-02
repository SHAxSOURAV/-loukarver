import React from 'react';
import { View, Pressable, StyleSheet } from 'react-native';
import { Colors } from '../../constants/colors';
import { AppText } from '../ui/AppText';
import { Track } from '../../types';
import { Config } from '../../constants/config';

interface PlaylistCardProps {
  tracks: Track[];
  onOpen: () => void;
  onAdd: () => void;
}

const MUSIC_META = {
  spotify: { glyph: 'S', color: '#1DB954' },
  apple: { glyph: 'A', color: '#FA243C' },
  youtube: { glyph: 'Y', color: '#FF0000' },
};

export const PlaylistCard: React.FC<PlaylistCardProps> = ({ tracks, onOpen, onAdd }) => (
  <View style={styles.container}>
    <View style={styles.header}>
      <AppText variant="smallCaps" color={Colors.light}>Our Playlist</AppText>
      <AppText variant="mono" color={Colors.light} style={{ fontSize: 10 }}>
        {tracks.length} TRACKS
      </AppText>
    </View>

    <AppText variant="heading" size={30} color={Colors.bone} style={{ marginBottom: 4 }}>
      Songs for{' '}
      <AppText variant="serifItalic" size={30} color={Colors.accent}>us.</AppText>
    </AppText>
    <AppText variant="serifItalic" color={Colors.cream2} style={{ marginBottom: 18, lineHeight: 22 }}>
      Synced across Spotify, Apple Music & YouTube.
    </AppText>

    {tracks.slice(0, 3).map(t => (
      <View key={t.id} style={styles.track}>
        <View style={styles.trackIcon}>
          <AppText size={14} color={Colors.bone}>♪</AppText>
        </View>
        <View style={{ flex: 1 }}>
          <AppText variant="heading" size={14} color={Colors.bone}>{t.title}</AppText>
          <AppText variant="serifItalic" size={12} color={Colors.light}>
            {t.artist} · {Config.DEMO_USERS[t.addedBy].name}
          </AppText>
        </View>
        <View style={{ flexDirection: 'row', gap: 3 }}>
          {t.available.map(s => (
            <View key={s} style={[styles.serviceDot, { backgroundColor: MUSIC_META[s].color }]}>
              <AppText size={8} color={Colors.white} style={{ fontFamily: 'JetBrainsMono-Regular', fontWeight: '600' }}>
                {MUSIC_META[s].glyph}
              </AppText>
            </View>
          ))}
        </View>
      </View>
    ))}

    <View style={styles.actions}>
      <Pressable style={styles.btnPrimary} onPress={onOpen}>
        <AppText variant="smallCaps" color={Colors.ink}>Open playlist</AppText>
      </Pressable>
      <Pressable style={styles.btnAccent} onPress={onAdd}>
        <AppText variant="smallCaps" color={Colors.bone}>+ Add</AppText>
      </Pressable>
    </View>
  </View>
);

const styles = StyleSheet.create({
  container: {
    backgroundColor: Colors.ink,
    padding: 26,
    marginHorizontal: -24,
    paddingHorizontal: 24,
  },
  header: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 6 },
  track: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    backgroundColor: 'rgba(244,238,228,0.06)',
    borderRadius: 10,
    padding: 10,
    marginBottom: 8,
  },
  trackIcon: {
    width: 36, height: 36, borderRadius: 10,
    backgroundColor: Colors.accent,
    alignItems: 'center', justifyContent: 'center',
  },
  serviceDot: {
    width: 18, height: 18, borderRadius: 9,
    alignItems: 'center', justifyContent: 'center',
  },
  actions: { flexDirection: 'row', gap: 8, marginTop: 18 },
  btnPrimary: {
    flex: 1, padding: 12, backgroundColor: Colors.bone,
    borderRadius: 10, alignItems: 'center',
  },
  btnAccent: {
    paddingHorizontal: 16, paddingVertical: 12,
    backgroundColor: Colors.accent, borderRadius: 10, alignItems: 'center',
  },
});