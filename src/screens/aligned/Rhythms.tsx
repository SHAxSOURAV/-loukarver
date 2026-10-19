import React, { useState, useEffect } from "react";
import { View, StyleSheet, Pressable, Switch, DeviceEventEmitter, ScrollView } from "react-native";
import { Colors } from "../../constants/colors";
import { AppText } from "@/components/ui/AppText";
import { AppButton } from "@/components/ui/AppButton";
import { BottomSheet } from "@/components/ui/BottomSheet";
import { AppTextInput } from "@/components/ui/AppTextInput";
import * as Haptics from "expo-haptics";
import { getLifecycleOverview, addPeriodStart, addPhaseNote, toggleCycleSharing, updatePeriodStart, deletePeriodRecord } from "../../services/lifecycleApi";
import { getEnergyLogs, createEnergyLog, updateEnergyLog, getPartnerEnergy, patchShareStatus } from "../../services/energyApi";
import { getUserProfile, getPartnerProfile } from "../../services/userApi";
import { Calendar, DateData } from "react-native-calendars";
import { LinearGradient } from "expo-linear-gradient";

const formatRelativeTime = (isoString: string | Date): string => {
  if (!isoString) return "";
  const date = typeof isoString === "string" ? new Date(isoString) : isoString;
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  if (diffMins < 1) return "just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays === 1) return "yesterday";
  return `${diffDays}d ago`;
};

const ENERGY_LEVELS = ["Drained", "Flat", "Steady", "On", "Lit"];
const SLEEP_LEVELS = ["Depleted", "Under-Slept", "Adequate", "Rested"];
const STRESS_LEVELS = ["Light", "Moderate", "Heavy", "Max"];

interface RhythmsProps {
  refreshTrigger?: number;
}

