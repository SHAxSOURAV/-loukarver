import React, { useState, useEffect } from 'react';
import { View, StyleSheet, ScrollView, Image, Pressable, Alert, RefreshControl, DeviceEventEmitter } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useNavigation } from '@react-navigation/native';
import { Ionicons } from '@expo/vector-icons';
import { Colors } from '../../constants/colors';
import { AppText } from '../../components/ui/AppText';
import { AppButton } from '../../components/ui/AppButton';
import { getAlignmentRequestStatus, respondAlignmentRequest } from '../../services/userApi';

export const AlignmentRequestsScreen: React.FC = () => {
  const navigation = useNavigation<any>();
  const [requests, setRequests] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [respondingId, setRespondingId] = useState<string | null>(null);

  const fetchRequests = async () => {
    try {
      const res = await getAlignmentRequestStatus();
      if (res && res.data) {
        if (res.data.is_aligned) {
          // Already aligned, go back to main app
          navigation.goBack();
          return;
        }
        const list = res.data.incoming_list || (res.data.incoming ? [res.data.incoming] : []);
        setRequests(list);
      } else {
        setRequests([]);
      }
    } catch (e) {
      console.log("Error fetching alignment requests:", e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchRequests();

    const sub1 = DeviceEventEmitter.addListener('ALIGNMENT_REQUEST_UPDATED', fetchRequests);
    const sub2 = DeviceEventEmitter.addListener('ALIGNMENT_BONDED', () => {
      navigation.goBack();
    });
    const sub3 = DeviceEventEmitter.addListener('REFRESH_ALIGNED_DATA', fetchRequests);

    return () => {
      sub1.remove();
      sub2.remove();
      sub3.remove();
    };
  }, []);

  const handleRespond = async (requestId: string, accept: boolean) => {
    setRespondingId(requestId);
    try {
      const res = await respondAlignmentRequest(requestId, accept);
      if (accept) {
        Alert.alert("Aligned!", "You and your partner are now aligned!");
        DeviceEventEmitter.emit('REFRESH_ALIGNED_DATA');
        navigation.goBack();
      } else {
        Alert.alert("Declined", "Alignment request declined.");
        await fetchRequests();
      }
    } catch (e: any) {
      console.log("Failed to respond to alignment request:", e);
      const msg = e.response?.data?.detail || e.message || "Failed to process response.";
      Alert.alert("Error", msg);
    } finally {
      setRespondingId(null);
    }
  };

  return (
    <SafeAreaView style={styles.safeArea} edges={['top', 'bottom']}>
      {/* Header */}
      <View style={styles.header}>
        <Pressable onPress={() => navigation.goBack()} style={styles.backBtn}>
          <Ionicons name="arrow-back" size={20} color={Colors.accent} />
          <AppText variant="smallCaps" color={Colors.accent} style={{ fontSize: 13, marginLeft: 6 }}>
            BACK
          </AppText>
        </Pressable>
        <AppText variant="mono" color={Colors.muted} style={{ fontSize: 11, letterSpacing: 1.5 }}>
          REQUESTS ({requests.length})
        </AppText>
      </View>

      <ScrollView
        contentContainerStyle={styles.scrollContent}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); fetchRequests(); }} />
        }
      >
        <View style={styles.titleSection}>
          <AppText variant="display" size={28} color={Colors.ink}>
            Alignment Requests
          </AppText>
          <AppText variant="serifItalic" size={14} color={Colors.muted} style={{ marginTop: 6, lineHeight: 20 }}>
            People who want to connect with you. Approving any request will bond your accounts and cancel all other pending requests.
          </AppText>
        </View>

        {loading ? (
          <View style={{ paddingVertical: 40, alignItems: 'center' }}>
            <AppText color={Colors.muted}>Loading requests...</AppText>
          </View>
        ) : requests.length === 0 ? (
          <View style={styles.emptyCard}>
            <Ionicons name="mail-open-outline" size={48} color={Colors.muted} />
            <AppText variant="heading" size={18} color={Colors.ink} style={{ marginTop: 16 }}>
              No Pending Requests
            </AppText>
            <AppText variant="serifItalic" size={14} color={Colors.muted} style={{ textAlign: 'center', marginTop: 8 }}>
              You don't have any incoming alignment requests right now.
            </AppText>
          </View>
        ) : (
          requests.map((req, idx) => (
            <View key={req.id} style={styles.requestCard}>
              <View style={styles.cardHeader}>
                <View style={styles.badge}>
                  <AppText variant="mono" style={{ fontSize: 9, color: Colors.accent, letterSpacing: 1 }}>
                    INCOMING REQUEST {requests.length > 1 ? `(${idx + 1}/${requests.length})` : ''}
                  </AppText>
                </View>
              </View>

              <View style={styles.senderRow}>
                {req.sender_profile_photo ? (
                  <Image source={{ uri: req.sender_profile_photo }} style={styles.avatar} />
                ) : (
                  <View style={[styles.avatar, styles.avatarPlaceholder]}>
                    <AppText variant="display" size={22} color={Colors.accent}>
                      {req.sender_name?.charAt(0)?.toUpperCase() || "P"}
                    </AppText>
                  </View>
                )}
                <View style={{ flex: 1 }}>
                  <AppText variant="heading" size={20} color={Colors.ink}>
                    {req.sender_name}
                  </AppText>
                  <AppText variant="serifItalic" size={13} color={Colors.muted} style={{ marginTop: 2 }}>
                    {req.sender_city ? `${req.sender_city} • ` : ""}wants to align with you
                  </AppText>
                </View>
              </View>

              <AppText variant="serifItalic" size={13} color={Colors.ink2} style={{ lineHeight: 19, marginVertical: 8 }}>
                Accepting will link your accounts, daily rituals, shared maps, and connection pulses.
              </AppText>

              <View style={styles.actionRow}>
                <AppButton
                  variant="outline"
                  size="md"
                  style={{ flex: 1, borderColor: Colors.rule }}
                  textStyle={{ color: Colors.muted }}
                  onPress={() => handleRespond(req.id, false)}
                  disabled={respondingId === req.id}
                >
                  Decline
                </AppButton>
                <AppButton
                  variant="solid"
                  size="md"
                  style={{ flex: 1.6, backgroundColor: Colors.ink }}
                  onPress={() => handleRespond(req.id, true)}
                  disabled={respondingId === req.id}
                >
                  {respondingId === req.id ? "Connecting..." : "Approve & Align →"}
                </AppButton>
              </View>
            </View>
          ))
        )}
      </ScrollView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: Colors.bone,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: Colors.rule,
  },
  backBtn: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  scrollContent: {
    padding: 20,
  },
  titleSection: {
    marginBottom: 24,
  },
  emptyCard: {
    backgroundColor: '#FAF9F6',
    borderRadius: 14,
    borderWidth: 1,
    borderColor: Colors.rule,
    padding: 40,
    alignItems: 'center',
    marginTop: 20,
  },
  requestCard: {
    backgroundColor: '#FAF9F6',
    borderRadius: 14,
    borderWidth: 1,
    borderColor: Colors.rule,
    padding: 18,
    marginBottom: 16,
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  badge: {
    backgroundColor: '#F1E4DA',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
  },
  senderRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
    marginBottom: 10,
  },
  avatar: {
    width: 52,
    height: 52,
    borderRadius: 26,
    borderWidth: 2,
    borderColor: Colors.accent,
  },
  avatarPlaceholder: {
    backgroundColor: Colors.cream,
    alignItems: 'center',
    justifyContent: 'center',
  },
  actionRow: {
    flexDirection: 'row',
    gap: 10,
    marginTop: 12,
  },
});
