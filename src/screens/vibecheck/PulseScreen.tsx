import React, { useState, useEffect } from 'react';
import { View, ScrollView, StyleSheet, Pressable, Alert, DeviceEventEmitter } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useNavigation } from '@react-navigation/native';
import { Colors } from '../../constants/colors';
import { AppText } from '../../components/ui/AppText';
import { AppButton } from '../../components/ui/AppButton';
import { AppTextInput } from '../../components/ui/AppTextInput';
import { BottomSheet } from '../../components/ui/BottomSheet';
import { LadderRow } from '../../components/vibecheck/LadderRow';
import SamVibeNav from '@/components/ui/SamVibeNav';
import { VibeRefreshControl } from '../../components/ui/VibeRefreshControl';
import { getVibeProfile } from '../../services/vibeCheckApi';
import { setVibePulse, getVibePulseStatus, getPulseAnalytics, getMyFlags, createFlag, checkAlignedConnection, updateFlag, deleteFlag, getPartnerFlags, breakAlignment } from '../../services/vibePulseApi';
import { pokePartner, getInteractions } from '../../services/interactionsApi';
import * as Haptics from 'expo-haptics';

const LADDER = [
  { l: 'Talking', sub: 'Texting, flirting — no dates yet' },
  { l: 'Dating', sub: 'Going on dates, still seeing other people' },
  { l: 'Seeing where it goes', sub: 'Real connection, no labels yet' },
  { l: 'Working toward us', sub: 'Active conversations about where this is heading' },
  { l: 'Exclusive', sub: 'Not seeing anyone else' },
  { l: 'FWB', sub: 'Physical intimacy, no long-term labels' },
  { l: 'Serious', sub: 'Met friends and family, planning longer-term' },
  { l: 'Aligned', sub: 'Defining as a couple — ready for the next phase' },
];

const getStageIndex = (statusStr: string) => {
  const mapping: Record<string, number> = {
    Talking: 0, Dating: 1, Seeing: 2, Working: 3, Exclusive: 4, FWB: 5, Serious: 6, Aligned: 7,
  };
  return mapping[statusStr] ?? -1;
};

const getStageStatus = (index: number) => {
  const statuses = ['Talking', 'Dating', 'Seeing', 'Working', 'Exclusive', 'FWB', 'Serious', 'Aligned'];
  return statuses[index] || 'None';
};