const Rhythms: React.FC<RhythmsProps> = ({ refreshTrigger = 0 }) => {
  const [activeSheet, setActiveSheet] = useState<
    "herRhythm" | "yourState" | null
  >(null);

  // API State
  const [lifecycle, setLifecycle] = useState<any>(null);
  const [userGender, setUserGender] = useState<string>("Male");
  const [partnerGender, setPartnerGender] = useState<string>("Male");
  const [partnerName, setPartnerName] = useState<string>("Partner");
  const [partnerEnergyLog, setPartnerEnergyLog] = useState<any>(null);
  const [showCalendar, setShowCalendar] = useState<boolean>(false);
  
  // Energy Form State
  const [todayLogId, setTodayLogId] = useState<string | null>(null);
  const [hasLoggedToday, setHasLoggedToday] = useState(false);
  const [energyLevel, setEnergyLevel] = useState<number>(2);
  const [sleepLevel, setSleepLevel] = useState<number>(2);
  const [stressLevel, setStressLevel] = useState<number>(1);
  const [energyNotes, setEnergyNotes] = useState<string>("");
  const [shareWithPartner, setShareWithPartner] = useState<boolean>(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [isLoadingLifecycle, setIsLoadingLifecycle] = useState(true);
  const [isLoadingEnergy, setIsLoadingEnergy] = useState(true);
  
  // Phase Note & History State
  const [isShared, setIsShared] = useState<boolean>(true);
  const [isEditingNote, setIsEditingNote] = useState(false);
  const [editNoteText, setEditNoteText] = useState("");
  const [isSubmittingNote, setIsSubmittingNote] = useState(false);
  const [editingHistoryId, setEditingHistoryId] = useState<string | null>(null);
  useEffect(() => {
    const loadData = async () => {
      try {
        const lc = await getLifecycleOverview();
        if (lc && lc.success) {
          setLifecycle(lc);
          setIsShared(lc.is_shared ?? true);
          
          if (lc.current_note?.text) {
            setCurrentNoteText(lc.current_note.text);
            if (lc.current_note.created_at) {
              setCreatedDateObj(new Date(lc.current_note.created_at));
            } else {
              setCurrentNoteAgo(lc.current_note.created_ago || "Just now");
              setCreatedDateObj(null);
            }
          } else {
            setCurrentNoteText("No note for today.");
            setCurrentNoteAgo("Just now");
            setCreatedDateObj(null);
          }
        }
      } catch (e) {
        console.log("Error loading lifecycle overview", e);
      } finally {
        setIsLoadingLifecycle(false);
      }
      
      try {
        const profile = await getUserProfile();
        if (profile && profile.success && profile.data) {
          setUserGender(profile.data.gender || "Male");
        }
        
        // Let's get partner profile and set partnerName
        const partnerProfile = await getPartnerProfile();
        if (partnerProfile && partnerProfile.success && partnerProfile.data) {
            setPartnerGender(partnerProfile.data.gender || "Male");
            if (partnerProfile.data.name) {
              setPartnerName(partnerProfile.data.name.trim().split(" ")[0]);
            }
        }
      } catch (e) {
        console.log("Error loading profiles", e);
      }
      
      try {
        const el = await getEnergyLogs();
        if (el && el.success && el.data.length > 0) {
          const latest = el.data[0];
          // Check if the latest log is from today (UTC)
          const logDate = new Date(latest.created_at);
          const now = new Date();
          const isToday = logDate.toISOString().slice(0, 10) === now.toISOString().slice(0, 10);
          
          setEnergyLevel(Math.max(0, ENERGY_LEVELS.indexOf(latest.energy_level)));
          setSleepLevel(Math.max(0, SLEEP_LEVELS.indexOf(latest.sleep)));
          setStressLevel(Math.max(0, STRESS_LEVELS.indexOf(latest.stress)));
          if (latest.notes) setEnergyNotes(latest.notes);
          else setEnergyNotes("");
          setShareWithPartner(latest.share_with_partner);
          
          if (isToday) {
            setTodayLogId(latest.id);
            setHasLoggedToday(true);
          } else {
            setTodayLogId(null);
            setHasLoggedToday(false);
          }
        } else {
          setTodayLogId(null);
          setHasLoggedToday(false);
        }
      } catch (e) {
        console.log("Error loading energy logs", e);
      } finally {
        setIsLoadingEnergy(false);
      }

      try {
        const partnerEl = await getPartnerEnergy();
        if (partnerEl && partnerEl.success && partnerEl.data.length > 0) {
          setPartnerEnergyLog(partnerEl.data[0]);
        } else {
          setPartnerEnergyLog(null);
        }
      } catch (e) {
        console.log("Error loading partner energy logs", e);
      }
    };
    loadData();

    let debounceTimer: any = null;
    const debouncedLoad = () => {
      if (debounceTimer) clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        loadData();
      }, 300);
    };

    const sub = DeviceEventEmitter.addListener('REFRESH_ALIGNED_DATA', debouncedLoad);
    const subCycle = DeviceEventEmitter.addListener('OPEN_RHYTHMS_CYCLE', () => {
      setActiveSheet('herRhythm');
    });
    const subState = DeviceEventEmitter.addListener('OPEN_YOUR_STATE', () => {
      setActiveSheet('yourState');
    });
    return () => {
      if (debounceTimer) clearTimeout(debounceTimer);
      sub.remove();
      subCycle.remove();
      subState.remove();
    };
  }, [refreshTrigger]);

  const handleUpdateCycle = async (day: DateData) => {
    setShowCalendar(false);
    try {
      const [year, month, dayStr] = day.dateString.split("-");
      const formattedDate = `${month}.${dayStr}.${year}`;
      await addPeriodStart({ start_date: formattedDate });
      
      setIsLoadingLifecycle(true);
      const lc = await getLifecycleOverview();
      if (lc && lc.success) {
        setLifecycle(lc);
      }
      DeviceEventEmitter.emit('REFRESH_ALIGNED_DATA');
    } catch (e) {
      console.log("Failed to update cycle dates", e);
    } finally {
      setIsLoadingLifecycle(false);
    }
  };

  const handleUpdateHistoryDate = async (day: DateData) => {
    setShowCalendar(false);
    if (!editingHistoryId) return;
    try {
      const [year, month, dayStr] = day.dateString.split("-");
      const formattedDate = `${month}.${dayStr}.${year}`;
      await updatePeriodStart(editingHistoryId, { start_date: formattedDate });
      
      setEditingHistoryId(null);
      setIsLoadingLifecycle(true);
      const lc = await getLifecycleOverview();
      if (lc && lc.success) {
        setLifecycle(lc);
      }
      DeviceEventEmitter.emit('REFRESH_ALIGNED_DATA');
    } catch (e) {
      console.log("Failed to update history date", e);
    } finally {
      setIsLoadingLifecycle(false);
    }
  };

  const handleDeleteHistoryDate = async (id: string) => {
    try {
      await deletePeriodRecord(id);
      setIsLoadingLifecycle(true);
      const lc = await getLifecycleOverview();
      if (lc && lc.success) {
        setLifecycle(lc);
      }
      DeviceEventEmitter.emit('REFRESH_ALIGNED_DATA');
    } catch (e) {
      console.log("Failed to delete history date", e);
    } finally {
      setIsLoadingLifecycle(false);
    }
  };

  const handleNoteSubmit = async () => {
    if (!editNoteText.trim()) return;
    setIsSubmittingNote(true);
    try {
      await addPhaseNote({
        text: editNoteText,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC"
      });
      setIsEditingNote(false);
      setEditNoteText("");
      
      setIsLoadingLifecycle(true);
      const lc = await getLifecycleOverview();
      if (lc && lc.success) {
        setLifecycle(lc);
      }
    } catch (e) {
      console.log("Error submitting phase note", e);
    } finally {
      setIsSubmittingNote(false);
      setIsLoadingLifecycle(false);
    }
  };

  const handleToggleShare = async (val: boolean) => {
    setIsShared(val);
    try {
      await toggleCycleSharing(val);
    } catch (e) {
      console.log("Error toggling share status", e);
      setIsShared(!val);
    }
  };

  const handleEnergySubmit = async () => {
    setIsSubmitting(true);
    try {
      await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
      const payload = {
        energy_level: ENERGY_LEVELS[energyLevel],
        sleep: SLEEP_LEVELS[sleepLevel],
        stress: STRESS_LEVELS[stressLevel],
        notes: energyNotes,
        share_with_partner: shareWithPartner
      };
      
      // Backend upserts today's log, so always use createEnergyLog
      const result = await createEnergyLog(payload);
      if (result?.data?.id) {
        setTodayLogId(result.data.id);
      }
      setHasLoggedToday(true);
      setIsSuccess(true);
      setTimeout(() => {
        setIsSuccess(false);
        setActiveSheet(null);
      }, 1000);
    } catch (e) {
      console.log("Error submitting energy log", e);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleShareToggle = async (val: boolean) => {
    const prevVal = shareWithPartner;
    setShareWithPartner(val);
    // If we have a saved log for today, persist the toggle to the backend immediately
    if (todayLogId) {
      try {
        await patchShareStatus(todayLogId, { share_with_partner: val });
      } catch (e) {
        console.log("Error patching share status", e);
        setShareWithPartner(prevVal); // rollback on failure
      }
    }
  };

  const ownerName = lifecycle?.period_user_name || "Partner";
  const hasCycleData = !!lifecycle?.stats?.current_phase;
  const currentPhase = lifecycle?.stats?.current_phase || "Not set";
  const daysSinceStart = lifecycle?.stats?.days_since_start || 0;
  const [currentNoteText, setCurrentNoteText] = useState<string>("");
  const [currentNoteAgo, setCurrentNoteAgo] = useState<string>("Just now");
  const [createdDateObj, setCreatedDateObj] = useState<Date | null>(null);

  useEffect(() => {
    if (lifecycle?.current_note?.text) {
      setCurrentNoteText(lifecycle.current_note.text);
      if (lifecycle.current_note.created_at) {
        setCreatedDateObj(new Date(lifecycle.current_note.created_at));
      } else {
        setCurrentNoteAgo(lifecycle.current_note.created_ago || "Just now");
        setCreatedDateObj(null);
      }
    } else {
      setCurrentNoteText("No note for today.");
      setCurrentNoteAgo("Just now");
      setCreatedDateObj(null);
    }
  }, [lifecycle]);

  // Dynamic time ago calculation
  useEffect(() => {
    if (!createdDateObj) return;

    const updateAgo = () => {
      const now = new Date();
      const diffSecs = Math.floor((now.getTime() - createdDateObj.getTime()) / 1000);
      
      if (diffSecs < 60) setCurrentNoteAgo("just now");
      else if (diffSecs < 3600) setCurrentNoteAgo(`${Math.floor(diffSecs / 60)} minute${Math.floor(diffSecs / 60) !== 1 ? 's' : ''} ago`);
      else if (diffSecs < 86400) setCurrentNoteAgo(`${Math.floor(diffSecs / 3600)} hour${Math.floor(diffSecs / 3600) !== 1 ? 's' : ''} ago`);
      else setCurrentNoteAgo(`${Math.floor(diffSecs / 86400)} day${Math.floor(diffSecs / 86400) !== 1 ? 's' : ''} ago`);
    };

    updateAgo();
    const interval = setInterval(updateAgo, 60000); // update every minute
    return () => clearInterval(interval);
  }, [createdDateObj]);  const phaseDesc = lifecycle?.stats?.phase_description || "";


  const partnerEnergyIndex = partnerEnergyLog ? ENERGY_LEVELS.indexOf(partnerEnergyLog.energy_level) : -1;
  const partnerSleepIndex = partnerEnergyLog ? SLEEP_LEVELS.indexOf(partnerEnergyLog.sleep) : -1;
  const partnerStressIndex = partnerEnergyLog ? STRESS_LEVELS.indexOf(partnerEnergyLog.stress) : -1;
  
  const COLOR_MAROON = "#7D1F20";

  return (
    <View>
      <AppText
        variant="smallCaps"
        color={Colors.ink2}
        style={styles.sectionLabel}
      >
        RHYTHMS
      </AppText>

      {/* Main Rhythms Card */}
      <View style={styles.rhythmsCard}>
        {(userGender === "Female" || partnerGender === "Female") && (
          <Pressable onPress={() => setActiveSheet("herRhythm")}>
            <View style={styles.topRow}>
              <View style={styles.circle}>
                <AppText style={{ fontSize: 15 }}>◊</AppText>
              </View>
              <View>
                {isLoadingLifecycle ? (
                  <AppText variant="serifItalic" color={Colors.muted} style={{ marginTop: 10 }}>Loading rhythm data...</AppText>
                ) : hasCycleData ? (
                  <>
                    <AppText
                      variant="mono"
                      color={Colors.accent}
                      style={{ fontSize: 10 }}
                    >
                      {ownerName.toUpperCase()} • {currentPhase.toUpperCase()} • DAY {daysSinceStart}
                    </AppText>
                    <AppText
                      variant="heading"
                      size={17}
                      style={{ marginTop: 5, lineHeight: 24 }}
                    >
                      {currentNoteText}
                    </AppText>

                    <AppText
                      variant="mono"
                      color={Colors.muted}
                      style={{ fontSize: 10, marginTop: 10 }}
                    >
                      TAP FOR CONTEXT
                    </AppText>
                  </>
                ) : (
                  <>
                    <AppText
                      variant="mono"
                      color={Colors.muted}
                      style={{ fontSize: 10 }}
                    >
                      {ownerName.toUpperCase()}
                    </AppText>
                    <AppText
                      variant="heading"
                      size={17}
                      style={{ marginTop: 5, lineHeight: 24, color: Colors.muted }}
                    >
                      No cycle data logged yet.
                    </AppText>
                    <AppText
                      variant="mono"
                      color={Colors.accent}
                      style={{ fontSize: 10, marginTop: 10 }}
                    >
                      TAP TO LEARN MORE
                    </AppText>
                  </>
                )}
              </View>
            </View>
          </Pressable>
        )}

        {(userGender === "Female" || partnerGender === "Female") && (
          <View style={styles.divider} />
        )}

        <Pressable
          onPress={() => {
            Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
            setActiveSheet("yourState");
          }}
          style={{
            flexDirection: "row",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <View>
            <AppText
              variant="smallCaps"
              color={Colors.muted}
              style={{ fontSize: 12 }}
            >
              YOUR STATE • TODAY
            </AppText>
            {hasLoggedToday ? (
              <>
                <AppText variant="heading" size={17} style={{ marginTop: 4 }}>
                  {ENERGY_LEVELS[energyLevel]} · {SLEEP_LEVELS[sleepLevel]} · {STRESS_LEVELS[stressLevel]}
                </AppText>
                <AppText
                  variant="serifItalic"
                  size={14}
                  color={Colors.muted}
                  style={{ marginTop: 3 }}
                >
                  Tap to update →
                </AppText>
              </>
            ) : (
              <>
                <AppText variant="heading" size={17} style={{ marginTop: 4 }}>
                  Update your energy, sleep, stress
                </AppText>
                <AppText
                  variant="serifItalic"
                  size={14}
                  color={Colors.muted}
                  style={{ marginTop: 3 }}
                >
                  Share the physiology behind the day.
                </AppText>
              </>
            )}
          </View>
          <View>
            <AppText style={{ fontSize: 24 }}>→</AppText>
          </View>
        </Pressable>
      </View>

      <AppText
        variant="serifItalic"
        color={Colors.muted}
        style={{ textAlign: "center", marginTop: 40, fontSize: 12 }}
      >
        Published daily, for two.
      </AppText>

      {/* ==================== BOTTOM SHEETS ==================== */}

      {/* Her Rhythm, Right Now */}
      <BottomSheet
        open={activeSheet === "herRhythm"}
        onClose={() => setActiveSheet(null)}
        kicker={`${ownerName.toUpperCase()} • SHARED WITH YOU`}
        title="Her rhythm, right now"
      >
        <View style={{ paddingBottom: 30 }}>
           <AppText
            variant="serifItalic"
            size={15}
            color={Colors.muted}
            style={{ marginBottom: 20, lineHeight: 22 }}
          >
            {ownerName} chose to share this so you have context — not so you have to fix anything. Just hold it with her.
          </AppText>
          <View style={styles.phaseRow}>
            <View style={{ flex: 1 }}>
              <View>
                <AppText
                  variant="mono"
                  color={Colors.accent}
                  style={{ fontSize: 10 }}
                >
                  CURRENT PHASE · DAY {daysSinceStart} OF CYCLE
                </AppText>
                <AppText variant="mono" style={{ fontSize: 25 }}>
                  {currentPhase}.
                </AppText>
              </View>
              <AppText
                variant="serifItalic"
                size={16}
                style={{ lineHeight: 24, marginTop: 12 }}
              >
                {phaseDesc}
              </AppText>
            </View>
          </View>
          {(lifecycle?.current_note?.text || userGender === "Female") && (
            <View style={styles.sheetCard}>
              <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                <AppText
                  variant="smallCaps"
                  color={Colors.ink2}
                  style={{ fontSize: 12 }}
                >
                  • IN HER WORDS
                </AppText>
                {userGender === "Female" && !isEditingNote && (
                  <Pressable onPress={() => { setEditNoteText(lifecycle?.current_note?.text || ""); setIsEditingNote(true); }}>
                    <AppText variant="mono" color={Colors.accent} style={{ fontSize: 10 }}>EDIT</AppText>
                  </Pressable>
                )}
              </View>
              
              {isEditingNote && userGender === "Female" ? (
                <View>
                  <AppTextInput
                    value={editNoteText}
                    onChangeText={setEditNoteText}
                    placeholder="How are you feeling today?"
                    multiline
                    style={{ minHeight: 80, fontSize: 16, marginBottom: 10, fontFamily: "Newsreader_400Regular_Italic", backgroundColor: "transparent" }}
                    autoFocus
                  />
                  <View style={{ flexDirection: "row", justifyContent: "flex-end", gap: 15, marginTop: 10 }}>
                    <Pressable onPress={() => setIsEditingNote(false)}>
                      <AppText variant="smallCaps" color={Colors.muted} style={{ fontSize: 12 }}>CANCEL</AppText>
                    </Pressable>
                    <Pressable onPress={handleNoteSubmit}>
                      <AppText variant="smallCaps" color={Colors.accent} style={{ fontSize: 12 }}>{isSubmittingNote ? "SAVING..." : "SAVE"}</AppText>
                    </Pressable>
                  </View>
                </View>
              ) : (
                <>
                  <AppText variant="serifItalic" size={16} style={{ lineHeight: 24 }}>
                    {currentNoteText}
                  </AppText>
                  <AppText
                    variant="mono"
                    color={Colors.muted}
                    style={{ fontSize: 9, marginTop: 12 }}
                  >
                    UPDATED {currentNoteAgo.toUpperCase()}
                  </AppText>
                </>
              )}
            </View>
          )}

          <AppText
            variant="smallCaps"
            color={Colors.ink2}
            style={{ marginTop: 32, marginBottom: 16, fontSize: 10 }}
          >
            THE FULL CYCLE
          </AppText>

          {/* Cycle Phases */}
          {/* Cycle Phases */}
          {[
            {
              phase: "Menstrual",
              days: "Days 1-5",
              desc: "Estrogen and progesterone at their lowest. The uterus sheds. Energy often low; body in reset.",
            },
            {
              phase: "Follicular",
              days: "Days 6-13",
              desc: "FSH drives follicle development. Estrogen climbs. Energy, mood, and openness usually rise.",
            },
            {
              phase: "Ovulatory",
              days: "Days 14-16",
              desc: "LH surge releases a mature egg. Estrogen peaks. Often the most expressive, social, confident window.",
            },
            {
              phase: "Luteal",
              days: "Days 17-28",
              desc: "Progesterone dominant. Body preparing for possible implantation. Later days can feel inward, more sensitive.",
            },
          ].map((item, i) => {
            const isActive = (currentPhase || "").toLowerCase().trim() === item.phase.toLowerCase().trim();
            return (
              <View
                key={i}
                style={[styles.phaseRow, isActive && styles.activePhase]}
              >
                <View style={{ flex: 1 }}>
                  <View
                    style={{
                      flexDirection: "row",
                      justifyContent: "space-between",
                    }}
                  >
                    <AppText
                      variant="heading"
                      size={13}
                      color={isActive ? "#fff" : Colors.ink}
                    >
                      {item.phase}
                    </AppText>
                    <AppText
                      variant="mono"
                      color={isActive ? "#ddd" : Colors.muted}
                      style={{ fontSize: 10 }}
                    >
                      {item.days}
                    </AppText>
                  </View>
                  <AppText
                    variant="serifItalic"
                    size={14}
                    color={isActive ? "#ddd" : Colors.muted}
                    style={{ marginTop: 6, lineHeight: 20 }}
                  >
                    {item.desc}
                  </AppText>
                </View>
              </View>
            );
          })}

          {userGender === "Female" && (
            <View style={{ marginTop: 20 }}>
              <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 15 }}>
                <AppText variant="smallCaps" color={Colors.ink2} style={{ fontSize: 10 }}>CYCLE HISTORY</AppText>
                <Pressable onPress={() => { setEditingHistoryId(null); setShowCalendar(true); }}>
                  <AppText variant="mono" color={Colors.accent} style={{ fontSize: 10 }}>+ ADD START DATE</AppText>
                </Pressable>
              </View>

              {lifecycle?.recent_history?.length > 0 ? (
                lifecycle.recent_history.map((cycle: any) => (
                  <View key={cycle.id} style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 10, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: Colors.muted }}>
                    <AppText variant="heading" size={14}>{cycle.start_date}</AppText>
                    <View style={{ flexDirection: 'row', gap: 15 }}>
                      <Pressable onPress={() => { setEditingHistoryId(cycle.id); setShowCalendar(true); }}>
                        <AppText variant="mono" color={Colors.muted} style={{ fontSize: 10 }}>EDIT</AppText>
                      </Pressable>
                      <Pressable onPress={() => handleDeleteHistoryDate(cycle.id)}>
                        <AppText variant="mono" color={Colors.accent} style={{ fontSize: 10 }}>DELETE</AppText>
                      </Pressable>
                    </View>
                  </View>
                ))
              ) : (
                <AppText variant="serifItalic" color={Colors.muted} style={{ textAlign: 'center', marginVertical: 10 }}>No cycles logged yet.</AppText>
              )}

              {showCalendar && (
                <View style={{ marginTop: 20, backgroundColor: "#fff", borderRadius: 10, overflow: "hidden" }}>
                  <Calendar
                    onDayPress={editingHistoryId ? handleUpdateHistoryDate : handleUpdateCycle}
                    theme={{
                      todayTextColor: Colors.accent,
                      arrowColor: Colors.accent,
                    }}
                  />
                  <Pressable style={{ padding: 10, alignItems: 'center' }} onPress={() => { setShowCalendar(false); setEditingHistoryId(null); }}>
                    <AppText variant="smallCaps" color={Colors.muted} style={{ fontSize: 10 }}>CANCEL</AppText>
                  </Pressable>
                </View>
              )}

              <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: 40 }}>
                <AppText variant="heading" size={14}>Share rhythm with partner</AppText>
                <Switch
                  value={isShared}
                  onValueChange={handleToggleShare}
                  trackColor={{ false: Colors.muted, true: Colors.accent }}
                  thumbColor="#fff"
                />
              </View>
              <AppText
                variant="serifItalic"
                color={Colors.muted}
                style={{ marginTop: 5, fontSize: 12, lineHeight: 18 }}
              >
                {ownerName} controls what's shown here. You can turn it off anytime.
              </AppText>
            </View>
          )}
        </View>
      </BottomSheet>

      {/* Where you are today */}
      <BottomSheet
        open={activeSheet === "yourState"}
        onClose={() => setActiveSheet(null)}
        kicker="YOUR STATE • TODAY"
        title="Where you are today"
      >
        <View style={{  paddingBottom: 30 }}>
          <AppText
            variant="serifItalic"
            size={15}
            color={Colors.muted}
            style={{ marginBottom: 20, lineHeight: 22 }}
          >
            Your body runs on a daily hormonal rhythm — cortisol peaks in the morning, testosterone fluctuates across the day, and sleep debt or stress measurably shifts both. This is an honest signal, not a performance number.
          </AppText>

          {partnerEnergyLog && (
            <AppText
              variant="mono"
              color={Colors.muted}
              style={{ fontSize: 10, marginBottom: 20, textTransform: 'uppercase', letterSpacing: 0.5 }}
            >
              • {partnerName} last logged: {formatRelativeTime(partnerEnergyLog.updated_at)}
            </AppText>
          )}

          {/* Energy */}
          <View style={{ marginBottom: 24 }}>
            <View
              style={{ flexDirection: "row", justifyContent: "space-between" }}
            >
              <AppText variant="smallCaps" color={Colors.ink2}>
                ENERGY
              </AppText>
              <AppText variant="mono" color={Colors.muted}>
                T / CORTISOL STATE
              </AppText>
            </View>
            <View style={styles.optionRow}>
              {ENERGY_LEVELS.map((label, i) => {
                const isUserSelected = i === energyLevel;
                const isPartnerSelected = i === partnerEnergyIndex;
                const hasSelection = isUserSelected || isPartnerSelected;

                return (
                  <Pressable
                    key={i}
                    style={[styles.optionBtn, { overflow: 'hidden', paddingVertical: 0, minHeight: 48, justifyContent: 'center' }, i === 4 && { width: "100%" }]}
                    onPress={() => {
                      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
                      setEnergyLevel(i);
                    }}
                  >
                    {isUserSelected && isPartnerSelected ? (
                      <LinearGradient
                        colors={[Colors.sage, COLOR_MAROON]}
                        start={{ x: 0, y: 0 }}
                        end={{ x: 1, y: 1 }}
                        style={StyleSheet.absoluteFillObject}
                      />
                    ) : isUserSelected ? (
                      <View style={[StyleSheet.absoluteFillObject, { backgroundColor: Colors.sage }]} />
                    ) : isPartnerSelected ? (
                      <View style={[StyleSheet.absoluteFillObject, { backgroundColor: COLOR_MAROON }]} />
                    ) : null}
                    <View style={{ alignItems: "center", justifyContent: "center", paddingVertical: 6 }}>
                      <AppText
                        style={{
                          color: hasSelection ? "#fff" : Colors.ink,
                          fontSize: 12,
                          fontFamily: hasSelection ? "mono" : "regular",
                        }}
                      >
                        {label.toUpperCase()}
                      </AppText>
                      {isUserSelected && isPartnerSelected ? (
                        <AppText style={{ fontSize: 7, color: '#ffffffd0', marginTop: 2, fontFamily: 'mono' }}>
                          YOU • {partnerName.toUpperCase()}
                        </AppText>
                      ) : isUserSelected ? (
                        <AppText style={{ fontSize: 7, color: '#ffffffd0', marginTop: 2, fontFamily: 'mono' }}>
                          YOU
                        </AppText>
                      ) : isPartnerSelected ? (
                        <AppText style={{ fontSize: 7, color: '#ffffffd0', marginTop: 2, fontFamily: 'mono' }}>
                          {partnerName.toUpperCase()}
                        </AppText>
                      ) : null}
                    </View>
                  </Pressable>
                );
              })}
            </View>
            <AppText variant="serifItalic" size={13} color={Colors.muted}>
              {ENERGY_LEVELS[energyLevel]} — {
                ["Depleted state. Needs total rest.", "Running low. Taking it easy.", "Normal range. Holding well.", "Elevated energy. Feeling good.", "Firing on all cylinders."][energyLevel]
              }
            </AppText>
          </View>

          {/* Sleep */}
          <View style={{ marginBottom: 24 }}>
            <View
              style={{ flexDirection: "row", justifyContent: "space-between" }}
            >
              <AppText variant="smallCaps" color={Colors.ink2}>
                SLEEP
              </AppText>
              <AppText variant="mono" color={Colors.muted}>
                RECOVERY STATE
              </AppText>
            </View>
            <View style={styles.optionRow}>
              {SLEEP_LEVELS.map((label, i) => {
                const isUserSelected = i === sleepLevel;
                const isPartnerSelected = i === partnerSleepIndex;
                const hasSelection = isUserSelected || isPartnerSelected;

                return (
                  <Pressable
                    key={i}
                    style={[styles.optionBtn, { overflow: 'hidden', paddingVertical: 0, minHeight: 48, justifyContent: 'center' }]}
                    onPress={() => {
                      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
                      setSleepLevel(i);
                    }}
                  >
                    {isUserSelected && isPartnerSelected ? (
                      <LinearGradient
                        colors={[Colors.sage, COLOR_MAROON]}
                        start={{ x: 0, y: 0 }}
                        end={{ x: 1, y: 1 }}
                        style={StyleSheet.absoluteFillObject}
                      />
                    ) : isUserSelected ? (
                      <View style={[StyleSheet.absoluteFillObject, { backgroundColor: Colors.sage }]} />
                    ) : isPartnerSelected ? (
                      <View style={[StyleSheet.absoluteFillObject, { backgroundColor: COLOR_MAROON }]} />
                    ) : null}
                    <View style={{ alignItems: "center", justifyContent: "center", paddingVertical: 6 }}>
                      <AppText
                        style={{
                          color: hasSelection ? "#fff" : Colors.ink,
                          fontSize: 12,
                          fontFamily: hasSelection ? "mono" : "regular",
                        }}
                      >
                        {label.toUpperCase()}
                      </AppText>
                      {isUserSelected && isPartnerSelected ? (
                        <AppText style={{ fontSize: 7, color: '#ffffffd0', marginTop: 2, fontFamily: 'mono' }}>
                          YOU • {partnerName.toUpperCase()}
                        </AppText>
                      ) : isUserSelected ? (
                        <AppText style={{ fontSize: 7, color: '#ffffffd0', marginTop: 2, fontFamily: 'mono' }}>
                          YOU
                        </AppText>
                      ) : isPartnerSelected ? (
                        <AppText style={{ fontSize: 7, color: '#ffffffd0', marginTop: 2, fontFamily: 'mono' }}>
                          {partnerName.toUpperCase()}
                        </AppText>
                      ) : null}
                    </View>
                  </Pressable>
                );
              })}
            </View>
            <AppText variant="serifItalic" size={13} color={Colors.muted}>
              {SLEEP_LEVELS[sleepLevel]} — {
                ["Zero recovery. Running on empty.", "One rough night. Recoverable.", "Solid sleep. Ready for the day.", "Excellent recovery. Feeling completely restored."][sleepLevel]
              }
            </AppText>
          </View>

          {/* Stress Load */}
          <View style={{ marginBottom: 32 }}>
            <View
              style={{ flexDirection: "row", justifyContent: "space-between" }}
            >
              <AppText variant="smallCaps" color={Colors.ink2}>
                STRESS LOAD
              </AppText>
              <AppText variant="mono" color={Colors.muted}>
                CORTISOL DEMAND
              </AppText>
            </View>
            <View style={styles.optionRow}>
              {STRESS_LEVELS.map((label, i) => {
                const isUserSelected = i === stressLevel;
                const isPartnerSelected = i === partnerStressIndex;
                const hasSelection = isUserSelected || isPartnerSelected;

                return (
                  <Pressable
                    key={i}
                    style={[styles.optionBtn, { overflow: 'hidden', paddingVertical: 0, minHeight: 48, justifyContent: 'center' }]}
                    onPress={() => {
                      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
                      setStressLevel(i);
                    }}
                  >
                    {isUserSelected && isPartnerSelected ? (
                      <LinearGradient
                        colors={[Colors.sage, COLOR_MAROON]}
                        start={{ x: 0, y: 0 }}
                        end={{ x: 1, y: 1 }}
                        style={StyleSheet.absoluteFillObject}
                      />
                    ) : isUserSelected ? (
                      <View style={[StyleSheet.absoluteFillObject, { backgroundColor: Colors.sage }]} />
                    ) : isPartnerSelected ? (
                      <View style={[StyleSheet.absoluteFillObject, { backgroundColor: COLOR_MAROON }]} />
                    ) : null}
                    <View style={{ alignItems: "center", justifyContent: "center", paddingVertical: 6 }}>
                      <AppText
                        style={{
                          color: hasSelection ? "#fff" : Colors.ink,
                          fontSize: 12,
                          fontFamily: hasSelection ? "mono" : "regular",
                        }}
                      >
                        {label.toUpperCase()}
                      </AppText>
                      {isUserSelected && isPartnerSelected ? (
                        <AppText style={{ fontSize: 7, color: '#ffffffd0', marginTop: 2, fontFamily: 'mono' }}>
                          YOU • {partnerName.toUpperCase()}
                        </AppText>
                      ) : isUserSelected ? (
                        <AppText style={{ fontSize: 7, color: '#ffffffd0', marginTop: 2, fontFamily: 'mono' }}>
                          YOU
                        </AppText>
                      ) : isPartnerSelected ? (
                        <AppText style={{ fontSize: 7, color: '#ffffffd0', marginTop: 2, fontFamily: 'mono' }}>
                          {partnerName.toUpperCase()}
                        </AppText>
                      ) : null}
                    </View>
                  </Pressable>
                );
              })}
            </View>
            <AppText variant="serifItalic" size={13} color={Colors.muted}>
              {STRESS_LEVELS[stressLevel]} — {
                ["Low demand. Feeling relaxed.", "Manageable load. Standard day.", "Elevated load. Shorter patience expected.", "Overwhelmed. Need a break."][stressLevel]
              }
            </AppText>
          </View>

          {/* In your words */}
          <View style={{ marginBottom: 24 }}>
            <AppText
              variant="smallCaps"
              color={Colors.ink2}
              style={{ marginBottom: 8 }}
            >
              04 IN YOUR WORDS (OPTIONAL)
            </AppText>
            <View style={styles.inputBox}>
              <AppTextInput 
                multiline
                placeholder="Optional notes on how you're feeling..."
                value={energyNotes}
                onChangeText={setEnergyNotes}
                style={{ fontSize: 20, fontFamily: 'serifItalic', color: Colors.ink, lineHeight: 28 }}
              />
            </View>
          </View>

          {/* Share toggle */}
          <View style={styles.shareRow}>
            <View style={{ flex: 1 }}>
              <AppText variant="heading" size={16}>
                Share with {partnerName}
              </AppText>
              <AppText
                variant="mono"
                color={Colors.muted}
                style={{ fontSize: 12 }}
              >
                They'll see this on their Today. You can turn it off anytime.
              </AppText>
            </View>
            <Switch
              value={shareWithPartner}
              onValueChange={(val) => {
                Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
                handleShareToggle(val);
              }}
              trackColor={{ false: Colors.rule, true: Colors.accent }}
              thumbColor={"#fff"}
            />
          </View>

          <AppButton 
            variant={isSuccess ? "outline" : "solid"}
            full 
            size="lg" 
            style={{ marginTop: 32 }}
            onPress={handleEnergySubmit}
            disabled={isSubmitting || isSuccess || isLoadingEnergy}
          >
            {isSuccess ? "SAVED!" : isSubmitting ? "SAVING..." : hasLoggedToday ? "UPDATE FOR TODAY →" : "SAVE FOR TODAY →"}
          </AppButton>
        </View>
      </BottomSheet>
      
    </View>
  );
};

