import React, { useState, useCallback, useEffect, useRef } from "react";
import { View, StyleSheet, Pressable } from "react-native";
import { useFocusEffect } from '@react-navigation/native';
import { Colors } from "../../constants/colors";
import { AppText } from "../../components/ui/AppText";
import { AppButton } from "../../components/ui/AppButton";
import { BottomSheet } from "../../components/ui/BottomSheet";
import { AppTextInput } from "../../components/ui/AppTextInput";
import { createCheckin, updateCheckin, getCheckin, getQuestionsEndpoint } from "../../services/checkinApi";
import { completeRitual } from "../../services/ritualApi";
import { postCheckin } from "../../services/threadApi";
import { getMe } from "../../services/authApi";
import { getPartnerProfile } from "../../services/userApi";

interface SharedCheckinSheetProps {
  open: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

export const SharedCheckinSheet: React.FC<SharedCheckinSheetProps> = ({ open, onClose, onSuccess }) => {
  const [userName, setUserName] = useState("YOU");
  const [partnerName, setPartnerName] = useState("PARTNER");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const isSubmittingRef = useRef(false);
  const [hasCheckedInToday, setHasCheckedInToday] = useState(false);
  const [checkinQ1, setCheckinQ1] = useState("");
  const [checkinQ2, setCheckinQ2] = useState("");
  const [checkinQ3, setCheckinQ3] = useState("");
  const [partnerCheckin, setPartnerCheckin] = useState<any>(null);
  const [questions, setQuestions] = useState({
    question_1: "How are you feeling?",
    question_2: "What do you need most?",
    question_3: "One thing on your mind..."
  });

  const loadData = useCallback(async () => {
    if (!open) return; // Only load when opened
    try {
      const [meData, partnerData] = await Promise.all([
        getMe().catch(() => null),
        getPartnerProfile().catch(() => null)
      ]);
      if (meData?.name) setUserName(meData.name);
      if (partnerData?.name) setPartnerName(partnerData.name);

      const qData = await getQuestionsEndpoint();
      if (qData?.data) {
        setQuestions({
          question_1: qData.data.question_1,
          question_2: qData.data.question_2,
          question_3: qData.data.question_3,
        });
      }

      const today = new Date().toLocaleDateString('en-US', {
        month: '2-digit', day: '2-digit', year: 'numeric'
      }).replace(/\//g, '.');

      const checkinData = await getCheckin(today);
      if (checkinData?.data) {
        if (checkinData.data.my_check_in) {
          setCheckinQ1(checkinData.data.my_check_in.answer_1);
          setCheckinQ2(checkinData.data.my_check_in.answer_2);
          setCheckinQ3(checkinData.data.my_check_in.answer_3);
          setHasCheckedInToday(true);
        } else {
          setHasCheckedInToday(false);
          setCheckinQ1("");
          setCheckinQ2("");
          setCheckinQ3("");
        }
        setPartnerCheckin(checkinData.data.partner_check_in);
      }
    } catch (e) {
      console.log("Error loading checkin sheet data:", e);
    }
  }, [open]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleCheckinSubmit = async () => {
    if (isSubmittingRef.current || isSubmitting) return;
    if (!checkinQ1.trim() || !checkinQ2.trim() || !checkinQ3.trim()) return;

    isSubmittingRef.current = true;
    setIsSubmitting(true);
    try {
      const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
      const today = new Date().toLocaleDateString('en-US', {
        month: '2-digit', day: '2-digit', year: 'numeric'
      }).replace(/\//g, '.');
      
      const hour = new Date().getHours();
      let tod = 'afternoon';
      if (hour < 12) tod = 'morning';
      else if (hour > 17) tod = 'evening';

      if (hasCheckedInToday) {
        await updateCheckin({
          date: today,
          answer_1: checkinQ1,
          answer_2: checkinQ2,
          answer_3: checkinQ3,
          timezone: tz,
          time_name: tod
        });
      } else {
        await createCheckin({
          date: today,
          answer_1: checkinQ1,
          answer_2: checkinQ2,
          answer_3: checkinQ3,
          timezone: tz,
          time_name: tod
        });
        
        // Integrate with Thread section
        await postCheckin({
          date: new Date().toISOString(),
          answer_1: checkinQ1,
          answer_2: checkinQ2,
          answer_3: checkinQ3
        });
        
        await completeRitual({
          ritual_type: 'checkin',
          timezone: tz,
          time_name: tod
        });
        setHasCheckedInToday(true);
      }
      
      if (onSuccess) onSuccess();
      onClose();
    } catch (e) {
      console.log("Error submitting checkin:", e);
    } finally {
      isSubmittingRef.current = false;
      setIsSubmitting(false);
    }
  };

  return (
    <BottomSheet
      open={open}
      onClose={onClose}
      kicker="CHECK IN · ◈"
      title="A pulse on the two of you"
    >
      <AppText
        variant="serifItalic"
        size={15}
        color={Colors.muted}
        style={{ marginVertical: 15, lineHeight: 22 }}
      >
       Three questions. Honest answers. A gentle pulse on where you both are this week.
      </AppText>

      {partnerCheckin ? (
        <>
          {/* Side-by-side editable UI */}
          {/* User Section (editable) */}
          <View style={{ borderWidth: 1, borderColor: Colors.rule, borderRadius: 0, marginBottom: 24 }}>
            <View style={{ flexDirection: "row", justifyContent: "space-between", backgroundColor: "#EAE2D4", padding: 12, borderBottomWidth: 1, borderBottomColor: Colors.rule }}>
              <AppText variant="mono" size={11} color={Colors.ink2}>{userName.toUpperCase()}</AppText>
              <AppText variant="mono" size={11} color={Colors.muted}>Nº 01</AppText>
            </View>
            
            <View style={{ padding: 16, borderBottomWidth: 1, borderBottomColor: Colors.rule }}>
              <AppTextInput 
                label={questions.question_1} n="01" placeholder="Honestly, I'm..." 
                value={checkinQ1} onChangeText={setCheckinQ1} 
              />
            </View>
            
            <View style={{ padding: 16, borderBottomWidth: 1, borderBottomColor: Colors.rule }}>
              <AppTextInput 
                label={questions.question_2} n="02" placeholder="I could use..." 
                value={checkinQ2} onChangeText={setCheckinQ2} 
              />
            </View>
            
            <View style={{ padding: 16 }}>
              <AppTextInput 
                label={questions.question_3} n="03" placeholder="I've been thinking about..." 
                value={checkinQ3} onChangeText={setCheckinQ3} 
              />
            </View>
          </View>

          {/* Partner Section (read-only) */}
          <View style={{ borderWidth: 1, borderColor: Colors.rule, borderRadius: 0, marginBottom: 32 }}>
            <View style={{ flexDirection: "row", justifyContent: "space-between", backgroundColor: "#EAE2D4", padding: 12, borderBottomWidth: 1, borderBottomColor: Colors.rule }}>
              <AppText variant="mono" size={11} color={Colors.ink2}>{partnerName.toUpperCase()}</AppText>
              <AppText variant="mono" size={11} color={Colors.muted}>Nº 02</AppText>
            </View>
            
            <View style={{ padding: 16, borderBottomWidth: 1, borderBottomColor: Colors.rule }}>
              <AppText variant="mono" size={11} color={Colors.muted} style={{ marginBottom: 12 }}>01 {questions.question_1.toUpperCase()}</AppText>
              <AppText variant="serifItalic" size={16} color={Colors.ink}>"{partnerCheckin.answer_1}"</AppText>
            </View>
            
            <View style={{ padding: 16, borderBottomWidth: 1, borderBottomColor: Colors.rule }}>
              <AppText variant="mono" size={11} color={Colors.muted} style={{ marginBottom: 12 }}>02 {questions.question_2.toUpperCase()}</AppText>
              <AppText variant="serifItalic" size={16} color={Colors.ink}>"{partnerCheckin.answer_2}"</AppText>
            </View>
            
            <View style={{ padding: 16 }}>
              <AppText variant="mono" size={11} color={Colors.muted} style={{ marginBottom: 12 }}>03 {questions.question_3.toUpperCase()}</AppText>
              <AppText variant="serifItalic" size={16} color={Colors.ink}>"{partnerCheckin.answer_3}"</AppText>
            </View>
          </View>
        </>
      ) : (
        <>
          {/* Single column editable UI with status text */}
          <AppText variant="serifItalic" size={14} color={Colors.accent} style={{ marginBottom: 20 }}>
            Your partner has not checked in yet.
          </AppText>
          
          <AppTextInput 
            label={questions.question_1} n="01" placeholder="Honestly, I'm..." 
            value={checkinQ1} onChangeText={setCheckinQ1} 
          />

          <AppTextInput 
            label={questions.question_2} n="02" placeholder="I could use..." 
            value={checkinQ2} onChangeText={setCheckinQ2} 
          />

          <AppTextInput 
            label={questions.question_3} n="03" placeholder="I've been thinking about..." 
            value={checkinQ3} onChangeText={setCheckinQ3} 
          />
        </>
      )}

      <AppButton
        variant="solid"
        full
        size="lg"
        style={{ marginTop: 24 }}
        onPress={handleCheckinSubmit}
        disabled={isSubmitting || !checkinQ1.trim() || !checkinQ2.trim() || !checkinQ3.trim()}
        loading={isSubmitting}
      >
        {isSubmitting ? (hasCheckedInToday ? "Updating..." : "Submitting...") : (hasCheckedInToday ? "Update →" : "Submit →")}
      </AppButton>
    </BottomSheet>
  );
};
