import React, { useState, useCallback, useEffect } from "react";
import {
  View,
  StyleSheet,
  Pressable,
  ActivityIndicator,
  Alert,
  FlatList,
  DeviceEventEmitter,
} from "react-native";
import { Colors } from "../../constants/colors";
import { AppText } from "../../components/ui/AppText";
import { BottomSheet } from "../../components/ui/BottomSheet";
import { Ionicons } from "@expo/vector-icons";
import Swipeable from "react-native-gesture-handler/Swipeable";
import { listHiddenVibeDates, deleteVibeDateForMe, unhideVibeDate } from "../../services/vibeDatesApi";

interface VCHiddenDatesBottomSheetProps {
  open: boolean;
  onClose: () => void;
}

export const VCHiddenDatesBottomSheet: React.FC<VCHiddenDatesBottomSheetProps> = ({ open, onClose }) => {
  const [dates, setDates] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);

  const fetchData = useCallback(async (pageNum = 1, append = false) => {
    if (!open) return;
    try {
      if (pageNum === 1) setLoading(true);
      else setLoadingMore(true);

      const res = await listHiddenVibeDates(pageNum, 20);
      if (res?.data) {
        if (append) {
          setDates(prev => [...prev, ...res.data]);
        } else {
          setDates(res.data);
        }
        setHasMore(res.data.length === 20);
        setPage(pageNum);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  }, [open]);

  useEffect(() => {
    if (open) {
      fetchData(1, false);
    }
  }, [open, fetchData]);

  const handleLoadMore = () => {
    if (!loadingMore && hasMore) {
      fetchData(page + 1, true);
    }
  };

  const handleDeleteForMe = async (dateId: string) => {
    setDates((prev) => prev.filter((d) => d.id !== dateId));
    try {
      await deleteVibeDateForMe(dateId);
      DeviceEventEmitter.emit("REFRESH_VIBE_DATA");
    } catch (e: any) {
      Alert.alert("Error", "Failed to delete date.");
      fetchData(1, false); 
    }
  };

  const handleUnhide = async (dateId: string) => {
    setDates((prev) => prev.filter((d) => d.id !== dateId));
    try {
      await unhideVibeDate(dateId);
      DeviceEventEmitter.emit("REFRESH_VIBE_DATA");
    } catch (e: any) {
      Alert.alert("Error", "Failed to unhide date.");
      fetchData(1, false); 
    }
  };

  const renderLeftActions = () => (
    <View style={[styles.hideActionContainer, { alignItems: 'flex-start', paddingLeft: 24, flex: 1 }]}>
      <Ionicons name="trash-outline" size={20} color={'#D9534F'} />
      <AppText color={'#D9534F'} variant="mono" style={{ fontSize: 10, marginTop: 4, letterSpacing: 1 }}>DELETE</AppText>
    </View>
  );

  const renderRightActions = () => (
    <View style={[styles.hideActionContainer, { alignItems: 'flex-end', paddingRight: 24, flex: 1 }]}>
      <Ionicons name="eye-outline" size={20} color={Colors.sage} />
      <AppText color={Colors.sage} variant="mono" style={{ fontSize: 10, marginTop: 4, letterSpacing: 1 }}>UNHIDE</AppText>
    </View>
  );

  const renderItem = (d: any) => (
    <View key={d.id} style={{ marginBottom: 10 }}>
      <Swipeable
        renderLeftActions={renderLeftActions}
        renderRightActions={renderRightActions}
        onSwipeableOpen={(direction) => {
          if (direction === 'left') handleDeleteForMe(d.id);
          if (direction === 'right') handleUnhide(d.id);
        }}
        overshootLeft={true}
        friction={1.5}
      >
        <Pressable style={({ pressed }) => [styles.pastCard, pressed && { opacity: 0.7 }]}>
          <View>
            <AppText variant="heading" size={15}>
              {d.where}
            </AppText>
            <AppText
              variant="mono"
              color={Colors.light}
              style={{ fontSize: 9, marginTop: 2 }}
            >
              {new Date(d.date).toLocaleDateString("en-US", { month: "short", day: "numeric" }).toUpperCase()} · {d.status.toUpperCase()}
            </AppText>
            {d.note && (
                <AppText
                  variant="serifItalic"
                  size={13}
                  color={Colors.muted}
                  style={{ marginTop: 4 }}
                >
                  {d.note}
                </AppText>
            )}
          </View>
        </Pressable>
      </Swipeable>
    </View>
  );

  return (
    <BottomSheet
      open={open}
      onClose={onClose}
      kicker="HISTORY"
      title="Hidden Dates"
    >
      <View style={{ height: 400, marginTop: 10 }}>
        {loading ? (
          <ActivityIndicator color={Colors.accent} style={{ marginTop: 40 }} />
        ) : dates.length === 0 ? (
          <AppText variant="serifItalic" color={Colors.muted} style={{ textAlign: 'center', marginTop: 40 }}>
            No hidden dates.
          </AppText>
        ) : (
          <View style={{ paddingBottom: 40 }}>
            {dates.map(d => renderItem(d))}
            
            {hasMore && (
              <Pressable onPress={handleLoadMore} style={{ alignItems: 'center', marginVertical: 10 }}>
                {loadingMore ? (
                  <ActivityIndicator color={Colors.accent} />
                ) : (
                  <AppText variant="mono" color={Colors.accent} style={{ fontSize: 10 }}>LOAD MORE</AppText>
                )}
              </Pressable>
            )}
          </View>
        )}
      </View>
    </BottomSheet>
  );
};

const styles = StyleSheet.create({
  pastCard: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    backgroundColor: Colors.bone,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: Colors.rule,
    padding: 14,
    gap: 12,
  },
  hideActionContainer: {
    justifyContent: 'center',
    height: '100%',
    flex: 1,
  },
});
