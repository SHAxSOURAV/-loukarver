import React, { useState, useEffect, useCallback } from 'react';
import { View, StyleSheet, ActivityIndicator, TextInput, RefreshControl } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Colors } from '../../constants/colors';
import { AppText } from '../../components/ui/AppText';
import { Tag } from '../../components/ui/Tag';
import SamVibeNav from '@/components/ui/SamVibeNav';
import { VibeFlatList } from '../../components/ui/VibeRefreshControl';
import { Feather } from '@expo/vector-icons';

import { getVibeCardHistory } from '../../services/vibeCheckApi';
import { useFocusEffect } from '@react-navigation/native';

export const HistoryScreen: React.FC = () => {
  const [history, setHistory] = useState<any[]>([]);
  const [filter, setFilter] = useState<'All' | 'Matched' | 'Differed'>('All');
  const [searchTerm, setSearchTerm] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [partnerId, setPartnerId] = useState<string | null>(null);
  const [totalMatched, setTotalMatched] = useState(0);
  const [totalDiffered, setTotalDiffered] = useState(0);
  const [refreshing, setRefreshing] = useState(false);

  // Debounce search term
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(searchTerm);
    }, 500);
    return () => clearTimeout(handler);
  }, [searchTerm]);

  const loadHistory = async (pageNum = 1, append = false, currentPartnerId: string | null, search = '', activeFilter = filter) => {
    if (!currentPartnerId) {
       setLoading(false);
       setLoadingMore(false);
       return;
    }
    
    if (pageNum === 1) {
      setLoading(true);
      if (!append) setHistory([]);
    } else {
      setLoadingMore(true);
    }

    try {
      const res = await getVibeCardHistory(currentPartnerId, activeFilter, search, pageNum, 10);
      if (res?.success) {
        if (append) {
          setHistory(prev => [...prev, ...res.data]);
        } else {
          setHistory(res.data);
        }
        setTotalMatched(res.total_matched || 0);
        setTotalDiffered(res.total_differed || 0);
        setHasMore(res.data.length === 10);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  };

  useFocusEffect(
    React.useCallback(() => {
      setPage(1);
      loadHistory(1, false, partnerId, debouncedSearch, filter);
    }, [filter, partnerId, debouncedSearch])
  );

  const handleLoadMore = () => {
    if (!loading && !loadingMore && hasMore) {
      const nextPage = page + 1;
      setPage(nextPage);
      loadHistory(nextPage, true, partnerId, debouncedSearch, filter);
    }
  };

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    setPage(1);
    await loadHistory(1, false, partnerId, debouncedSearch, filter);
    setRefreshing(false);
  }, [partnerId, debouncedSearch, filter]);

  const renderCard = ({ item: h }: { item: any }) => {
    const matched = h.is_match;
    return (
      <View style={styles.card}>
        <View style={styles.cardHeader}>
          <AppText variant="smallCaps" color={Colors.muted}>{h.category}</AppText>
          <AppText variant="mono" color={matched ? Colors.sage : Colors.accent} style={{ fontSize: 10 }}>
            {matched ? '● MATCH' : '● DIFFER'}
          </AppText>
        </View>

        <AppText variant="heading" size={16} color={Colors.ink} style={{ marginBottom: 12 }}>
          {h.question}
        </AppText>

        <View style={styles.optRow}>
          <View style={[styles.opt, h.user_answer === h.option_a && (matched ? styles.optMatchActive : styles.optMineActive)]}>
            <AppText variant="heading" size={13} color={h.user_answer === h.option_a ? Colors.bone : Colors.ink}>{h.option_a}</AppText>
          </View>
          <View style={[styles.opt, h.user_answer === h.option_b && (matched ? styles.optMatchActive : styles.optMineActive)]}>
            <AppText variant="heading" size={13} color={h.user_answer === h.option_b ? Colors.bone : Colors.ink}>{h.option_b}</AppText>
          </View>
        </View>
        <View style={styles.cardFooter}>
          <AppText variant="mono" color={Colors.light} style={{ fontSize: 9 }}>
            YOU PICKED {h.user_answer.toUpperCase()} · {h.partner_name.toUpperCase()} {h.partner_answer.toUpperCase()}
          </AppText>
          <AppText variant="mono" color={Colors.light} style={{ fontSize: 9 }}>{h.date.toUpperCase()}</AppText>
        </View>
      </View>
    );
  };

  const renderHeader = () => (
    <View style={styles.inner}>
      <AppText variant="display" size={42} style={{ lineHeight: 42, marginBottom: 6 }}>
        History<AppText size={42} color={Colors.accent}>.</AppText>
      </AppText>
      <AppText variant="serifItalic" size={16} color={Colors.muted} style={{ lineHeight: 24, marginBottom: 20 }}>
        Every card you've played together.
      </AppText>

      {/* Search Bar */}
      <View style={styles.searchContainer}>
        <Feather name="search" size={18} color={Colors.muted} style={{ marginRight: 8 }} />
        <TextInput
          style={styles.searchInput}
          placeholder="Search day, question, or answers..."
          placeholderTextColor={Colors.muted}
          value={searchTerm}
          onChangeText={setSearchTerm}
          returnKeyType="search"
        />
      </View>

      {/* Filters with Counters */}
      <View style={{ flexDirection: 'row', gap: 6, marginBottom: 22, flexWrap: 'wrap' }}>
        <Tag active={filter === 'All'} onPress={() => setFilter('All')}>All</Tag>
        <Tag active={filter === 'Matched'} onPress={() => setFilter('Matched')}>
          {totalMatched} Matched
        </Tag>
        <Tag active={filter === 'Differed'} onPress={() => setFilter('Differed')}>
          {totalDiffered} Differed
        </Tag>
      </View>

      {history.length === 0 && !loading && (
         <AppText variant="serifItalic" size={15} color={Colors.muted} style={{ textAlign: 'center', marginTop: 40 }}>
            No history found.
         </AppText>
      )}

      {loading && !loadingMore && <ActivityIndicator color={Colors.accent} style={{ marginTop: 20 }} />}
    </View>
  );

  return (
    <SafeAreaView style={styles.safe}>
      <SamVibeNav onPartnerChange={(pid) => setPartnerId(pid)} />
      
      <VibeFlatList
        data={history}
        keyExtractor={(item: any, i: number) => i.toString()}
        renderItem={renderCard}
        ListHeaderComponent={renderHeader()}
        contentContainerStyle={{ paddingBottom: 80 }}
        showsVerticalScrollIndicator={false}
        onEndReached={handleLoadMore}
        onEndReachedThreshold={0.5}
        refreshing={refreshing}
        onRefresh={onRefresh}
        iconMark="◈"
        ListFooterComponent={loadingMore ? <ActivityIndicator color={Colors.accent} style={{ padding: 20 }} /> : null}
      />
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Colors.bone },
  inner: { paddingHorizontal: 24, paddingTop: 24, paddingBottom: 10 },
  searchContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.cream,
    borderWidth: 1,
    borderColor: Colors.rule,
    borderRadius: 24,
    paddingHorizontal: 16,
    paddingVertical: 10,
    marginBottom: 20,
  },
  searchInput: {
    flex: 1,
    fontFamily: 'Inter-Regular',
    fontSize: 14,
    color: Colors.ink,
    padding: 0,
  },
  counterPill: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
    borderWidth: 1,
  },
  card: {
    borderRadius: 14, padding: 16, backgroundColor: Colors.bone,
    borderWidth: 1, borderColor: Colors.rule, marginBottom: 10, marginHorizontal: 24,
    shadowColor: Colors.ink2, shadowOpacity: 0.04, shadowRadius: 6, elevation: 1,
  },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 12 },
  optRow: { flexDirection: 'row', gap: 8, marginBottom: 12 },
  opt: { flex: 1, padding: 10, borderRadius: 10, backgroundColor: Colors.cream, alignItems: 'center' },
  optMineActive: { backgroundColor: Colors.accent },
  optMatchActive: { backgroundColor: Colors.sage },
  cardFooter: { flexDirection: 'row', justifyContent: 'space-between' },
});