export default Rhythms;

const styles = StyleSheet.create({
  sectionLabel: { marginBottom: 12, marginTop: 8 },

  rhythmsCard: {
    backgroundColor: Colors.bone,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: Colors.rule,
    padding: 20,
  },
  topRow: {
    flexDirection: "row",

    gap: 10,
  },
  circle: {
    width: 42,
    height: 42,
    borderRadius: 50,
    backgroundColor: "#ff4f280e",
    alignItems: "center",
    justifyContent: "center",
  },
  divider: {
    height: 1,
    backgroundColor: Colors.rule,
    marginVertical: 16,
  },

  sheetCard: {
    borderWidth: 1,
    borderColor: Colors.rule,
    borderRadius: 12,
    padding: 12,
  },

  phaseRow: {
    padding: 16,
    backgroundColor: Colors.cream,
    borderRadius: 12,
    marginBottom: 8,
  },
  activePhase: {
    backgroundColor: "#1C1C1E",
  },

  updateCycle: {
    paddingVertical: 16,
    alignItems: "center",
    borderTopWidth: 1,
    borderBottomWidth: 1,
    marginTop: 7,
    borderColor: Colors.rule,
  },

  optionRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent: "space-between",
    marginVertical: 10,
  },
  optionBtn: {
    width: "48%",
    marginVertical: 4,
    backgroundColor: Colors.cream,
    borderRadius: 10,
    alignItems: "center",
  },
  selectedOption: {
    backgroundColor: "#C44D4D",
  },
  selectedOptionGreen: {
    backgroundColor: Colors.sage,
  },
  selectedOptionBrown: {
    backgroundColor: "#D4A574",
  },

  inputBox: {
    borderBottomWidth:1,
    borderColor:Colors.rule,
  
    paddingVertical:4,
    minHeight: 80,
  },

  shareRow: {
    flexDirection: "row",
    alignItems: "center",
  backgroundColor: Colors.cream,
    padding: 16,
    borderRadius: 12,
  },
  toggle: {
    width: 50,
    height: 28,
    backgroundColor: Colors.accent,
    borderRadius: 20,
    justifyContent: "center",
    paddingHorizontal: 4,
  },
  toggleCircle: {
    width: 20,
    height: 20,
    backgroundColor: "#fff",
    borderRadius: 10,
    alignSelf: "flex-end",
  },
  levelPill: {
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: Colors.light,
    backgroundColor: Colors.bone,
  },
});
