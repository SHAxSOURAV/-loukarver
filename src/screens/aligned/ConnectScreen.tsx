import { SafeAreaView } from 'react-native-safe-area-context';
import React, { useState, useEffect, useCallback } from "react";
import { View, ScrollView, StyleSheet, Pressable, DeviceEventEmitter, Alert, RefreshControl } from 'react-native';
import { Colors } from "../../constants/colors";
import { AppText } from "../../components/ui/AppText";
import { AppButton } from "../../components/ui/AppButton";
import { ActivityCard } from "../../components/connect/ActivityCard";
import { BottomSheet } from "../../components/ui/BottomSheet";
import Moment from "./Moment";
import { AppTextInput } from "@/components/ui/AppTextInput";
import AlignedNav from "@/components/ui/AlignedNav";

import { getBrowseIdeas, getActiveIdeas, getCompletedIdeas, getIncompleteIdeas, getCategories, createPersonalizedIdea, updatePersonalizedIdea, deletePersonalizedIdea, selectIdea, markIdeaDone, acceptIdea, requestCancelIdea, respondCancelIdea } from "../../services/ideasApi";
import { triggerNotification } from "../../services/notificationApi";

export const ConnectScreen: React.FC = () => {
  const [filter, setFilter] = useState<string>('all');
  const [tab, setTab] = useState<"yours" | "browse">("yours");
  const [sheet, setSheet] = useState<string | null>(null);
  const [selected, setSelected] = useState<any | null>(null);

  // API State
  const [activeIdeas, setActiveIdeas] = useState<any[]>([]);
  const [completedIdeas, setCompletedIdeas] = useState<any[]>([]);
  const [incompleteIdeas, setIncompleteIdeas] = useState<any[]>([]);
  const [browseIdeas, setBrowseIdeas] = useState<any[]>([]);
  const [yoursFilter, setYoursFilter] = useState<"active" | "completed" | "incomplete">("active");
  const [categories, setCategories] = useState<string[]>(['all', 'movement', 'cooking', 'adventure', 'cozy', 'creative']);
  
  // New Idea Form State
  const [editingIdeaId, setEditingIdeaId] = useState<string | null>(null);
  const [markingDone, setMarkingDone] = useState(false);
  const [newName, setNewName] = useState("");
  const [newTime, setNewTime] = useState("");
  const [newTagline, setNewTagline] = useState("");
  const [newCat, setNewCat] = useState("creative");
  
  const [refreshing, setRefreshing] = useState(false);

  const loadData = useCallback(async () => {
    try {
      if (tab === "yours") {
        if (yoursFilter === "active") {
          const res = await getActiveIdeas();
          if (res.success) setActiveIdeas(res.data);
        } else if (yoursFilter === "completed") {
          const res = await getCompletedIdeas();
          if (res.success) setCompletedIdeas(res.data);
        } else if (yoursFilter === "incomplete") {
          const res = await getIncompleteIdeas();
          if (res.success) setIncompleteIdeas(res.data);
        }
      } else {
        const res = await getBrowseIdeas();
        if (res.success) setBrowseIdeas(res.data);
        const catRes = await getCategories();
        if (catRes.success) setCategories(["all", ...catRes.data]);
      }
    } catch (e) {
      console.log(e);
    }
  }, [tab, yoursFilter]);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    DeviceEventEmitter.emit('REFRESH_ALIGNED_DATA');
    await loadData();
    setRefreshing(false);
  }, [loadData]);

  useEffect(() => {
    loadData();
    const sub1 = DeviceEventEmitter.addListener('REFRESH_IDEAS_DATA', loadData);
    const sub2 = DeviceEventEmitter.addListener('REFRESH_ALIGNED_DATA', loadData);
    return () => {
      sub1.remove();
      sub2.remove();
    };
  }, [loadData]);

  const addFromLibrary = async (ideaId: string) => {
    try {
      await selectIdea(ideaId);
      setTab("yours");
    } catch (e) {
      console.log("Failed to select idea", e);
    }
  };

  const handleProposeNew = async () => {
    if (!newName || !newTime || !newTagline) return;
    try {
      if (editingIdeaId) {
        await updatePersonalizedIdea(editingIdeaId, {
          name: newName,
          time: newTime,
          tagline: newTagline,
          category: newCat
        });
        setEditingIdeaId(null);
      } else {
        await createPersonalizedIdea({
          name: newName,
          time: newTime,
          tagline: newTagline,
          category: newCat
        });
      }
      setSheet(null);
      setTab("browse");
      setNewName("");
      setNewTime("");
      setNewTagline("");
      loadData();
    } catch (e) {
      console.log("Failed to save idea", e);
    }
  };

  const handleEditIdea = (idea: any) => {
    setEditingIdeaId(idea.id);
    setNewName(idea.name);
    setNewTime(idea.time);
    setNewTagline(idea.tagline);
    setNewCat(idea.category);
    setSheet("new");
  };

  const handleDeletePersonalized = async (ideaId: string) => {
    try {
      await deletePersonalizedIdea(ideaId);
      loadData();
    } catch (e) {
      console.log("Failed to delete personalized idea", e);
    }
  };

  const handleAcceptIdea = async (progressId: string) => {
    try {
      const res = await acceptIdea(progressId);
      if (res.success) {
        loadData();
        setSelected(res.data);
      }
    } catch (e) {
      console.log("Failed to accept idea", e);
    }
  };

  const toggleDone = async (progressId: string) => {
    if (markingDone) return;
    setMarkingDone(true);
    try {
      await markIdeaDone(progressId);
      loadData();
      if (selected) {
        setSelected({ ...selected, is_done_user: !selected.is_done_user });
      }
    } catch (e) {
      console.log("Failed to mark idea done", e);
    } finally {
      setMarkingDone(false);
    }
  };

  const handleRequestCancelIdea = (progressId: string) => {
    Alert.alert(
      "Cancel Activity",
      "Are you sure you want to request cancellation? Your partner will need to approve this.",
      [
        { text: "No", style: "cancel" },
        { 
          text: "Yes, Request Cancel", 
          style: "destructive",
          onPress: async () => {
            try {
              const res = await requestCancelIdea(progressId);
              loadData();
              if (res.success) {
                setSelected(res.data);
              }
            } catch (e) {
              console.log("Failed to request cancel", e);
            }
          }
        }
      ]
    );
  };

  const handleRespondCancelIdea = async (progressId: string, approved: boolean) => {
    try {
      const res = await respondCancelIdea(progressId, approved);
      loadData();
      if (res.success) {
        if (approved) setSheet(null);
        else setSelected(res.data);
      }
    } catch (e) {
      console.log("Failed to respond to cancel", e);
    }
  };

  const mapProgressToActivity = (progress: any) => {
    return {
      id: progress.id,
      label: progress.name,
      duration: progress.time,
      description: progress.tagline,
      cat: progress.category,
      status: (progress.is_completed ? 'completed' : 
             (progress.is_accepted_user && progress.is_accepted_partner) ? 'active' : 'pending') as any,
      louDone: progress.is_done_user,
      amandaDone: progress.is_done_partner,
      mark: "✧",
      createdAt: progress.created_at,
      originalProgress: progress
    };
  };

  const filteredBrowse = filter === "all" ? browseIdeas : browseIdeas.filter(i => i.category.toLowerCase() === filter.toLowerCase());

  return (
    <SafeAreaView style={styles.safe}>
      <AlignedNav></AlignedNav>
      <ScrollView 
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl 
            refreshing={refreshing} 
            onRefresh={onRefresh} 
            tintColor={Colors.accent} 
          />
        }
      >
        <View style={styles.inner}>
          <AppText
            variant="display"
            size={42}
            style={{ lineHeight: 42, marginBottom: 6 }}
          >
            Connect
            <AppText size={42} color={Colors.accent}>
              .
            </AppText>
          </AppText>

          {/* Things to do together - Hidden per client feedback */}
          {false && (
            <>
              <AppText
                variant="serifItalic"
                size={16}
                color={Colors.muted}
                style={{ lineHeight: 24, marginBottom: 20 }}
              >
                Things to do together — across distance.
              </AppText>

          <AppText
            style={{
              backgroundColor: "#F1E4DA",
              padding: 8,
              marginBottom: 7,
              borderRadius: 50,
            }}
            variant="smallCaps"
            color={Colors.accent}
          >
            ◐ TODAY ONLY · ALL ITEMS CLEAR AT MIDNIGHT
          </AppText>

          <AppText
            style={{ marginBottom: 10, marginTop: 15 }}
            variant="smallCaps"
          >
            Shared Activities
          </AppText>

          {/* Tab Toggle */}
          <View style={styles.tabRow}>
            {(
              [
                { k: "yours", l: `Yours (${activeIdeas.length})` },
                { k: "browse", l: "Browse Ideas" },
              ] as const
            ).map((t) => (
              <Pressable
                key={t.k}
                onPress={() => {
                  setTab(t.k);
                  if (t.k === "browse") {
                    triggerNotification("Browse Ideas", "Partner is browsing connection ideas").catch(() => {});
                  }
                }}
                style={[styles.tabBtn, tab === t.k && styles.tabBtnActive]}
              >
                <AppText
                  variant="mono"
                  color={tab === t.k ? Colors.bone : Colors.muted}
                  style={{ fontSize: 10 }}
                >
                  {t.l.toUpperCase()}
                </AppText>
              </Pressable>
            ))}
          </View>

          {tab === "yours" && (() => {
            const currentList = yoursFilter === "active" ? activeIdeas : yoursFilter === "completed" ? completedIdeas : incompleteIdeas;
            return (
              <>
                <View style={[styles.tabRow, { marginBottom: 15, padding: 3, borderRadius: 50 }]}>
                  {(
                    [
                      { k: "active", l: `Active (${activeIdeas.length})` },
                      { k: "completed", l: `Completed (${completedIdeas.length})` },
                      { k: "incomplete", l: `Incomplete (${incompleteIdeas.length})` },
                    ] as const
                  ).map((t) => (
                    <Pressable
                      key={t.k}
                      onPress={() => setYoursFilter(t.k)}
                      style={[
                        styles.tabBtn, 
                        yoursFilter === t.k && styles.tabBtnActive,
                        { borderRadius: 50, paddingVertical: 8 }
                      ]}
                    >
                      <AppText
                        variant="mono"
                        color={yoursFilter === t.k ? Colors.bone : Colors.muted}
                        style={{ fontSize: 9 }}
                      >
                        {t.l.toUpperCase()}
                      </AppText>
                    </Pressable>
                  ))}
                </View>
                {currentList.length === 0 ? (
                  <View style={styles.emptyState}>
                    <AppText
                      variant="serifItalic"
                      size={15}
                      color={Colors.muted}
                      style={{ textAlign: "center", marginBottom: 16 }}
                    >
                      No activities yet.{"\n"}Browse ideas or suggest your own.
                    </AppText>
                    <AppButton variant="accent" onPress={() => setTab("browse")}>
                      Browse →
                    </AppButton>
                  </View>
                ) : (
                  currentList.map((progress) => (
                    <ActivityCard
                      key={progress.id}
                      activity={mapProgressToActivity(progress)}
                      onPress={() => {
                        setSelected(progress);
                        setSheet("detail");
                      }}
                    />
                  ))
                )}
                <Pressable style={styles.addRow} onPress={() => { setEditingIdeaId(null); setNewName(""); setNewTime(""); setNewTagline(""); setNewCat("creative"); setSheet("new"); }}>
                  <View>
                    <AppText variant="smallCaps" color={Colors.accent}>
                      + Suggest your own
                    </AppText>
                    <AppText variant="serifItalic" size={13} color={Colors.muted}>
                      Make up an activity together
                    </AppText>
                  </View>
                  <AppText size={18} color={Colors.accent}>
                    →
                  </AppText>
                </Pressable>
              </>
            );
          })()}

          {tab === "browse" && (
            <>
            <View style={{ flexDirection: 'row', gap: 6, flexWrap: "wrap", marginBottom: 10 }}>
              {categories.map((c) => (
                <Pressable key={c} onPress={() => setFilter(c)}>
                  <AppText 
                    variant="smallCaps" 
                    style={{ 
                      paddingHorizontal: 16, 
                      paddingVertical: 8, 
                      backgroundColor: filter === c ? Colors.ink : Colors.bone,
                      color: filter === c ? '#fff' : Colors.muted,
                      borderRadius: 20,
                      borderWidth: 1,
                      borderColor: Colors.rule,
                    }}
                  >
                    {c.charAt(0).toUpperCase() + c.slice(1)}
                  </AppText>
                </Pressable>
              ))}
            </View>
              {filteredBrowse.map((idea) => (
                <Pressable
                  key={idea.id}
                  style={styles.libraryCard}
                  onPress={() => addFromLibrary(idea.id)}
                >
                  <View style={styles.libIcon}>
                    <AppText size={20} color={Colors.accent}>
                      ✧
                    </AppText>
                  </View>
                  <View style={{ flex: 1 }}>
                    <View
                      style={{
                        flexDirection: "row",
                        justifyContent: "space-between",
                        marginBottom: 4,
                      }}
                    >
                      <AppText variant="heading" size={16}>
                        {idea.name}
                      </AppText>
                      <AppText
                        variant="mono"
                        color={Colors.light}
                        style={{ fontSize: 9 }}
                      >
                        {idea.time.toUpperCase()}
                      </AppText>
                    </View>
                    <AppText
                      variant="serifItalic"
                      size={13}
                      color={Colors.muted}
                      style={{ lineHeight: 19 }}
                    >
                      {idea.tagline}
                    </AppText>
                  </View>
                  <View style={{ alignItems: 'flex-end', justifyContent: 'space-between', paddingVertical: 4 }}>
                    <AppText
                      variant="mono"
                      color={Colors.accent}
                      style={{ fontSize: 10 }}
                    >
                      + ADD
                    </AppText>
                    {idea.is_personalized && (
                      <View style={{ flexDirection: 'row', gap: 12, marginTop: 12 }}>
                        <Pressable onPress={() => handleEditIdea(idea)} hitSlop={10}>
                          <AppText variant="mono" color={Colors.muted} style={{ fontSize: 9 }}>EDIT</AppText>
                        </Pressable>
                        <Pressable onPress={() => handleDeletePersonalized(idea.id)} hitSlop={10}>
                          <AppText variant="mono" color={Colors.accentDeep} style={{ fontSize: 9 }}>DEL</AppText>
                        </Pressable>
                      </View>
                    )}
                  </View>
                </Pressable>
              ))}
            </>
          )}
            </>
          )}

          <View>
            <Moment></Moment>
          </View>

          <View style={{ height: 80 }} />
        </View>
      </ScrollView>

      {/* Activity detail sheet */}
      <BottomSheet
        open={sheet === "detail" && !!selected}
        onClose={() => setSheet(null)}
        title={selected?.name ?? ""}
        kicker="ACTIVITY"
      >
        {selected && (
          <>
            <AppText
              variant="serifItalic"
              size={17}
              color={Colors.ink2}
              style={{ lineHeight: 26, marginBottom: 22 }}
            >
              {selected.tagline}
            </AppText>
            
            {!selected.is_accepted_user ? (
              <AppButton variant="accent" full size="lg" onPress={() => handleAcceptIdea(selected.id)}>
                ACCEPT IDEA
              </AppButton>
            ) : !selected.is_accepted_partner ? (
              <AppText variant="serifItalic" color={Colors.muted} style={{ textAlign: 'center', marginVertical: 10 }}>Waiting for partner to accept...</AppText>
            ) : (
              <>
                <AppText
                  variant="smallCaps"
                  color={Colors.muted}
                  style={{ marginBottom: 12 }}
                >
                  Mark done
                </AppText>
                <View style={{ flexDirection: "row", gap: 10 }}>
                  {["you", "partner"].map((u) => {
                    const isDone = u === "you" ? selected.is_done_user : selected.is_done_partner;
                    const isInteractive = u === "you" && !selected.is_done_user;
                    return (
                      <Pressable
                        key={u}
                        style={[styles.doneBtn, isDone && styles.doneBtnActive]}
                        onPress={() => {
                          if (isInteractive && !markingDone) toggleDone(selected.id);
                        }}
                      >
                        <AppText
                          variant="smallCaps"
                          color={isDone ? Colors.sage : Colors.muted}
                        >
                          {u === "you" ? "YOU" : "PARTNER"}
                        </AppText>
                        <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginTop: 20, width: '100%' }}>
                          <AppText
                            size={24}
                            color={isDone ? Colors.sage : Colors.rule}
                          >
                            {isInteractive && markingDone ? "..." : (isDone ? "✓" : "○")}
                          </AppText>
                          {isDone && (
                            <AppText variant="mono" size={10} color={Colors.sage}>
                              {new Date(u === "you" ? selected.done_at_user : selected.done_at_partner).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}
                            </AppText>
                          )}
                        </View>
                      </Pressable>
                    );
                  })}
                </View>
                {!selected.is_completed && !selected.is_expired && (
                  <View style={{ marginTop: 20 }}>
                    {selected.has_user_requested_cancel ? (
                      <AppButton variant="outline" size="md" disabled style={{ borderRadius: 50 }}>
                        Cancellation Requested...
                      </AppButton>
                    ) : selected.has_partner_requested_cancel ? (
                      <View style={{ flexDirection: 'row', gap: 10 }}>
                        <View style={{ flex: 1 }}>
                          <AppButton variant="outline" size="md" onPress={() => handleRespondCancelIdea(selected.id, false)} style={{ borderRadius: 50 }}>
                            Decline Cancel
                          </AppButton>
                        </View>
                        <View style={{ flex: 1 }}>
                          <AppButton variant="accent" size="md" onPress={() => handleRespondCancelIdea(selected.id, true)} style={{ borderRadius: 50 }}>
                            Approve Cancel
                          </AppButton>
                        </View>
                      </View>
                    ) : (
                      <AppButton variant="outline" size="md" onPress={() => handleRequestCancelIdea(selected.id)} style={{ borderRadius: 50 }}>
                        CANCEL ACTIVITY
                      </AppButton>
                    )}
                  </View>
                )}
              </>
            )}
            
          </>
        )}
      </BottomSheet>

      {/* New activity sheet */}
      <BottomSheet
        open={sheet === "new"}
        onClose={() => setSheet(null)}
        kicker="NEW"
        title="Suggest an activity"
      >
        <AppTextInput label="Name" n="01" placeholder="Morning Walk" value={newName} onChangeText={setNewName} />

        <AppTextInput label="Duration" n="02" placeholder="30 min" value={newTime} onChangeText={setNewTime} />

        <AppTextInput
          label="Description"
          n="03"
          placeholder="What you'll do together"
          value={newTagline} onChangeText={setNewTagline}
        />
        <AppText
          variant="smallCaps"
          color={Colors.ink2}
          style={{ marginTop: 15, marginBottom: 10 }}
        >
          04 Category
        </AppText>
        <View style={styles.chipRow}>
          {categories.filter(c => c !== 'all').map((m) => (
            <Pressable
              key={m}
              style={[styles.chip, newCat === m && styles.chipSelected]}
              onPress={() => setNewCat(m)}
            >
              <AppText
                variant="smallCaps"
                style={{
                  color: newCat === m ? "#e7e3e3" : Colors.muted,
                  fontSize: 9,
                }}
              >
                {m.toUpperCase()}
              </AppText>
            </Pressable>
          ))}
        </View>

        <AppButton
          full
          variant="solid"
          size="lg"
          onPress={handleProposeNew}
        >
          Propose →
        </AppButton>
      </BottomSheet>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Colors.bone },
  inner: { padding: 24 },
  tabRow: {
    flexDirection: "row",
    backgroundColor: Colors.cream,
    borderRadius: 10,
    padding: 4,
    marginBottom: 16,
    gap: 4,
  },
  tabBtn: {
    flex: 1,
    paddingVertical: 10,
    alignItems: "center",
    borderRadius: 8,
  },
  tabBtnActive: { backgroundColor: Colors.ink },
  emptyState: {
    padding: 32,
    borderRadius: 14,
    backgroundColor: Colors.cream,
    alignItems: "center",
    marginBottom: 18,
  },
  chipRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
    marginBottom:15
  },
  chip: {
    paddingHorizontal: 13,
    paddingVertical: 3,

    borderRadius: 999,
    borderWidth: 1,
    borderColor: Colors.rule,
  },
  chipSelected: {
    backgroundColor: "#1C1C1E",
    borderColor: "#1C1C1E",
  },
  addRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    padding: 16,
    borderRadius: 10,
    backgroundColor: Colors.cream,
    marginBottom: 30,
  },
  libraryCard: {
    flexDirection: "row",
    gap: 14,
    marginTop:10,
    backgroundColor: Colors.bone,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: Colors.rule,
    padding: 16,
    marginBottom: 10,
    shadowColor: Colors.ink2,
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
    alignItems: "flex-start",
  },
  libIcon: {
    width: 44,
    height: 44,
    borderRadius: 10,
    backgroundColor: Colors.cream,
    alignItems: "center",
    justifyContent: "center",
  },
  doneBtn: {
    flex: 1,
    padding: 16,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: Colors.rule,
    alignItems: "flex-start",
    backgroundColor: Colors.cream,
    justifyContent: "space-between",
  },
  doneBtnActive: {
    backgroundColor: `${Colors.sage}15`,
    borderColor: Colors.sage,
  },
});
