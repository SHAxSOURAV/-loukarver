import React, { useState } from "react";
import { View, StyleSheet, Pressable, Platform } from "react-native";
import { Colors } from "../../constants/colors";
import { AppText } from "./AppText";
import DateTimePicker from "@react-native-community/datetimepicker";
import { Ionicons } from "@expo/vector-icons";

type DateTimePickerFieldProps = {
  label: string;
  date: Date;
  onDateChange: (date: Date) => void;
  showCalendar?: boolean;
  onCalendarToggle?: (visible: boolean) => void;
};

const DateTimePickerField: React.FC<DateTimePickerFieldProps> = ({
  label,
  date,
  onDateChange,
  showCalendar = false,
  onCalendarToggle,
}) => {
  const [showTimePicker, setShowTimePicker] = useState(false);
  const [showDatePicker, setShowDatePicker] = useState(false);

  const formatDate = (d: Date) =>
    d.toLocaleDateString("en-US", {
      month: "2-digit",
      day: "2-digit",
      year: "numeric",
    });

  const formatTime = (d: Date) =>
    d.toLocaleTimeString("en-US", {
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
    });

  const handleDateChange = (_: any, selectedDate?: Date) => {
    // Android-এ picker auto-close হয়, iOS-এ হয় না
    if (Platform.OS === "android") setShowDatePicker(false);
    if (selectedDate) {
      const updated = new Date(date);
      updated.setFullYear(selectedDate.getFullYear());
      updated.setMonth(selectedDate.getMonth());
      updated.setDate(selectedDate.getDate());
      onDateChange(updated);
      onCalendarToggle?.(false);
    }
  };

  const handleTimeChange = (_: any, selectedTime?: Date) => {
    if (Platform.OS === "android") setShowTimePicker(false);
    if (selectedTime) {
      const updated = new Date(date);
      updated.setHours(selectedTime.getHours());
      updated.setMinutes(selectedTime.getMinutes());
      onDateChange(updated);
    }
  };

  return (
    <View style={{ marginBottom: 24 }}>
      <AppText
        variant="smallCaps"
        color={Colors.ink2}
        style={{ fontSize: 12, marginBottom: 8 }}
      >
        {label}
      </AppText>

      {/* ── DATE ROW ── */}
      <Pressable
        style={styles.row}
        onPress={() => {
          setShowTimePicker(false); // time picker বন্ধ করো
          setShowDatePicker((prev) => !prev);
          onCalendarToggle?.(!showCalendar);
        }}
      >
        <AppText variant="display" size={26}>
          {formatDate(date)}
        </AppText>
        <Ionicons name="calendar-outline" size={24} color="#000" />
      </Pressable>

      {/* Date Picker — iOS inline / Android modal */}
      {(showDatePicker || showCalendar) && (
        <View style={styles.pickerWrapper}>
          <DateTimePicker
            value={date}
            mode="date"
            display={Platform.OS === "ios" ? "inline" : "default"}
            onChange={handleDateChange}
            themeVariant="light"
          />
          {/* iOS-এ manually close করতে হয় */}
          {Platform.OS === "ios" && (
            <Pressable
              onPress={() => {
                setShowDatePicker(false);
                onCalendarToggle?.(false);
              }}
              style={styles.doneBtn}
            >
              <AppText
                variant="smallCaps"
                color={Colors.accent}
                style={{ fontSize: 13 }}
              >
                Done
              </AppText>
            </Pressable>
          )}
        </View>
      )}

      {/* ── TIME ROW ── */}
      <Pressable
        style={[styles.row, { marginTop: 12 }]}
        onPress={() => {
          setShowDatePicker(false); // date picker বন্ধ করো
          onCalendarToggle?.(false);
          setShowTimePicker((prev) => !prev);
        }}
      >
        <AppText variant="display" size={26}>
          {formatTime(date)}
        </AppText>
        <Ionicons name="time-outline" size={24} color="#000" />
      </Pressable>

      {/* Time Picker — iOS inline / Android modal */}
      {showTimePicker && (
        <View style={styles.pickerWrapper}>
          <DateTimePicker
            value={date}
            mode="time"
            display={Platform.OS === "ios" ? "spinner" : "default"}
            is24Hour={false}
            onChange={handleTimeChange}
          />
          {Platform.OS === "ios" && (
            <Pressable
              onPress={() => setShowTimePicker(false)}
              style={styles.doneBtn}
            >
              <AppText
                variant="smallCaps"
                color={Colors.accent}
                style={{ fontSize: 13 }}
              >
                Done
              </AppText>
            </Pressable>
          )}
        </View>
      )}
    </View>
  );
};

export default DateTimePickerField;

const styles = StyleSheet.create({
  row: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    backgroundColor: "#F9F7F4",
    padding: 16,
    borderRadius: 12,
  },
  pickerWrapper: {
    marginTop: 8,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: Colors.rule,
    overflow: "hidden",
    backgroundColor: "#F9F7F4",
  },
  doneBtn: {
    alignItems: "flex-end",
    padding: 12,
    borderTopWidth: 1,
    borderColor: Colors.rule,
  },
});