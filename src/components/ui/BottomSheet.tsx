import React, { useEffect, useState } from "react";
import {
  Modal,
  View,
  Pressable,
  StyleSheet,
  useWindowDimensions,
  Platform,
  Keyboard,
  ScrollView,
} from "react-native";
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withSpring,
  withTiming,
} from "react-native-reanimated";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { GestureHandlerRootView } from "react-native-gesture-handler";
import { Colors } from "../../constants/colors";
import { AppText } from "./AppText";
import { AppButton } from "./AppButton";

interface BottomSheetProps {
  open: boolean;
  onClose: () => void;
  title: string;
  kicker?: string;
  dark?: boolean;
  noScroll?: boolean;
  children: React.ReactNode;
}

export const BottomSheet: React.FC<BottomSheetProps> = ({
  open,
  onClose,
  title,
  kicker,
  dark = false,
  noScroll = false,
  children,
}) => {
  const { height: screenHeight } = useWindowDimensions();
  const insets = useSafeAreaInsets();
  const translateY = useSharedValue(screenHeight);
  const keyboardShift = useSharedValue(0);
  const [currentKeyboardHeight, setCurrentKeyboardHeight] = useState(0);

  useEffect(() => {
    const showEvent = Platform.OS === "ios" ? "keyboardWillShow" : "keyboardDidShow";
    const hideEvent = Platform.OS === "ios" ? "keyboardWillHide" : "keyboardDidHide";

    const showSub = Keyboard.addListener(showEvent, (e) => {
      const height = e.endCoordinates.height;
      setCurrentKeyboardHeight(height);
      const duration = e.duration && e.duration > 0 ? e.duration : 250;
      keyboardShift.value = withTiming(height, { duration });
    });

    const hideSub = Keyboard.addListener(hideEvent, (e) => {
      setCurrentKeyboardHeight(0);
      const duration = e?.duration && e?.duration > 0 ? e.duration : 200;
      keyboardShift.value = withTiming(0, { duration });
    });

    return () => {
      showSub.remove();
      hideSub.remove();
    };
  }, []);

  useEffect(() => {
    if (open) {
      translateY.value = withSpring(0, {
        damping: 30,
        stiffness: 220,
        mass: 1,
      });
    } else {
      keyboardShift.value = 0;
      setCurrentKeyboardHeight(0);
      translateY.value = withSpring(screenHeight, {
        damping: 25,
        stiffness: 200,
      });
    }
  }, [open, screenHeight]);

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ translateY: translateY.value }],
  }));

  const animatedOverlayStyle = useAnimatedStyle(() => ({
    paddingBottom: keyboardShift.value,
  }));

  const bg = dark ? Colors.ink : Colors.bone;
  const textColor = dark ? Colors.bone : Colors.ink;
  const subtleColor = dark ? "rgba(255,255,255,0.15)" : Colors.rule;

  const handleClose = () => {
    Keyboard.dismiss();
    onClose();
  };

  const topSafety = insets.top || 40;
  const maxSheetHeight = currentKeyboardHeight > 0
    ? Math.max(screenHeight - currentKeyboardHeight - topSafety - 10, 200)
    : "90%";

  const bottomInset = insets.bottom || 0;
  // Detect navigation mode:
  // - Android 3-Button Navigation bar reports bottomInset >= 24 (typically 48px).
  // - Android Gesture Navigation reports bottomInset < 24 (typically 0px - 16px).
  // - iOS Home Indicator reports bottomInset = 34px.
  const isAndroidThreeButtonNav = Platform.OS === 'android' && bottomInset >= 24;
  const dynamicBottomPadding = isAndroidThreeButtonNav
    ? bottomInset + 8
    : Math.max(bottomInset, 16);

  const sheetContent = (
    <Animated.View
      style={[
        styles.sheet,
        animatedStyle,
        { 
          backgroundColor: bg, 
          flexShrink: 1, 
          maxHeight: maxSheetHeight,
        },
      ]}
    >
      {/* Handle */}
      <View style={styles.handleContainer}>
        <View style={[styles.handle, { backgroundColor: subtleColor }]} />
      </View>

      {/* Header */}
      <View
        style={[
          styles.header,
          { borderBottomColor: subtleColor, paddingBottom: 16 },
        ]}
      >
        <View style={{ flex: 1, paddingRight: 12 }}>
          {kicker ? (
            <View style={{ marginBottom: 6 }}>
              <AppText
                variant="smallCaps"
                color={dark ? Colors.light : Colors.muted}
              >
                {kicker}
              </AppText>
            </View>
          ) : null}
          <AppText
            variant="display"
            style={{ letterSpacing: -0.4, lineHeight: 30 }}
            size={24}
            color={textColor}
          >
            {title}
          </AppText>
        </View>

        <AppButton
          variant="ghost"
          size="sm"
          onPress={handleClose}
          textStyle={{ color: dark ? Colors.light : Colors.muted }}
          style={{ borderWidth: 1, borderColor: Colors.rule, borderRadius: 30, marginTop: 2 }}
        >
          Close
        </AppButton>
      </View>

      {/* Content */}
      {noScroll ? (
        <View style={[styles.content, { flexShrink: 1, paddingBottom: dynamicBottomPadding }]}>
          {children}
        </View>
      ) : (
        <ScrollView
          contentContainerStyle={[
            styles.content,
            { paddingBottom: dynamicBottomPadding }
          ]}
          showsVerticalScrollIndicator={false}
          bounces={false}
          keyboardShouldPersistTaps="handled"
        >
          {children}
        </ScrollView>
      )}
    </Animated.View>
  );

  return (
    <Modal
      transparent
      visible={open}
      animationType="none"
      onRequestClose={handleClose}
      statusBarTranslucent
    >
      <GestureHandlerRootView style={{ flex: 1 }}>
        <Animated.View style={[styles.overlay, animatedOverlayStyle]}>
          <Pressable style={StyleSheet.absoluteFill} onPress={handleClose} />
          {sheetContent}
        </Animated.View>
      </GestureHandlerRootView>
    </Modal>
  );
};

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    justifyContent: "flex-end",
    backgroundColor: "rgba(26, 22, 20, 0.65)",
  },
  sheet: {
    maxHeight: "90%",
    minHeight: 200,
    borderTopLeftRadius: 28,
    borderTopRightRadius: 28,
    overflow: "hidden",
  },
  handleContainer: {
    alignItems: "center",
    paddingTop: 12,
    paddingBottom: 8,
  },
  handle: {
    width: 36,
    height: 4,
    borderRadius: 3,
  },
  header: {
    flexDirection: "row",
    alignItems: "flex-start",
    paddingHorizontal: 20,
    paddingVertical: 16,
    borderBottomWidth: 1,
  },
  content: {
    paddingHorizontal: 20,
    paddingBottom: 40,
  },
});
