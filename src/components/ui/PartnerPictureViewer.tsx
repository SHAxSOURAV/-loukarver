import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Modal,
  StyleSheet,
  Pressable,
  DeviceEventEmitter,
  ActivityIndicator,
  Animated,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import ImageViewing from '../thread/ImageViewerWrapper';
import { AppText } from './AppText';
import { Colors } from '../../constants/colors';
import { getFastPartnerPicture } from '../../services/userApi';
import api from '../../services/api';

export interface ShowPartnerPicturePayload {
  context: 'aligned' | 'vibe';
  partnerId?: string;
  fallbackUrl?: string | null;
  name?: string;
}

export const showPartnerPicture = (payload: ShowPartnerPicturePayload) => {
  DeviceEventEmitter.emit('SHOW_PARTNER_PICTURE', payload);
};

export const normalizePartnerImageUrl = (url?: string | null): string | null => {
  if (!url) return null;
  if (url.startsWith('http://') || url.startsWith('https://')) return url;
  const base = api.defaults.baseURL?.replace(/\/api\/v1\/?$/, '') || '';
  const clean = url.replace(/\\/g, '/').replace(/^\//, '');
  return `${base}/${clean}`;
};

export const PartnerPictureViewer: React.FC = () => {
  const insets = useSafeAreaInsets();
  const [visible, setVisible] = useState(false);
  const [pictureUrl, setPictureUrl] = useState<string | null>(null);
  const [partnerName, setPartnerName] = useState<string>('Partner');
  const [context, setContext] = useState<'aligned' | 'vibe'>('aligned');
  const [loading, setLoading] = useState(false);
  const [hasNoPicture, setHasNoPicture] = useState(false);

  const closeViewer = useCallback(() => {
    setVisible(false);
    setHasNoPicture(false);
    setPictureUrl(null);
    setLoading(false);
  }, []);

  useEffect(() => {
    const sub = DeviceEventEmitter.addListener(
      'SHOW_PARTNER_PICTURE',
      async (payload: ShowPartnerPicturePayload) => {
        if (!payload) return;

        const initialUrl = normalizePartnerImageUrl(payload.fallbackUrl);
        const name = payload.name || (payload.context === 'vibe' ? 'Vibe Partner' : 'Aligned Partner');

        setContext(payload.context);
        setPartnerName(name);
        setPictureUrl(initialUrl);
        setVisible(true);
        setHasNoPicture(false);

        // If we don't have an initial URL, show loader while querying API
        if (!initialUrl) {
          setLoading(true);
        }

        try {
          // Parallel super-fast backend call
          const res = await getFastPartnerPicture(payload.context, payload.partnerId || null);
          if (res?.success && res.data) {
            if (res.data.name) {
              setPartnerName(res.data.name);
            }
            if (res.data.picture_url) {
              const freshUrl = normalizePartnerImageUrl(res.data.picture_url);
              setPictureUrl(freshUrl);
              setHasNoPicture(false);
            } else if (!initialUrl) {
              // Both fallback and API confirm no picture set
              setHasNoPicture(true);
            }
          } else if (!initialUrl) {
            setHasNoPicture(true);
          }
        } catch (e) {
          console.log('[PartnerPictureViewer] Error fetching fast partner picture:', e);
          if (!initialUrl) {
            setHasNoPicture(true);
          }
        } finally {
          setLoading(false);
        }
      }
    );

    return () => {
      sub.remove();
    };
  }, []);

  if (!visible) return null;

  const initial = (partnerName || 'P').charAt(0).toUpperCase();
  const isAligned = context === 'aligned';
  const badgeLabel = isAligned ? 'ALIGNED PARTNER' : 'VIBE CONNECTION';
  const badgeBg = isAligned ? 'rgba(196, 77, 77, 0.2)' : 'rgba(46, 125, 50, 0.2)';
  const badgeColor = isAligned ? Colors.accent : '#81c784';

  // 1. Monogram placeholder modal when partner has no picture
  if (hasNoPicture && !pictureUrl) {
    return (
      <Modal
        visible={visible}
        transparent
        animationType="fade"
        onRequestClose={closeViewer}
        statusBarTranslucent
      >
        <Pressable style={styles.backdrop} onPress={closeViewer}>
          <Pressable style={styles.noPicCard} onPress={(e) => e.stopPropagation()}>
            <Pressable style={styles.closeBtnCorner} onPress={closeViewer} hitSlop={15}>
              <Ionicons name="close" size={24} color={Colors.ink} />
            </Pressable>

            <View style={styles.monogramCircle}>
              <AppText variant="heading" size={38} color={Colors.bone}>
                {initial}
              </AppText>
            </View>

            <AppText variant="heading" size={20} color={Colors.ink} style={{ marginTop: 14 }}>
              {partnerName}
            </AppText>

            <View style={[styles.contextBadge, { backgroundColor: badgeBg }]}>
              <AppText variant="mono" size={10} color={badgeColor} style={{ letterSpacing: 1.5 }}>
                {badgeLabel}
              </AppText>
            </View>

            <AppText variant="serifItalic" size={14} color={Colors.muted} style={{ marginTop: 16, textAlign: 'center' }}>
              No profile picture uploaded yet.
            </AppText>

            <Pressable style={styles.dismissBtn} onPress={closeViewer}>
              <AppText variant="smallCaps" size={12} color={Colors.ink}>
                CLOSE
              </AppText>
            </Pressable>
          </Pressable>
        </Pressable>
      </Modal>
    );
  }

  // 2. Loading state when waiting for API and no fallback is yet present
  if (loading && !pictureUrl) {
    return (
      <Modal
        visible={visible}
        transparent
        animationType="fade"
        onRequestClose={closeViewer}
        statusBarTranslucent
      >
        <View style={styles.backdrop}>
          <View style={styles.loadingBox}>
            <ActivityIndicator size="large" color={Colors.accent} />
            <AppText variant="smallCaps" size={11} color={Colors.bone} style={{ marginTop: 12 }}>
              FETCHING PROFILE PICTURE...
            </AppText>
          </View>
        </View>
      </Modal>
    );
  }

  // 3. High-performance native image viewer with pinch-to-zoom and swipe-to-dismiss
  return (
    <ImageViewing
      images={[{ uri: pictureUrl! }]}
      imageIndex={0}
      visible={visible && !!pictureUrl}
      onRequestClose={closeViewer}
      HeaderComponent={() => (
        <View style={[styles.headerContainer, { paddingTop: insets.top + 10 }]}>
          <View style={{ flex: 1 }}>
            <AppText variant="heading" size={18} color="#FFFFFF">
              {partnerName}
            </AppText>
            <View style={[styles.contextBadge, { backgroundColor: badgeBg, alignSelf: 'flex-start', marginTop: 4 }]}>
              <AppText variant="mono" size={9} color={badgeColor} style={{ letterSpacing: 1.2 }}>
                {badgeLabel}
              </AppText>
            </View>
          </View>
          <Pressable onPress={closeViewer} hitSlop={20} style={styles.headerCloseBtn}>
            <Ionicons name="close" size={26} color="#FFFFFF" />
          </Pressable>
        </View>
      )}
    />
  );
};

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.82)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 24,
  },
  loadingBox: {
    backgroundColor: 'rgba(26, 26, 26, 0.9)',
    paddingVertical: 24,
    paddingHorizontal: 32,
    borderRadius: 20,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.1)',
  },
  noPicCard: {
    width: '100%',
    maxWidth: 320,
    backgroundColor: Colors.bone,
    borderRadius: 24,
    padding: 28,
    alignItems: 'center',
    position: 'relative',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.35,
    shadowRadius: 16,
    elevation: 12,
  },
  closeBtnCorner: {
    position: 'absolute',
    top: 16,
    right: 16,
    padding: 4,
  },
  monogramCircle: {
    width: 90,
    height: 90,
    borderRadius: 45,
    backgroundColor: Colors.ink,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 2,
    borderColor: Colors.rule,
  },
  contextBadge: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
    marginTop: 6,
  },
  dismissBtn: {
    marginTop: 22,
    paddingVertical: 10,
    paddingHorizontal: 24,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: Colors.rule,
    backgroundColor: Colors.cream,
  },
  headerContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingBottom: 14,
    backgroundColor: 'rgba(0, 0, 0, 0.55)',
  },
  headerCloseBtn: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: 'rgba(255, 255, 255, 0.15)',
    justifyContent: 'center',
    alignItems: 'center',
    marginLeft: 12,
  },
});