export const PulseScreen: React.FC = () => {
  const navigation = useNavigation<any>();
  const [section, setSection] = useState<'overview' | 'ladder' | 'patterns' | 'flags'>('overview');
  const [partnerFlags, setPartnerFlags] = useState<any[]>([]);
  const [flagTab, setFlagTab] = useState<'mine' | 'partner'>('mine');
  const [partnerId, setPartnerId] = useState<string | null>(null);
  
  // SamVibeNav will fire onPartnerChange on mount if there are active connections
  // which will set partnerId and trigger the loadPulseData effect.
  const [partnerName, setPartnerName] = useState('Partner');
  
  const [myStage, setMyStage] = useState<number>(-1);
  const [theirStage, setTheirStage] = useState<number>(-1);
  const [isAligned, setIsAligned] = useState(false);
  const [alignedMessage, setAlignedMessage] = useState('');
  
  const [breakAlignSheet, setBreakAlignSheet] = useState(false);
  const [breakPassword, setBreakPassword] = useState('');
  const [isBreaking, setIsBreaking] = useState(false);
  
  const [analytics, setAnalytics] = useState<any>(null);
  const [flags, setFlags] = useState<any[]>([]);

  const [thinkingSent, setThinkingSent] = useState(false);
  const [interactionStats, setInteractionStats] = useState<any>(null);
  const [isPoking, setIsPoking] = useState(false);

  const [newFlagSheet, setNewFlagSheet] = useState(false);
  const [newFlagText, setNewFlagText] = useState('');
  const [newFlagColor, setNewFlagColor] = useState<'Green' | 'Yellow' | 'Red'>('Green');
  const [newFlagType, setNewFlagType] = useState<'private' | 'public'>('private');
  const [submittingFlag, setSubmittingFlag] = useState(false);

  const [refreshing, setRefreshing] = useState(false);
  const onRefresh = React.useCallback(async () => {
    setRefreshing(true);
    if (partnerId) {
      await loadPulseData(partnerId);
    }
    setRefreshing(false);
  }, [partnerId]);

  const [confirmAlignedSheet, setConfirmAlignedSheet] = useState(false);
  const [alignedTargetIndex, setAlignedTargetIndex] = useState(-1);

  const [editFlagSheet, setEditFlagSheet] = useState(false);
  const [selectedFlag, setSelectedFlag] = useState<any>(null);
  const [editFlagText, setEditFlagText] = useState('');
  const [editFlagColor, setEditFlagColor] = useState<'Green' | 'Yellow' | 'Red'>('Green');
  const [updatingFlag, setUpdatingFlag] = useState(false);
  const [deletingFlag, setDeletingFlag] = useState(false);

  // Removed getVibeProfile useEffect because SamVibeNav handles initial fetch and fires onPartnerChange

  const loadPulseData = async (pid: string) => {
    // Clear previous data
    setMyStage(-1);
    setTheirStage(-1);
    setIsAligned(false);
    setAlignedMessage('');
    setAnalytics({
      partner_id: '', partner_name: '', overall_match_percentage: 0,
      total_cards_played: 0, total_matches: 0, timeline: [], by_depth: [], by_category: [],
      key_agreements: [], key_disagreements: [], strongest_category: null, divergent_category: null
    });
    setFlags([]);
    setPartnerFlags([]);

    try {
      const pulseRes = await getVibePulseStatus(pid);
      if (pulseRes) {
        setMyStage(getStageIndex(pulseRes.my_status));
        setTheirStage(getStageIndex(pulseRes.partner_status));
        if (pulseRes.partner_name) {
          setPartnerName(pulseRes.partner_name);
        }
      }
    } catch (e) {
      setMyStage(-1);
      setTheirStage(-1);
    }
    
    try {
      const alignRes = await checkAlignedConnection(pid);
      if (alignRes.success) {
         setIsAligned(alignRes.is_aligned);
         setAlignedMessage(alignRes.message);
         if (alignRes.is_aligned) {
           Alert.alert(
             'Mutually Aligned! 🎉',
             `You and ${partnerName} are now officially Aligned! Access to Vibe Check is locked while aligned. Transitioning to Aligned...`,
             [{ text: 'Go to Aligned', onPress: () => navigation.navigate('AlignedApp' as any) }]
           );
           return;
         }
      }
    } catch (e) {}
    
    try {
      const analyticsRes = await getPulseAnalytics(pid);
      if (analyticsRes.success) setAnalytics(analyticsRes.data);
    } catch (e) {}

    try {
      const flagsRes = await getMyFlags(pid);
      if (flagsRes.success) setFlags(flagsRes.data);
    } catch (e) {}

    try {
      const pFlagsRes = await getPartnerFlags(pid);
      if (pFlagsRes.success) setPartnerFlags(pFlagsRes.data);
    } catch (e) {}

    try {
      const intRes = await getInteractions("UTC", pid);
      if (intRes?.success) setInteractionStats(intRes.data);
    } catch (e) {}
  };

  useEffect(() => {
    if (partnerId) {
      loadPulseData(partnerId);
    }
  }, [partnerId]);

  // Auto-refresh when a FLAG_CREATED WebSocket event arrives via SamVibeNav
  useEffect(() => {
    const sub = DeviceEventEmitter.addListener('REFRESH_VIBE_DATA', () => {
      if (partnerId) loadPulseData(partnerId);
    });
    return () => sub.remove();
  }, [partnerId]);

  const handleConfirmAligned = async () => {
    if (!partnerId || alignedTargetIndex === -1) return;
    setConfirmAlignedSheet(false);
    try {
      await setVibePulse(partnerId, getStageStatus(alignedTargetIndex));
      const alignRes = await checkAlignedConnection(partnerId);
      if (alignRes.success && alignRes.is_aligned) {
        setIsAligned(true);
        Alert.alert(
          'Mutually Aligned! 🎉',
          `You and ${partnerName} are now officially Aligned! Access to Vibe Check is locked while aligned. Transitioning to Aligned...`,
          [{ text: 'Go to Aligned', onPress: () => navigation.navigate('AlignedApp' as any) }]
        );
        return;
      }
      loadPulseData(partnerId);
    } catch (e: any) {
      const msg = e?.response?.data?.detail || 'Could not save your stage.';
      Alert.alert('Error', msg);
    }
  };

  const handleBreakAlignment = async () => {
    if (!breakPassword) {
      Alert.alert('Error', 'Please enter your password.');
      return;
    }
    setIsBreaking(true);
    try {
      await breakAlignment(breakPassword);
      setBreakAlignSheet(false);
      setBreakPassword('');
      // Optimistically update our stage to Serious
      setMyStage(LADDER.length - 2); 
      if (partnerId) loadPulseData(partnerId);
    } catch (e: any) {
      const msg = e?.response?.data?.detail || 'Could not break alignment. Please check your password.';
      Alert.alert('Error', msg);
    } finally {
      setIsBreaking(false);
    }
  };

  const handlePoke = async () => {
    if (!partnerId) {
      Alert.alert("Connection Required", "Please connect with a partner first to send a silent ping.");
      return;
    }
    if (thinkingSent || isPoking) return;
    setIsPoking(true);
    try {
      await pokePartner(partnerId);
      try {
        Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium).catch(() => {});
      } catch (_) {}
      setThinkingSent(true);
      const res = await getInteractions("UTC", partnerId).catch(() => null);
      if (res?.success) setInteractionStats(res.data);
      setTimeout(() => setThinkingSent(false), 3000);
    } catch (e: any) {
      const msg = e?.response?.data?.detail || "Could not send ping to partner.";
      Alert.alert("Notice", msg);
    } finally {
      setIsPoking(false);
    }
  };

  const handleLadderPress = async (index: number) => {
    if (!partnerId) {
      Alert.alert('Error', 'No active partner found.');
      return;
    }

    // Aligned confirmation gate (last step)
    if (index === LADDER.length - 1) {
      setAlignedTargetIndex(index);
      setConfirmAlignedSheet(true);
      return;
    }

    // Break alignment gate (stepping down from Aligned to lower stage)
    if (myStage === LADDER.length - 1 && index < LADDER.length - 1 && isAligned) {
      setBreakAlignSheet(true);
      return;
    }

    // Free stage selection on the ladder
    try {
      await setVibePulse(partnerId, getStageStatus(index));
      loadPulseData(partnerId);
    } catch (e: any) {
      const msg = e?.response?.data?.detail || 'Could not save your stage.';
      Alert.alert('Error', msg);
    }
  };

  const handleCreateFlag = async () => {
    if (!newFlagText.trim() || !partnerId) return;
    setSubmittingFlag(true);
    try {
      await createFlag(partnerId, newFlagColor, newFlagType, newFlagText.trim());
      setNewFlagText('');
      setNewFlagSheet(false);
      loadPulseData(partnerId);
    } catch (e) {
       Alert.alert('Error', 'Could not save flag.');
    } finally {
      setSubmittingFlag(false);
    }
  };

  const handleUpdateFlag = async () => {
    if (!selectedFlag || !editFlagText.trim()) return;
    setUpdatingFlag(true);
    try {
      await updateFlag(selectedFlag.id, { category: editFlagColor, text: editFlagText.trim() });
      setEditFlagSheet(false);
      if (partnerId) loadPulseData(partnerId);
    } catch (e) {
      Alert.alert('Error', 'Could not update flag.');
    } finally {
      setUpdatingFlag(false);
    }
  };

  const handleDeleteFlag = async () => {
    if (!selectedFlag) return;
    Alert.alert(
      "Delete Flag",
      "Are you sure you want to delete this flag?",
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Delete",
          style: "destructive",
          onPress: async () => {
            setDeletingFlag(true);
            try {
              await deleteFlag(selectedFlag.id);
              setEditFlagSheet(false);
              if (partnerId) loadPulseData(partnerId);
            } catch (e) {
              Alert.alert('Error', 'Could not delete flag.');
            } finally {
              setDeletingFlag(false);
            }
          }
        }
      ]
    );
  };

  const openEditSheet = (flag: any) => {
    setSelectedFlag(flag);
    setEditFlagText(flag.text);
    setEditFlagColor(flag.category as any);
    setEditFlagSheet(true);
  };

  const ladderGap = (myStage !== -1 && theirStage !== -1) ? Math.abs(myStage - theirStage) : -1;
  const isSameStep = ladderGap === 0;

  const greenCount = flags.filter(f => f.category === 'Green').length;
  const yellowCount = flags.filter(f => f.category === 'Yellow').length;
  const redCount = flags.filter(f => f.category === 'Red').length;

  const getFlagColorHex = (cat: string) => {
    if (cat === 'Green') return Colors.sage;
    if (cat === 'Yellow') return '#D4A574';
    return Colors.accent;
  };

  // ==================== LADDER FULL SCREEN ====================
  if (section === 'ladder') {
    return (
      <SafeAreaView style={styles.safe}>
        <VibeRefreshControl refreshing={refreshing} onRefresh={onRefresh} iconMark="✦" showsVerticalScrollIndicator={false}>
          <View style={styles.inner}>
            <Pressable onPress={() => setSection('overview')} style={{ marginBottom: 16 }}>
              <AppText variant="mono" color={Colors.accent} style={{ fontSize: 10 }}>← BACK TO PULSE</AppText>
            </Pressable>

            <AppText variant="display" size={36} style={{ lineHeight: 36, marginBottom: 6 }}>
              The ladder<AppText size={36} color={Colors.accent}>.</AppText>
            </AppText>
            <AppText variant="serifItalic" size={15} color={Colors.muted} style={{ lineHeight: 22, marginBottom: 24 }}>
              Where do you each think you are? Tap to mark your stage.
            </AppText>

            {isAligned ? (
              <View style={[styles.statusCard, { backgroundColor: '#1C1C1E', borderColor: '#333' }]}>
                <AppText variant="smallCaps" color={Colors.sage} style={{ marginBottom: 6 }}>● FULLY ALIGNED</AppText>
                <AppText variant="display" size={24} color={Colors.bone}>
                  Congratulations.
                </AppText>
                <AppText variant="serifItalic" size={15} color="#ccc" style={{ marginTop: 4, lineHeight: 22 }}>
                  {alignedMessage || 'You and your partner have both marked yourselves as aligned!'}
                </AppText>
              </View>
            ) : theirStage === -1 ? (
              <View style={[styles.statusCard, { backgroundColor: `${Colors.bone}`, borderColor: Colors.rule }]}>
                <AppText variant="smallCaps" color={Colors.muted} style={{ marginBottom: 6 }}>⏳ WAITING</AppText>
                <AppText variant="serifItalic" size={14} color={Colors.muted} style={{ lineHeight: 22 }}>
                  {partnerName} hasn't started their ladder yet. Your positions are private.
                </AppText>
              </View>
            ) : isSameStep ? (
              <View style={[styles.statusCard, { backgroundColor: `${Colors.sage}12`, borderColor: `${Colors.sage}30` }]}>
                <AppText variant="smallCaps" color={Colors.sage} style={{ marginBottom: 6 }}>● IN SYNC</AppText>
                <AppText variant="serifItalic" size={14} color={Colors.muted} style={{ lineHeight: 22 }}>
                  You're both on the same step. That's a good sign.
                </AppText>
              </View>
            ) : ladderGap > 0 ? (
              <View style={[styles.statusCard, { backgroundColor: `${Colors.accent}10`, borderColor: `${Colors.accent}30` }]}>
                <AppText variant="smallCaps" color={Colors.accent} style={{ marginBottom: 6 }}>
                  {ladderGap} step{ladderGap > 1 ? 's' : ''} apart
                </AppText>
                <AppText variant="serifItalic" size={14} color={Colors.muted} style={{ lineHeight: 22 }}>
                  The gap isn't bad — it's information.
                </AppText>
              </View>
            ) : null}

            {LADDER.map((stage, i) => (
              <LadderRow
                key={i}
                stage={stage}
                index={i}
                isLast={i === LADDER.length - 1}
                isMine={i === myStage}
                disabled={false}
                showPartnerBadge={isAligned && i === LADDER.length - 1}
                partnerName={partnerName}
                onPress={() => handleLadderPress(i)}
              />
            ))}

            <View style={{ height: 80 }} />
          </View>
        </VibeRefreshControl>

        {/* Aligned Confirmation Sheet */}
        <BottomSheet
          open={confirmAlignedSheet}
          onClose={() => setConfirmAlignedSheet(false)}
          kicker="COMMITMENT"
          title="Confirm Alignment"
        >
          <View>
            <AppText variant="serifItalic" size={16} color={Colors.muted} style={{ lineHeight: 24, marginBottom: 24 }}>
              This will mark you as Aligned with {partnerName}. When both partners select Aligned, you become each other's committed partner. You can only have one. Continue?
            </AppText>
            <View style={{ gap: 12 }}>
              <AppButton variant="solid" size="lg" onPress={handleConfirmAligned}>
                CONFIRM ALIGNMENT
              </AppButton>
              <AppButton variant="outline" size="lg" onPress={() => setConfirmAlignedSheet(false)} style={{ borderColor: Colors.rule }} textStyle={{ color: Colors.ink }}>
                CANCEL
              </AppButton>
            </View>
          </View>
        </BottomSheet>

        {/* Break Alignment Password Sheet */}
        <BottomSheet
          open={breakAlignSheet}
          onClose={() => setBreakAlignSheet(false)}
          kicker="DANGER"
          title="Break Alignment"
        >
          <View>
            <AppText variant="serifItalic" size={16} color={Colors.muted} style={{ lineHeight: 24, marginBottom: 24 }}>
              Stepping down from Aligned will officially break your alignment with {partnerName}. This action requires your password.
            </AppText>
            <AppTextInput
              placeholder="Enter your password"
              value={breakPassword}
              onChangeText={setBreakPassword}
              isPassword
              style={{ marginBottom: 24 }}
            />
            <View style={{ gap: 12 }}>
              <AppButton variant="solid" size="lg" onPress={handleBreakAlignment} loading={isBreaking}>
                CONFIRM BREAKUP
              </AppButton>
              <AppButton variant="outline" size="lg" onPress={() => setBreakAlignSheet(false)} style={{ borderColor: Colors.rule }} textStyle={{ color: Colors.ink }}>
                CANCEL
              </AppButton>
            </View>
          </View>
        </BottomSheet>
      </SafeAreaView>
    );
  }

  // ==================== PATTERNS FULL SCREEN ====================
  if (section === 'patterns') {
    return (
      <SafeAreaView style={styles.safe}>
        <VibeRefreshControl refreshing={refreshing} onRefresh={onRefresh} iconMark="✦" showsVerticalScrollIndicator={false}>
          <View style={styles.inner}>
            <Pressable onPress={() => setSection('overview')} style={{ marginBottom: 16 }}>
              <AppText variant="mono" color={Colors.accent} style={{ fontSize: 10 }}>← BACK TO PULSE</AppText>
            </Pressable>

            <AppText variant="display" size={36} style={{ lineHeight: 36, marginBottom: 6 }}>
              Patterns<AppText size={36} color={Colors.accent}>.</AppText>
            </AppText>
            <AppText variant="serifItalic" size={15} color={Colors.muted} style={{ lineHeight: 22, marginBottom: 24 }}>
              What the cards are saying about your alignment.
            </AppText>

            {/* Overall Match Ring / Header */}
            <View style={[styles.statusCard, { backgroundColor: '#1C1C1E', borderColor: '#333', alignItems: 'center', paddingVertical: 32 }]}>
              <AppText variant="mono" color={Colors.sage} style={{ marginBottom: 8 }}>OVERALL SYNC</AppText>
              <AppText variant="display" size={56} color={Colors.bone}>
                {analytics?.overall_match_percentage ?? 0}%
              </AppText>
              <AppText variant="serifItalic" size={14} color="#ccc" style={{ marginTop: 8 }}>
                {analytics?.total_matches ?? 0} matches out of {analytics?.total_cards_played ?? 0} cards played.
              </AppText>
            </View>

            {/* Timeline View */}
            <View style={{ marginBottom: 32 }}>
              <AppText variant="smallCaps" color={Colors.ink2} style={{ marginBottom: 12 }}>TIMELINE</AppText>
              {analytics?.timeline?.length > 0 ? (
                <View style={{ gap: 8 }}>
                  {analytics.timeline.map((entry: any, i: number) => (
                    <View key={i} style={styles.progressRow1}>
                      <View style={styles.progressRow}>
                        <AppText variant="heading" size={16} style={{ flex: 1 }}>Day {entry.day}</AppText>
                        <AppText variant="mono" color={Colors.muted}>{entry.matches}/{entry.total}</AppText>
                      </View>
                      <View style={styles.progressBarContainer}>
                        <View style={[styles.progressBar, { width: `${entry.match_percentage}%` }]} />
                      </View>
                    </View>
                  ))}
                </View>
              ) : (
                <AppText variant="serifItalic" color={Colors.muted}>No timeline data yet.</AppText>
              )}
            </View>

            {/* Depth View */}
            <View style={{ marginBottom: 32 }}>
              <AppText variant="smallCaps" color={Colors.ink2} style={{ marginBottom: 12 }}>ALIGNMENT BY DEPTH</AppText>
              {analytics?.by_depth?.length > 0 ? (
                <View style={{ flexDirection: 'row', gap: 12 }}>
                  {analytics.by_depth.map((depth: any, i: number) => (
                    <View key={i} style={styles.statBox}>
                      <AppText variant="smallCaps" color={Colors.ink2}>{depth.depth}</AppText>
                      <AppText variant="display" size={24} style={{ marginTop: 8 }}>{depth.match_percentage}%</AppText>
                      <AppText variant="mono" color={Colors.muted} style={{ marginTop: 4, fontSize: 10 }}>{depth.matches}/{depth.total}</AppText>
                    </View>
                  ))}
                </View>
              ) : (
                <AppText variant="serifItalic" color={Colors.muted}>No depth data yet.</AppText>
              )}
            </View>

            {/* Category Clusters */}
            <View style={{ marginBottom: 32 }}>
              <AppText variant="smallCaps" color={Colors.ink2} style={{ marginBottom: 12 }}>BY CATEGORY</AppText>
              {analytics?.by_category?.length > 0 ? (
                <View style={{ gap: 8 }}>
                  {analytics.by_category.map((cat: any, i: number) => (
                    <View key={i} style={[styles.progressRow1, { backgroundColor: '#F8F6F0' }]}>
                      <View style={styles.progressRow}>
                        <AppText variant="heading" size={16} style={{ flex: 1 }}>{cat.category}</AppText>
                        <AppText variant="mono" color={Colors.muted}>{cat.matched_questions}/{cat.total_questions}</AppText>
                      </View>
                      <View style={styles.progressBarContainer}>
                        <View style={[styles.progressBar, { width: `${cat.match_percentage}%` }]} />
                      </View>
                    </View>
                  ))}
                </View>
              ) : (
                <AppText variant="serifItalic" color={Colors.muted}>No category data yet.</AppText>
              )}
            </View>

            {/* Key Cards Highlight */}
            <View style={{ marginBottom: 32 }}>
              <AppText variant="smallCaps" color={Colors.sage} style={{ marginBottom: 12 }}>KEY AGREEMENTS</AppText>
              {analytics?.key_agreements?.length > 0 ? (
                analytics.key_agreements.map((match: any, i: number) => (
                  <View key={i} style={styles.matchCard}>
                    <AppText variant="mono" color={Colors.muted} style={{ marginBottom: 4, fontSize: 10 }}>{match.date.toUpperCase()} • {match.category.toUpperCase()}</AppText>
                    <AppText variant="serifItalic" size={15} style={{ marginBottom: 8 }}>{match.question}</AppText>
                    <View style={{ backgroundColor: '#E9E5D9', padding: 8, borderRadius: 6, alignSelf: 'flex-start' }}>
                      <AppText variant="mono" color={Colors.sage}>YOU BOTH CHOSE: {match.user_answer}</AppText>
                    </View>
                  </View>
                ))
              ) : (
                <AppText variant="serifItalic" color={Colors.muted}>No major agreements yet.</AppText>
              )}

              <View style={{ height: 24 }} />

              <AppText variant="smallCaps" color={Colors.accent} style={{ marginBottom: 12 }}>WHERE YOU DIFFERED</AppText>
              {analytics?.key_disagreements?.length > 0 ? (
                analytics.key_disagreements.map((diff: any, i: number) => (
                  <View key={i} style={[styles.matchCard, { backgroundColor: '#FDECEB', borderColor: '#F5C6C3' }]}>
                    <AppText variant="mono" color={Colors.muted} style={{ marginBottom: 4, fontSize: 10 }}>{diff.date.toUpperCase()} • {diff.category.toUpperCase()}</AppText>
                    <AppText variant="serifItalic" size={15} style={{ marginBottom: 8 }}>{diff.question}</AppText>
                    
                    <View style={{ gap: 4 }}>
                      <AppText variant="mono" color={Colors.ink} style={{ fontSize: 11 }}>{diff.user_name.toUpperCase()} CHOSE: {diff.user_answer}</AppText>
                      <AppText variant="mono" color={Colors.ink} style={{ fontSize: 11 }}>{diff.partner_name.toUpperCase()} CHOSE: {diff.partner_answer}</AppText>
                    </View>
                  </View>
                ))
              ) : (
                <AppText variant="serifItalic" color={Colors.muted}>No major differences yet.</AppText>
              )}
            </View>

            <View style={{ height: 80 }} />
          </View>
        </VibeRefreshControl>
      </SafeAreaView>
    );
  }

  // ==================== FLAGS FULL SCREEN ====================
  if (section === 'flags') {
    const activeFlags = flagTab === 'mine' ? [...flags] : [...partnerFlags];
    activeFlags.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

    return (
      <SafeAreaView style={styles.safe}>
        <VibeRefreshControl refreshing={refreshing} onRefresh={onRefresh} iconMark="✦" showsVerticalScrollIndicator={false}>
          <View style={styles.inner}>
            <Pressable onPress={() => setSection('overview')} style={{ marginBottom: 16 }}>
              <AppText variant="mono" color={Colors.accent} style={{ fontSize: 10 }}>← BACK TO PULSE</AppText>
            </Pressable>

            <AppText variant="display" size={36} style={{ lineHeight: 36, marginBottom: 6 }}>
              Flags<AppText size={36} color={Colors.accent}>.</AppText>
            </AppText>
            <AppText variant="serifItalic" size={15} color={Colors.muted} style={{ lineHeight: 22, marginBottom: 24 }}>
              Track moments that feel right and wrong.
            </AppText>

            {/* Segmented Control */}
            <View style={{ flexDirection: 'row', backgroundColor: '#E9E5D9', borderRadius: 10, padding: 4, marginBottom: 24 }}>
              <Pressable 
                onPress={() => setFlagTab('mine')}
                style={{ flex: 1, paddingVertical: 12, alignItems: 'center', borderRadius: 8, backgroundColor: flagTab === 'mine' ? Colors.ink : 'transparent' }}
              >
                <AppText variant="smallCaps" color={flagTab === 'mine' ? Colors.bone : Colors.muted}>My Notes</AppText>
              </Pressable>
              <Pressable 
                onPress={() => setFlagTab('partner')}
                style={{ flex: 1, paddingVertical: 12, alignItems: 'center', borderRadius: 8, backgroundColor: flagTab === 'partner' ? Colors.ink : 'transparent' }}
              >
                <AppText variant="smallCaps" color={flagTab === 'partner' ? Colors.bone : Colors.muted}>Partner's Flags</AppText>
              </Pressable>
            </View>

            {flagTab === 'mine' && (
              <AppButton variant="solid" size="lg" onPress={() => setNewFlagSheet(true)} style={{ marginBottom: 24 }}>
                 LOG A NEW FLAG
              </AppButton>
            )}
            
            {flagTab === 'partner' && (
              <AppText variant="serifItalic" size={14} color={Colors.muted} style={{ marginBottom: 24 }}>
                These are public flags your partner has shared about you. You cannot edit these.
              </AppText>
            )}

            {activeFlags.length === 0 ? (
               <AppText variant="serifItalic" color={Colors.muted}>
                 {flagTab === 'mine' ? 'You have not logged any flags yet.' : 'Your partner has not shared any public flags.'}
               </AppText>
            ) : (
              <View style={{ gap: 12 }}>
                {activeFlags.map((log: any, i: number) => (
                  <Pressable 
                    key={i} 
                    onPress={() => flagTab === 'mine' ? openEditSheet(log) : null} 
                    style={[styles.logEntry, { backgroundColor: Colors.bone }]}
                  >
                    <View style={[styles.logDot, { backgroundColor: getFlagColorHex(log.category) }]} />
                    <View style={{ flex: 1 }}>
                      <AppText variant="serifItalic" size={15}>"{log.text}"</AppText>
                      <AppText variant="mono" color={Colors.muted} style={{ fontSize: 11, marginTop: 4 }}>
                        {new Date(log.created_at).toLocaleDateString()} • {log.category.toUpperCase()} • {log.type.toUpperCase()}
                      </AppText>
                    </View>
                  </Pressable>
                ))}
              </View>
            )}

            <View style={{ height: 80 }} />
          </View>
        </VibeRefreshControl>

      {/* New Flag Sheet */}
      <BottomSheet
        open={newFlagSheet}
        onClose={() => setNewFlagSheet(false)}
        kicker="NEW LOG"
        title="Log a moment"
      >
         <View>
            <AppText variant="serifItalic" size={14} color={Colors.muted} style={{ marginBottom: 20 }}>
               Track moments that matter. Private notes are only for you. Public flags are shared with your partner.
            </AppText>

            <View style={{ flexDirection: 'row', backgroundColor: '#E9E5D9', borderRadius: 10, padding: 4, marginBottom: 24 }}>
              <Pressable 
                onPress={() => setNewFlagType('private')}
                style={{ flex: 1, paddingVertical: 12, alignItems: 'center', borderRadius: 8, backgroundColor: newFlagType === 'private' ? Colors.ink : 'transparent' }}
              >
                <AppText variant="smallCaps" color={newFlagType === 'private' ? Colors.bone : Colors.muted}>PRIVATE</AppText>
              </Pressable>
              <Pressable 
                onPress={() => setNewFlagType('public')}
                style={{ flex: 1, paddingVertical: 12, alignItems: 'center', borderRadius: 8, backgroundColor: newFlagType === 'public' ? Colors.ink : 'transparent' }}
              >
                <AppText variant="smallCaps" color={newFlagType === 'public' ? Colors.bone : Colors.muted}>PUBLIC</AppText>
              </Pressable>
            </View>

            <View style={{ flexDirection: 'row', gap: 10, marginBottom: 20 }}>
               {['Green', 'Yellow', 'Red'].map((c) => (
                 <Pressable 
                   key={c}
                   onPress={() => setNewFlagColor(c as any)}
                   style={[styles.colorPicker, newFlagColor === c && { borderColor: getFlagColorHex(c), backgroundColor: getFlagColorHex(c) + '1A' }]}
                 >
                    <View style={[styles.logDot, { backgroundColor: getFlagColorHex(c), marginTop: 0, marginBottom: 8 }]} />
                    <AppText variant="smallCaps">{c}</AppText>
                 </Pressable>
               ))}
            </View>

            <AppTextInput 
               n="01"
               label="What happened?"
               value={newFlagText}
               onChangeText={setNewFlagText}
               placeholder="They remembered my favorite coffee..."
            />

            <AppButton 
              variant="solid" 
              size="lg" 
              disabled={submittingFlag || !newFlagText.trim()}
              onPress={handleCreateFlag}
              style={{ marginTop: 24 }}
            >
               {submittingFlag ? 'SAVING...' : 'SAVE MOMENT'}
            </AppButton>
         </View>
      </BottomSheet>

      {/* Edit/Delete Flag Sheet */}
      <BottomSheet
        open={editFlagSheet}
        onClose={() => setEditFlagSheet(false)}
        kicker="EDIT LOG"
        title="Update or delete note"
      >
         <View>
            <View style={{ flexDirection: 'row', gap: 10, marginBottom: 20 }}>
               {['Green', 'Yellow', 'Red'].map((c) => (
                 <Pressable 
                   key={c}
                   onPress={() => setEditFlagColor(c as any)}
                   style={[styles.colorPicker, editFlagColor === c && { borderColor: getFlagColorHex(c), backgroundColor: getFlagColorHex(c) + '1A' }]}
                 >
                    <View style={[styles.logDot, { backgroundColor: getFlagColorHex(c), marginTop: 0, marginBottom: 8 }]} />
                    <AppText variant="smallCaps">{c}</AppText>
                 </Pressable>
               ))}
            </View>

            <AppTextInput 
               n="01"
               label="What happened?"
               value={editFlagText}
               onChangeText={setEditFlagText}
               placeholder="Update your note..."
            />

            <View style={{ gap: 12, marginTop: 24 }}>
              <AppButton 
                variant="solid" 
                size="lg" 
                disabled={updatingFlag || !editFlagText.trim()}
                onPress={handleUpdateFlag}
              >
                {updatingFlag ? 'SAVING...' : 'SAVE CHANGES'}
              </AppButton>
              
              <AppButton 
                variant="outline" 
                size="lg" 
                disabled={deletingFlag}
                onPress={handleDeleteFlag}
                style={{ borderColor: Colors.accent }}
                textStyle={{ color: Colors.accent }}
              >
                {deletingFlag ? 'DELETING...' : 'DELETE MOMENT'}
              </AppButton>
            </View>
         </View>
      </BottomSheet>
      </SafeAreaView>
    );
  }

  // ==================== MAIN PULSE OVERVIEW ====================
  return (
    <SafeAreaView style={styles.safe}>
      <SamVibeNav onPartnerChange={(pid) => setPartnerId(pid)} />
      <VibeRefreshControl refreshing={refreshing} onRefresh={onRefresh} iconMark="✦" showsVerticalScrollIndicator={false}>
        <View style={styles.inner}>
          <AppText variant="display" size={42} style={{ lineHeight: 42, marginBottom: 6 }}>
            The Pulse<AppText size={42} color={Colors.accent}>.</AppText>
          </AppText>
          <AppText variant="serifItalic" size={16} color={Colors.muted} style={{ lineHeight: 24, marginBottom: 24 }}>
            Deeper patterns, beyond the daily card.
          </AppText>

          <View style={{ gap: 12 }}>
            {/* Thinking of you Ping Card */}
            <Pressable 
              style={[styles.door, { backgroundColor: Colors.bone }]} 
              onPress={handlePoke}
              disabled={thinkingSent || isPoking}
            >
              <View style={styles.doorHeader}>
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                  <AppText style={{ fontSize: 16 }}>◉</AppText>
                  <AppText variant="smallCaps" color={Colors.muted}>IN THIS MOMENT</AppText>
                </View>
                {thinkingSent ? (
                  <AppText variant="mono" color={Colors.accent} style={{ fontSize: 10, fontWeight: '700' }}>
                    SENT ✓
                  </AppText>
                ) : interactionStats && (interactionStats.sent_count > 0 || interactionStats.received_count > 0) ? (
                  <AppText variant="mono" color={Colors.accent} style={{ fontSize: 10 }}>
                    {interactionStats.sent_count} SENT · {interactionStats.received_count} RECEIVED
                  </AppText>
                ) : (
                  <AppText variant="mono" color={Colors.accent} style={{ fontSize: 10 }}>
                    SILENT PING
                  </AppText>
                )}
              </View>
              <AppText variant="display" size={24} style={{ lineHeight: 28, marginBottom: 4 }}>
                Thinking of you
              </AppText>
              <AppText variant="serifItalic" size={14} color={Colors.muted} style={{ lineHeight: 22 }}>
                {thinkingSent
                  ? `Silent ping delivered to ${partnerName}.`
                  : `Send a silent ping to let ${partnerName} know they're on your mind.`}
              </AppText>
            </Pressable>

            {/* The Ladder */}
            <Pressable style={styles.door} onPress={() => setSection('ladder')}>
              <View style={styles.doorHeader}>
                <AppText variant="smallCaps" color={Colors.muted}>The Ladder</AppText>
                <AppText variant="mono" color={Colors.accent} style={{ fontSize: 10 }}>
                  {theirStage === -1 ? 'WAITING' : ladderGap === -1 ? '' : ladderGap === 0 ? 'IN SYNC' : `${ladderGap} STEP${ladderGap > 1 ? 'S' : ''} APART`}
                </AppText>
              </View>
              <AppText variant="display" size={24} style={{ lineHeight: 28, marginBottom: 6 }}>Where do you each think you are?</AppText>
              <AppText variant="serifItalic" size={14} color={Colors.muted} style={{ lineHeight: 22 }}>Mark your stage. See the gap.</AppText>
            </Pressable>

            {/* Patterns */}
            <Pressable style={styles.door} onPress={() => setSection('patterns')}>
              <View style={styles.doorHeader}>
                <AppText variant="smallCaps" color={Colors.muted}>Patterns</AppText>
                <AppText variant="mono" color={Colors.accent} style={{ fontSize: 10 }}>
                   {analytics?.overall_match_percentage ?? 0}% MATCH
                </AppText>
              </View>
              <AppText variant="display" size={24} style={{ lineHeight: 28, marginBottom: 6 }}>What the cards are saying.</AppText>
              <AppText variant="serifItalic" size={14} color={Colors.muted} style={{ lineHeight: 22 }}>Your shared picks over time.</AppText>
            </Pressable>

            {/* Private Flags */}
            <Pressable style={styles.door} onPress={() => setSection('flags')}>
              <View style={styles.doorHeader}>
                <AppText variant="smallCaps" color={Colors.muted}>Flags</AppText>
                <AppText variant="mono" color={Colors.accent} style={{ fontSize: 10 }}>{flags.length} LOGGED</AppText>
              </View>
              <AppText variant="display" size={24} style={{ lineHeight: 28, marginBottom: 6 }}>Your private notes.</AppText>
              <AppText variant="serifItalic" size={14} color={Colors.muted} style={{ lineHeight: 22 }}>Track moments that feel right and wrong.</AppText>
            </Pressable>
          </View>

          <View style={{ height: 80 }} />
        </View>
      </VibeRefreshControl>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Colors.bone },
  inner: { padding: 24 },
  door: {
    backgroundColor: Colors.bone,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: Colors.rule,
    padding: 22,
  },
  doorHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'baseline',
    marginBottom: 8,
  },
  statusCard: {
    padding: 18,
    borderRadius: 14,
    marginBottom: 22,
    borderWidth: 1,
  },
  statBox: {
    flex: 1,
    backgroundColor: '#E9E5D9',
    padding: 16,
    borderRadius: 12,
  },
  progressRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 10,
  },
  progressRow1: {
    borderWidth: 1,
    borderColor: Colors.rule,
    borderRadius: 8,
    marginVertical: 4,
    padding: 14,
  },
  progressBarContainer: {
    flex: 1,
    height: 6,
    backgroundColor: '#EAE2D4',
    borderRadius: 3,
    marginLeft: 12,
    overflow: 'hidden',
  },
  progressBar: {
    height: '100%',
    backgroundColor: Colors.sage,
  },
  matchCard: {
    borderWidth: 1,
    borderColor: Colors.rule,
    backgroundColor: '#EFEBE0',
    padding: 16,
    borderRadius: 12,
    marginBottom: 8,
  },
  flagSummary: {
    flex: 1,
    alignItems: 'center',
    padding: 12,
    backgroundColor: '#E9E5D9',
    borderRadius: 12,
  },
  redFlagBox: {
    backgroundColor: '#1C1C1E',
    padding: 20,
    borderRadius: 14,
    marginBottom: 24,
  },
  logEntry: {
    flexDirection: 'row',
    gap: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: Colors.rule,
    borderRadius: 12,
  },
  logDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    marginTop: 6,
  },
  colorPicker: {
    flex: 1,
    borderWidth: 2,
    borderColor: Colors.rule,
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
  }
});