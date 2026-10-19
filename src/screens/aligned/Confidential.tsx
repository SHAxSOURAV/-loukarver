import React, { useState, useEffect, useRef, useCallback } from 'react';
import { SafeAreaView } from 'react-native-safe-area-context';
import { View, StyleSheet, Pressable, Modal, Image, DeviceEventEmitter, ActivityIndicator, Animated, useWindowDimensions, Platform } from 'react-native';
import { CustomAlert } from '../../components/ui/CustomAlert';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useNavigation } from '@react-navigation/native';
import { Colors } from '../../constants/colors';
import { AppText } from '../../components/ui/AppText';
import { AppButton } from '../../components/ui/AppButton';
import * as ImagePicker from 'expo-image-picker';
import { preventScreenCaptureAsync, allowScreenCaptureAsync } from 'expo-screen-capture';
import { uploadSecret, getReceivedSecrets, getSentSecrets, getSecretViewUrl, getSecretViewInfo, requestRewatchSecret, approveRewatchSecret, declineRewatchSecret, revokeSecret } from '../../services/secretApi';
import { triggerNotification } from '../../services/notificationApi';
import { getMe } from '../../services/authApi';
import { Gesture, GestureDetector, GestureHandlerRootView } from 'react-native-gesture-handler';
import { Ionicons } from '@expo/vector-icons';
import ReAnimated, { useSharedValue, useAnimatedStyle, withSpring } from 'react-native-reanimated';
import { LinearGradient } from 'expo-linear-gradient';
import { Camera } from 'expo-camera';
import { BottomSheet } from '../../components/ui/BottomSheet';
import * as FileSystem from 'expo-file-system/legacy';
import { ProfessionalVideoPlayer } from '../../components/ui/ProfessionalVideoPlayer';

const isCurrentMediaVideo = (secret: any, uri: string | null): boolean => {
  if (secret?.is_video === true) return true;
  if (secret?.file_type?.startsWith('video')) return true;
  const filename = (secret?.filename || '').toLowerCase();
  if (filename.endsWith('.mp4') || filename.endsWith('.mov') || filename.endsWith('.webm') || filename.endsWith('.m4v')) return true;
  if (uri) {
    const cleanUri = uri.split('?')[0].toLowerCase();
    if (cleanUri.endsWith('.mp4') || cleanUri.endsWith('.mov') || cleanUri.endsWith('.webm') || cleanUri.endsWith('.m4v')) return true;
    if (uri.startsWith('data:video')) return true;
  }
  return false;
};

const Confidential: React.FC = () => {
  const { width: windowWidth, height: windowHeight } = useWindowDimensions();
  const navigation = useNavigation<any>();
  const [secrets, setSecrets] = useState<any[]>([]);
  const [sentSecrets, setSentSecrets] = useState<any[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadMediaType, setUploadMediaType] = useState<'photo' | 'video'>('video');
  const [isAligned, setIsAligned] = useState<boolean>(true);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [viewingSecret, setViewingSecret] = useState<any | null>(null);
  const [mediaDataUri, setMediaDataUri] = useState<string | null>(null);
  const [authToken, setAuthToken] = useState<string | null>(null);
  const [isPaused, setIsPaused] = useState(false);
  const [downloadProgress, setDownloadProgress] = useState<number | null>(null);
  const [approvingSecretId, setApprovingSecretId] = useState<string | null>(null);
  const [decliningSecretId, setDecliningSecretId] = useState<string | null>(null);
  const [requestingSecretId, setRequestingSecretId] = useState<string | null>(null);

  const progress = useRef(new Animated.Value(1)).current;
  const animRef = useRef<Animated.CompositeAnimation | null>(null);
  const viewingSecretRef = useRef<any>(null);



  // Keep ref in sync for use inside callbacks
  useEffect(() => {
    viewingSecretRef.current = viewingSecret;
  }, [viewingSecret]);

  // Pinch-to-zoom shared values
  const scale = useSharedValue(1);
  const savedScale = useSharedValue(1);
  const translateX = useSharedValue(0);
  const translateY = useSharedValue(0);
  const savedTranslateX = useSharedValue(0);
  const savedTranslateY = useSharedValue(0);

  const pinchGesture = Gesture.Pinch()
    .onUpdate((e) => {
      scale.value = savedScale.value * e.scale;
    })
    .onEnd(() => {
      if (scale.value < 1) {
        scale.value = withSpring(1);
        savedScale.value = 1;
        translateX.value = withSpring(0);
        translateY.value = withSpring(0);
        savedTranslateX.value = 0;
        savedTranslateY.value = 0;
      } else {
        savedScale.value = scale.value;
      }
    });

  const panGesture = Gesture.Pan()
    .minPointers(2)
    .onUpdate((e) => {
      translateX.value = savedTranslateX.value + e.translationX;
      translateY.value = savedTranslateY.value + e.translationY;
    })
    .onEnd(() => {
      savedTranslateX.value = translateX.value;
      savedTranslateY.value = translateY.value;
    });

  const doubleTapGesture = Gesture.Tap()
    .numberOfTaps(2)
    .onEnd(() => {
      if (scale.value > 1) {
        scale.value = withSpring(1);
        savedScale.value = 1;
        translateX.value = withSpring(0);
        translateY.value = withSpring(0);
        savedTranslateX.value = 0;
        savedTranslateY.value = 0;
      } else {
        scale.value = withSpring(2.5);
        savedScale.value = 2.5;
      }
    });

  const composedGesture = Gesture.Simultaneous(pinchGesture, panGesture, doubleTapGesture);

  const animatedImageStyle = useAnimatedStyle(() => ({
    transform: [
      { translateX: translateX.value },
      { translateY: translateY.value },
      { scale: scale.value },
    ],
  }));

  // Screenshot protection scoped to modal
  useEffect(() => {
    if (viewingSecret) {
      preventScreenCaptureAsync().catch(console.error);
    } else {
      allowScreenCaptureAsync().catch(console.error);
      progress.stopAnimation();
      // Reset zoom
      scale.value = 1;
      savedScale.value = 1;
      translateX.value = 0;
      translateY.value = 0;
      savedTranslateX.value = 0;
      savedTranslateY.value = 0;
    }
    return () => { allowScreenCaptureAsync().catch(console.error); };
  }, [viewingSecret]);

  const startTimer = (duration: number) => {
    animRef.current = Animated.timing(progress, {
      toValue: 0,
      duration: duration,
      useNativeDriver: false,
    });
    animRef.current.start(({ finished }) => {
      if (finished) {
        handleViewSecretOut();
      }
    });
  };

  // Start timer for media (10s for images only)
  useEffect(() => {
    if (viewingSecret && mediaDataUri) {
      const isVideo = isCurrentMediaVideo(viewingSecret, mediaDataUri);
      if (!isVideo) {
        progress.setValue(1);
        startTimer(10000);
      }
    }
  }, [viewingSecret, mediaDataUri]);

  // Decrypting timeout safety: abort and alert if decrypting takes longer than 30s
  useEffect(() => {
    let decryptTimer: any = null;
    if (viewingSecret && !mediaDataUri) {
      decryptTimer = setTimeout(() => {
        setViewingSecret(null);
        setMediaDataUri(null);
        CustomAlert.alert("Timeout", "Decrypting secret timed out. Please check your connection and try again.");
      }, 30000);
    }
    return () => {
      if (decryptTimer) clearTimeout(decryptTimer);
    };
  }, [viewingSecret, mediaDataUri]);

  const handlePause = () => {
    setIsPaused(true);
    progress.stopAnimation();
  };

  const handleResume = () => {
    setIsPaused(false);
    const isVideo = isCurrentMediaVideo(viewingSecret, mediaDataUri);
    if (!isVideo) {
      progress.stopAnimation((value) => {
        startTimer(value * 10000);
      });
    }
  };

  const parseUtcDate = (dateStr: string | null) => {
    if (!dateStr) return null;
    let d = dateStr;
    if (!d.endsWith("Z") && !d.includes("+") && !d.includes("-", 10)) d += "Z";
    return new Date(d);
  };

  const loadSecrets = async () => {
    try {
      const [resRec, resSent] = await Promise.all([
        getReceivedSecrets(),
        getSentSecrets()
      ]);
      if (resRec.success) setSecrets(resRec.data);
      if (resSent.success) setSentSecrets(resSent.data);
    } catch (e) {
      console.log("Failed to load secrets", e);
    }
  };

  const checkAlignment = async () => {
    try {
      const meData = await getMe();
      const aligned = !!(meData && (meData.is_aligned || meData.partner));
      setIsAligned(aligned);
    } catch (e) {
      console.log("Failed to check alignment in Confidential", e);
    }
  };

  useEffect(() => {
    const fetchToken = async () => {
      const token = await AsyncStorage.getItem('access_token');
      setAuthToken(token);
    };
    fetchToken();
    loadSecrets();
    checkAlignment();

    let debounceTimer: any = null;
    const debouncedRefresh = () => {
      if (debounceTimer) clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        loadSecrets();
        checkAlignment();
      }, 300);
    };

    const sub1 = DeviceEventEmitter.addListener('REFRESH_SECRET_DATA', debouncedRefresh);
    const sub2 = DeviceEventEmitter.addListener('REFRESH_ALIGNED_DATA', debouncedRefresh);
    const sub3 = DeviceEventEmitter.addListener('ALIGNMENT_BONDED', debouncedRefresh);
    const sub4 = DeviceEventEmitter.addListener('ALIGNMENT_BROKEN', debouncedRefresh);

    return () => {
      if (debounceTimer) clearTimeout(debounceTimer);
      sub1.remove();
      sub2.remove();
      sub3.remove();
      sub4.remove();
    };
  }, []);

  const handleCompose = () => {
    if (!isAligned) {
      CustomAlert.alert(
        "Partner Required",
        "Please connect with your partner first to send confidential photos and videos."
      );
      return;
    }
    setPickerOpen(true);
  };

  const getVideoDurationInSeconds = (asset: any): number | null => {
    if (typeof asset?.duration === 'number' && asset.duration > 0) {
      // Android/iOS native duration is in milliseconds; web HTML5 is in seconds
      return asset.duration > 1000 ? asset.duration / 1000 : asset.duration;
    }
    return null;
  };

  const processAndUploadSecret = async (uri: string, mimeType: string, filename: string, isVideo: boolean = false) => {
    setIsUploading(true);
    setUploadProgress(0);
    setUploadMediaType(isVideo ? 'video' : 'photo');
    try {
      await uploadSecret(uri, mimeType, filename, (percent: number) => {
        setUploadProgress(percent);
      });
      setUploadProgress(100);
      CustomAlert.alert(
        "Delivered",
        isVideo ? "Confidential video sent successfully!" : "Secret photo sent successfully!"
      );
      loadSecrets();
    } catch (error: any) {
      const errorMsg = error?.message || error?.response?.data?.detail || "Could not send the secret.";
      CustomAlert.alert("Upload Failed", errorMsg);
      console.error(error);
    } finally {
      setIsUploading(false);
      setUploadProgress(0);
    }
  };

  const handleTakePhoto = async () => {
    setPickerOpen(false);
    try {
      const { status } = await ImagePicker.requestCameraPermissionsAsync();
      if (status !== 'granted') {
        CustomAlert.alert("Permission Required", "Camera permission is required to take photos.");
        return;
      }

      const result = await ImagePicker.launchCameraAsync({
        mediaTypes: ['images'],
        quality: 0.8,
        allowsEditing: false,
      });

      if (!result.canceled && result.assets && result.assets.length > 0) {
        const asset = result.assets[0];
        await processAndUploadSecret(asset.uri, asset.mimeType || 'image/jpeg', 'secret.jpg', false);
      }
    } catch (e: any) {
      console.error(e);
      CustomAlert.alert("Camera Error", e?.message || "Could not open camera.");
    }
  };

  const handleRecordVideo = async () => {
    setPickerOpen(false);
    try {
      const cameraStatus = await ImagePicker.requestCameraPermissionsAsync();
      const micStatus = await Camera.requestMicrophonePermissionsAsync();
      if (cameraStatus.status !== 'granted' || micStatus.status !== 'granted') {
        CustomAlert.alert("Permission Required", "Camera and microphone permissions are required to record video.");
        return;
      }

      // Max 4 minutes (240s) for video recording
      const result = await ImagePicker.launchCameraAsync({
        mediaTypes: ['videos'],
        videoMaxDuration: 240,
      });

      if (!result.canceled && result.assets && result.assets.length > 0) {
        const asset = result.assets[0];
        const durationSec = getVideoDurationInSeconds(asset);
        if (durationSec !== null && durationSec > 240.5) {
          CustomAlert.alert(
            "Video Too Long",
            "Recorded video exceeds the 4-minute maximum limit (240 seconds)."
          );
          return;
        }
        await processAndUploadSecret(asset.uri, asset.mimeType || 'video/mp4', 'secret.mp4', true);
      }
    } catch (e: any) {
      console.error(e);
      CustomAlert.alert("Video Error", e?.message || "Could not record video.");
    }
  };

  const handleChooseLibrary = async () => {
    setPickerOpen(false);
    try {
      const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (status !== 'granted') {
        CustomAlert.alert("Permission Required", "Photo library permission is required to select photos and videos.");
        return;
      }

      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ['images', 'videos'],
        quality: 0.8,
      });

      if (!result.canceled && result.assets && result.assets.length > 0) {
        const asset = result.assets[0];
        const isVideo = asset.type === 'video' || asset.mimeType?.startsWith('video') || asset.uri.toLowerCase().endsWith('.mp4') || asset.uri.toLowerCase().endsWith('.mov');

        // Enforce 4-minute maximum duration (240 seconds)
        if (isVideo) {
          const durationSec = getVideoDurationInSeconds(asset);
          if (durationSec !== null && durationSec > 240.5) {
            const mins = Math.floor(durationSec / 60);
            const secs = Math.round(durationSec % 60);
            CustomAlert.alert(
              "Video Too Long",
              `Confidential videos cannot exceed 4 minutes (240 seconds).\nSelected video is ${mins}m ${secs}s long. Please trim or select a video under 4 minutes.`
            );
            return;
          }
        }

        const mime = asset.mimeType || (isVideo ? 'video/mp4' : 'image/jpeg');
        const filename = isVideo ? 'secret.mp4' : 'secret.jpg';
        await processAndUploadSecret(asset.uri, mime, filename, isVideo);
      }
    } catch (e: any) {
      console.error(e);
      CustomAlert.alert("Upload Error", e?.message || "Could not open library.");
    }
  };

  const handleViewSecretIn = async (secret: any) => {
    setViewingSecret(secret);
    setMediaDataUri(null);
    setDownloadProgress(null);
    setIsPaused(false);

    try {
      const targetId = secret?.id || secret?._id;
      const viewInfo = await getSecretViewInfo(targetId);
      if (!viewInfo?.url) {
        throw new Error("Could not resolve video stream URL.");
      }

      setViewingSecret((prev: any) => ({ ...prev, ...viewInfo }));
      setMediaDataUri(viewInfo.url);
      setDownloadProgress(null);
    } catch (apiErr: any) {
      console.error("Failed to load secret media:", apiErr);
      const errorMsg = apiErr?.response?.data?.detail || apiErr?.message || "Could not decrypt secret media.";
      
      // Close viewer immediately to prevent infinite DECRYPTING spinner
      setViewingSecret(null);
      setMediaDataUri(null);
      setDownloadProgress(null);
      CustomAlert.alert("Secret Unavailable", errorMsg);
      loadSecrets();
    }
  };

  const handleViewSecretOut = () => {
    if (!viewingSecretRef.current) return;
    setSecrets(prev => prev.filter(s => s.id !== viewingSecretRef.current.id));
    if (mediaDataUri && mediaDataUri.startsWith('file://')) {
      FileSystem.deleteAsync(mediaDataUri, { idempotent: true }).catch(() => {});
    }
    setViewingSecret(null);
    setMediaDataUri(null);
    setDownloadProgress(null);
    progress.stopAnimation();
    setIsPaused(false);
    loadSecrets();
  };

  const handleRequestRewatch = async (secretId: string) => {
    if (requestingSecretId) return;
    setRequestingSecretId(secretId);
    try {
      await requestRewatchSecret(secretId);
      setSecrets(prev => prev.map(s => (s.id === secretId || s._id === secretId) ? { ...s, rewatch_status: 'requested' } : s));
      await loadSecrets();
      CustomAlert.alert("Requested", "Rewatch request sent to your partner.");
    } catch (e: any) {
      console.log(e);
      const msg = e?.response?.data?.detail || e?.message || "Could not request rewatch.";
      CustomAlert.alert("Error", msg);
      loadSecrets();
    } finally {
      setRequestingSecretId(null);
    }
  };

  const handleApproveRewatch = async (secretId: string) => {
    if (approvingSecretId) return;
    setApprovingSecretId(secretId);
    try {
      await approveRewatchSecret(secretId);
      // Optimistic update so UI immediately reflects 'approved' state
      setSentSecrets(prev => prev.map(s => (s.id === secretId || s._id === secretId) ? { ...s, rewatch_status: 'approved', is_viewed: false, status: 'delivered' } : s));
      await loadSecrets();
      CustomAlert.alert("Approved", "Your partner can now view it one more time.");
    } catch (e: any) {
      console.error("Failed to approve rewatch:", e);
      const msg = e?.response?.data?.detail || e?.message || "Could not approve rewatch.";
      CustomAlert.alert("Error", msg);
      loadSecrets();
    } finally {
      setApprovingSecretId(null);
    }
  };

  const handleDeclineRewatch = async (secretId: string) => {
    if (decliningSecretId) return;
    setDecliningSecretId(secretId);
    try {
      await declineRewatchSecret(secretId);
      setSentSecrets(prev => prev.map(s => (s.id === secretId || s._id === secretId) ? { ...s, rewatch_status: 'denied' } : s));
      await loadSecrets();
    } catch (e: any) {
      console.error("Failed to decline rewatch:", e);
      const msg = e?.response?.data?.detail || e?.message || "Could not decline rewatch.";
      CustomAlert.alert("Error", msg);
      loadSecrets();
    } finally {
      setDecliningSecretId(null);
    }
  };

  const handleRevokeSecret = (secretId: string) => {
    CustomAlert.alert(
      "Revoke Secret",
      "Are you sure you want to permanently delete this secret before it's opened?",
      [
        { text: "Cancel", style: "cancel" },
        { 
          text: "Revoke", 
          style: "destructive",
          onPress: async () => {
            try {
              await revokeSecret(secretId);
              loadSecrets();
            } catch (e) {
              console.log(e);
              CustomAlert.alert("Error", "Could not revoke secret.");
            }
          }
        }
      ]
    );
  };

  const renderSecret = (secret: any) => (
    <View key={secret.id} style={styles.messageCard}>
      <View style={styles.messageHeader}>
        <View style={styles.avatar}>
          <AppText style={{ color: '#fff', fontSize: 14 }}>
            {secret.partner_name ? secret.partner_name[0].toUpperCase() : "P"}
          </AppText>
        </View>
        <View>
          <AppText variant="mono" style={styles.fromText}>
            FROM {secret.partner_name ? secret.partner_name.toUpperCase() : "PARTNER"}
          </AppText>
          <AppText variant="heading" size={17} style={{ color: '#fff' }}>
            Something just for you
          </AppText>
        </View>
      </View>

      <View style={styles.messageMeta}>
        <View style={styles.metaTextContainer}>
          <AppText variant="mono" style={styles.metaMainText} numberOfLines={1}>
            {secret.file_type?.startsWith('video') || secret.filename?.endsWith('.mp4') || secret.filename?.endsWith('.mov') ? '🎥 VIDEO' : '📷 PHOTO'} • OPENS ONCE
          </AppText>
          <AppText variant="mono" style={styles.metaSubText} numberOfLines={1}>
            ⏳ {secret.delete_after}
          </AppText>
        </View>
        
        {(!secret.is_viewed || secret.rewatch_status === 'approved') ? (
          <Pressable
            onPress={() => handleViewSecretIn(secret)}
            style={styles.openButton}
          >
            <AppText variant="mono" style={styles.openButtonText}>TAP TO VIEW</AppText>
          </Pressable>
        ) : secret.rewatch_status === "requested" ? (
          <View style={[styles.openButton, { backgroundColor: '#5c544d' }]}>
            <AppText variant="mono" style={styles.openButtonText}>
              WAITING...
            </AppText>
          </View>
        ) : (
          <Pressable
            onPress={() => handleRequestRewatch(secret.id)}
            disabled={requestingSecretId === secret.id}
            style={[styles.openButton, { backgroundColor: '#8C7F75', opacity: requestingSecretId === secret.id ? 0.7 : 1 }]}
          >
            <AppText variant="mono" style={styles.openButtonText}>
              {requestingSecretId === secret.id ? "REQUESTING..." : "ASK TO REWATCH"}
            </AppText>
          </Pressable>
        )}
      </View>
    </View>
  );

  const renderMediaViewer = () => {
    if (!mediaDataUri) {
      return (
        <View style={viewerStyles.loadingContainer}>
          <View style={viewerStyles.loadingPulse}>
            <ActivityIndicator size="large" color="#E06C6C" />
          </View>
          <AppText variant="mono" style={viewerStyles.loadingText}>
            DECRYPTING...
          </AppText>
          <AppText variant="serifItalic" style={viewerStyles.loadingSubtext}>
            Preparing your secret media
          </AppText>
        </View>
      );
    }

    const isVideo = isCurrentMediaVideo(viewingSecret, mediaDataUri);

    if (isVideo) {
      return (
        <ProfessionalVideoPlayer
          uri={mediaDataUri}
          isPausedExternal={isPaused}
          style={{ width: windowWidth, height: windowHeight }}
        />
      );
    }

    // Image with pinch-to-zoom
    return (
      <GestureDetector gesture={composedGesture}>
        <ReAnimated.View 
          style={[{ flex: 1, width: '100%', justifyContent: 'center', alignItems: 'center' }, animatedImageStyle]}
        >
          <Image 
            source={{ uri: mediaDataUri }} 
            style={{ width: windowWidth, height: windowHeight * 0.8, resizeMode: 'contain' }}
          />
        </ReAnimated.View>
      </GestureDetector>
    );
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <AppText variant="mono" style={styles.headerText}>CONFIDENTIAL</AppText>
      </View>

      <AppText variant="display" size={35} style={styles.title}>
        Just between {""}
        <AppText variant="serifItalic" size={32} style={{ color: "#E06C6C" }}>
         you two.
        </AppText>
      </AppText>

      <AppText variant="serifItalic" size={13} color={Colors.cream} style={styles.subtitle}>
        Photos and videos that open once, then disappear. No screenshots, no saves.
      </AppText>

      {secrets.length === 0 ? (
        <AppText variant="serifItalic" color={Colors.muted} style={{ marginTop: 20, marginBottom: 40 }}>
          No new secrets received.
        </AppText>
      ) : (
        <View>
          {renderSecret(secrets[0])}
          {secrets.length > 1 && (
            <Pressable 
              onPress={() => navigation.navigate('SecretHistory')}
              style={{ alignSelf: 'flex-start', padding: 8, backgroundColor: '#3A2823', borderRadius: 8, marginBottom: 20 }}
            >
              <AppText variant="mono" style={{ color: '#E06C6C', fontSize: 11 }}>
                VIEW {secrets.length - 1} OLDER SECRETS
              </AppText>
            </Pressable>
          )}
        </View>
      )}

      {/* Sent Secrets Status Tracker */}
      {sentSecrets.length > 0 && (
        <View style={{ marginTop: 10, marginBottom: 30 }}>
          <AppText variant="smallCaps" color={Colors.ink2} style={{ fontSize: 10, marginBottom: 15, color: '#8C7F75' }}>
            SENT STATUS
          </AppText>
          {sentSecrets.map(sent => (
            <View key={sent.id} style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 12 }}>
              <AppText style={{ fontSize: 14, marginRight: 8 }}>
                {sent.status === 'viewed' ? '⭕' : '🔴'}
              </AppText>
              <View style={{ flex: 1 }}>
                <AppText variant="serifItalic" color={Colors.cream} style={{ fontSize: 15 }}>
                  {sent.status === 'viewed' ? 'Opened' : 'Delivered'}
                </AppText>
                <AppText variant="mono" style={{ color: '#8C7F75', fontSize: 10, marginTop: 2 }}>
                  {sent.file_type?.startsWith('video') || sent.filename?.endsWith('.mp4') || sent.filename?.endsWith('.mov') ? '🎥 VIDEO' : '📷 PHOTO'}
                </AppText>
              </View>

              <Pressable 
                onPress={() => handleViewSecretIn(sent)}
                style={{ backgroundColor: '#2C221E', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 12, marginRight: 8 }}
              >
                <AppText variant="mono" style={{ color: '#E8B4A0', fontSize: 10 }}>PREVIEW</AppText>
              </Pressable>

              {sent.rewatch_status === 'requested' && (
                <View style={{ flexDirection: 'row', gap: 6, alignItems: 'center' }}>
                  <Pressable 
                    onPress={() => handleDeclineRewatch(sent.id)}
                    disabled={decliningSecretId === sent.id || approvingSecretId === sent.id}
                    style={{ 
                      backgroundColor: '#4A3B32', 
                      paddingHorizontal: 10, 
                      paddingVertical: 5, 
                      borderRadius: 12,
                      opacity: (decliningSecretId === sent.id || approvingSecretId === sent.id) ? 0.6 : 1
                    }}
                  >
                    <AppText variant="mono" style={{ color: '#fff', fontSize: 10 }}>
                      {decliningSecretId === sent.id ? 'DENYING...' : 'DENY'}
                    </AppText>
                  </Pressable>
                  <Pressable 
                    onPress={() => handleApproveRewatch(sent.id)}
                    disabled={approvingSecretId === sent.id || decliningSecretId === sent.id}
                    style={{ 
                      backgroundColor: approvingSecretId === sent.id ? '#823727' : '#B7553E', 
                      paddingHorizontal: 10, 
                      paddingVertical: 5, 
                      borderRadius: 12, 
                      marginRight: 10,
                      flexDirection: 'row',
                      alignItems: 'center',
                      gap: 4,
                      opacity: (approvingSecretId === sent.id || decliningSecretId === sent.id) ? 0.8 : 1
                    }}
                  >
                    {approvingSecretId === sent.id && (
                      <ActivityIndicator size="small" color="#fff" style={{ transform: [{ scale: 0.7 }] }} />
                    )}
                    <AppText variant="mono" style={{ color: '#fff', fontSize: 10, fontWeight: '700' }}>
                      {approvingSecretId === sent.id ? 'APPROVING...' : 'APPROVE'}
                    </AppText>
                  </Pressable>
                </View>
              )}

              {sent.rewatch_status === 'approved' && (
                <View style={{ 
                  backgroundColor: '#1C2E22', 
                  borderWidth: 1, 
                  borderColor: '#2F5D38', 
                  paddingHorizontal: 8, 
                  paddingVertical: 4, 
                  borderRadius: 10, 
                  marginRight: 8 
                }}>
                  <AppText variant="mono" style={{ color: '#88D49E', fontSize: 10, fontWeight: '700' }}>
                    APPROVED
                  </AppText>
                </View>
              )}

              {sent.rewatch_status === 'denied' && (
                <View style={{ 
                  backgroundColor: '#2A1F1D', 
                  borderWidth: 1, 
                  borderColor: '#4A312D', 
                  paddingHorizontal: 8, 
                  paddingVertical: 4, 
                  borderRadius: 10, 
                  marginRight: 8 
                }}>
                  <AppText variant="mono" style={{ color: '#E06C6C', fontSize: 10 }}>
                    DENIED
                  </AppText>
                </View>
              )}

              {sent.rewatch_status === 'none' && !sent.is_viewed && (
                <Pressable 
                  onPress={() => handleRevokeSecret(sent.id)}
                  style={{ backgroundColor: '#4A3B32', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 12 }}
                >
                  <AppText variant="mono" style={{ color: '#E06C6C', fontSize: 10 }}>REVOKE</AppText>
                </Pressable>
              )}

              <AppText variant="mono" style={{ color: '#8C7F75', fontSize: 10 }}>
                {parseUtcDate(sent.created_at)?.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}
              </AppText>
            </View>
          ))}
        </View>
      )}

      <View style={styles.composeSection}>
        <AppText variant="smallCaps" style={styles.composeLabel}>COMPOSE</AppText>

        {!isAligned && (
          <View style={styles.notAlignedCard}>
            <View style={styles.notAlignedHeader}>
              <AppText style={{ fontSize: 16, marginRight: 8 }}>🔒</AppText>
              <AppText variant="heading" size={15} style={{ color: '#E06C6C' }}>
                Partner Not Connected
              </AppText>
            </View>
            <AppText variant="serifItalic" size={13} style={styles.notAlignedDesc}>
              Confidential photos are strictly private between two partners. Please connect with your partner on the Today tab first.
            </AppText>
            <Pressable 
              style={styles.connectButton}
              onPress={() => navigation.navigate('Home')}
            >
              <AppText variant="mono" style={styles.connectButtonText}>
                CONNECT WITH PARTNER →
              </AppText>
            </Pressable>
          </View>
        )}

        <Pressable 
          style={[styles.composeButton, !isAligned && styles.composeButtonDisabled]} 
          onPress={handleCompose} 
          disabled={isUploading}
        >
          <AppText variant="heading" size={17} style={{ color: !isAligned ? '#7A6E65' : '#fff' }}>
            {isUploading ? "Sending..." : "Send something private"}
          </AppText>
          <AppText style={{ color: !isAligned ? '#7A6E65' : '#E8B4A0', fontSize: 18 }}>→</AppText>
        </Pressable>
      </View>

      <Modal visible={!!viewingSecret} transparent={true} animationType="fade">
        <GestureHandlerRootView style={{ flex: 1 }}>
          <View style={viewerStyles.container}>
            {/* Top gradient overlay (Photos only; video has its own overlay) */}
            {!isCurrentMediaVideo(viewingSecret, mediaDataUri) && (
              <LinearGradient
                colors={['rgba(0,0,0,0.8)', 'transparent']}
                style={viewerStyles.topGradient}
              />
            )}

            {/* Close button (always clickable on top) */}
            <Pressable onPress={handleViewSecretOut} style={[viewerStyles.closeButton, { zIndex: 99 }]} hitSlop={15}>
              <View style={viewerStyles.closeButtonInner}>
                <AppText style={{ color: '#fff', fontSize: 16, fontWeight: '700' }}>✕</AppText>
              </View>
            </Pressable>

            {/* Progress bar (Photos only) */}
            {mediaDataUri && !isCurrentMediaVideo(viewingSecret, mediaDataUri) && (
              <View style={viewerStyles.progressTrack}>
                <Animated.View style={[viewerStyles.progressBar, { 
                  width: progress.interpolate({ inputRange: [0, 1], outputRange: ['0%', '100%'] })
                }]} />
              </View>
            )}

            {/* Timer label (Photos only) */}
            {mediaDataUri && !isCurrentMediaVideo(viewingSecret, mediaDataUri) && (
              <View style={viewerStyles.timerLabel}>
                <AppText variant="mono" style={{ color: 'rgba(255,255,255,0.5)', fontSize: 9 }}>
                  {isPaused ? 'PAUSED' : 'AUTO-DESTRUCT'}
                </AppText>
              </View>
            )}

            {/* Media content: touch responder only activates for photos */}
            <View 
              style={{ flex: 1, width: '100%', justifyContent: 'center', alignItems: 'center' }}
              onStartShouldSetResponder={() => !isCurrentMediaVideo(viewingSecret, mediaDataUri)}
              onResponderGrant={!isCurrentMediaVideo(viewingSecret, mediaDataUri) ? handlePause : undefined}
              onResponderRelease={!isCurrentMediaVideo(viewingSecret, mediaDataUri) ? handleResume : undefined}
              onResponderTerminate={!isCurrentMediaVideo(viewingSecret, mediaDataUri) ? handleResume : undefined}
            >
              {renderMediaViewer()}
            </View>

            {/* Bottom gradient overlay (Photos only) */}
            {!isCurrentMediaVideo(viewingSecret, mediaDataUri) && (
              <LinearGradient
                colors={['transparent', 'rgba(0,0,0,0.6)']}
                style={viewerStyles.bottomGradient}
              />
            )}

            {/* Bottom hint (Photos only) */}
            {mediaDataUri && !isCurrentMediaVideo(viewingSecret, mediaDataUri) && (
              <View style={viewerStyles.bottomHint}>
                <AppText variant="mono" style={{ color: 'rgba(255,255,255,0.35)', fontSize: 9 }}>
                  HOLD TO PAUSE • PINCH TO ZOOM • DOUBLE TAP TO 2.5×
                </AppText>
              </View>
            )}
          </View>
        </GestureHandlerRootView>
      </Modal>

      {/* ─── Video/Photo Upload Progress Modal ─── */}
      <Modal
        visible={isUploading}
        transparent={true}
        animationType="fade"
        statusBarTranslucent={true}
      >
        <View style={styles.uploadOverlay}>
          <View style={styles.uploadCard}>
            <View style={styles.uploadHeader}>
              <View style={styles.uploadIconBadge}>
                <Ionicons
                  name={uploadMediaType === 'video' ? 'videocam' : 'image'}
                  size={24}
                  color={Colors.accent}
                />
              </View>
              <View style={{ flex: 1, marginLeft: 14 }}>
                <AppText variant="heading" size={17} color="#fff">
                  {uploadMediaType === 'video' ? 'Uploading Video' : 'Uploading Photo'}
                </AppText>
                <AppText variant="serifItalic" size={12.5} color="#8C7F75" style={{ marginTop: 2 }}>
                  {uploadProgress >= 100
                    ? 'Finalizing encryption...'
                    : `Encrypted transfer · ${uploadProgress}%`}
                </AppText>
              </View>
              <AppText variant="mono" size={17} color={Colors.accent} style={{ fontWeight: '700' }}>
                {uploadProgress}%
              </AppText>
            </View>

            {/* Progress Track */}
            <View style={styles.progressBarTrack}>
              <View style={[styles.progressBarFill, { width: `${Math.max(4, uploadProgress)}%` }]} />
            </View>

            <View style={styles.uploadFooter}>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                <Ionicons name="lock-closed" size={12} color="#8C7F75" />
                <AppText variant="mono" size={10} color="#8C7F75" style={{ letterSpacing: 0.5 }}>
                  MAX 4 MIN · END-TO-END ENCRYPTED
                </AppText>
              </View>
              <ActivityIndicator size="small" color={Colors.accent} />
            </View>
          </View>
        </View>
      </Modal>

      {/* Media Picker Bottom Sheet */}
      <BottomSheet
        open={pickerOpen}
        onClose={() => setPickerOpen(false)}
        title="Send something private"
        kicker="CONFIDENTIAL"
        dark={true}
      >
        <View style={styles.sheetOptionContainer}>
          <Pressable style={styles.sheetOption} onPress={handleTakePhoto}>
            <View style={styles.sheetIconWrap}>
              <AppText size={20}>📷</AppText>
            </View>
            <View style={{ flex: 1 }}>
              <AppText variant="heading" size={17} color="#fff">Take Photo</AppText>
              <AppText variant="serifItalic" size={13} color="#8C7F75">Capture a moment from your camera</AppText>
            </View>
            <AppText color="#8C7F75" size={16}>→</AppText>
          </Pressable>

          <Pressable style={styles.sheetOption} onPress={handleRecordVideo}>
            <View style={styles.sheetIconWrap}>
              <AppText size={20}>🎥</AppText>
            </View>
            <View style={{ flex: 1 }}>
              <AppText variant="heading" size={17} color="#fff">Record Video</AppText>
              <AppText variant="serifItalic" size={13} color="#8C7F75">Up to 4 minutes with sound</AppText>
            </View>
            <AppText color="#8C7F75" size={16}>→</AppText>
          </Pressable>

          <Pressable style={styles.sheetOption} onPress={handleChooseLibrary}>
            <View style={styles.sheetIconWrap}>
              <AppText size={20}>📁</AppText>
            </View>
            <View style={{ flex: 1 }}>
              <AppText variant="heading" size={17} color="#fff">Choose from Library</AppText>
              <AppText variant="serifItalic" size={13} color="#8C7F75">Upload photos or videos up to 4 minutes</AppText>
            </View>
            <AppText color="#8C7F75" size={16}>→</AppText>
          </Pressable>
        </View>
      </BottomSheet>
    </View>
  );
};

export default Confidential;

const styles = StyleSheet.create({
  container: {
    backgroundColor: "#1D1815",
    padding: 20,
    borderRadius: 16,
    marginVertical: 12,
    borderWidth: 1,
    borderColor: "#2E221E",
    overflow: "hidden",
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  headerText: { fontSize: 10, letterSpacing: 1, color: '#AD442E' },
  title: { color: "#fff", marginBottom: 4 },
  subtitle: { marginTop: -7, marginBottom: 24 },
  messageCard: {
    backgroundColor: '#2D1D1A',
    borderRadius: 16,
    padding: 14,
    marginBottom: 20,
    borderWidth: 1,
    borderColor: '#3D2824',
  },
  messageHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginBottom: 16,
  },
  avatar: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: '#E06C6C',
    alignItems: 'center',
    justifyContent: 'center',
  },
  fromText: {
    fontSize: 11,
    color: '#AD442E',
    letterSpacing: 1,
  },
  messageMeta: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: 12,
  },
  metaTextContainer: {
    flex: 1,
    marginRight: 8,
  },
  metaMainText: {
    color: '#A8998D',
    fontSize: 11,
    letterSpacing: 0.5,
  },
  metaSubText: {
    color: '#8C7F75',
    fontSize: 10,
    marginTop: 3,
    letterSpacing: 0.5,
  },
  openButton: {
    backgroundColor: '#B7553E',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    minWidth: 105,
  },
  openButtonText: {
    color: '#fff',
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 0.5,
  },
  composeSection: {
    marginTop: 8,
  },
  composeLabel: {
    fontSize: 11,
    letterSpacing: 2,
    color: '#8C7F75',
    marginBottom: 10,
  },
  composeButton: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: '#2E2622',
    padding: 20,
    borderRadius: 14,
  },
  composeButtonDisabled: {
    opacity: 0.6,
    borderWidth: 1,
    borderColor: '#3A2E28',
  },
  notAlignedCard: {
    backgroundColor: '#261D1A',
    borderColor: '#3D2A24',
    borderWidth: 1,
    borderRadius: 14,
    padding: 16,
    marginBottom: 12,
  },
  notAlignedHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 6,
  },
  notAlignedDesc: {
    color: '#A89B91',
    lineHeight: 18,
    marginBottom: 12,
  },
  connectButton: {
    alignSelf: 'flex-start',
    backgroundColor: '#AD442E',
    paddingHorizontal: 12,
    paddingVertical: 7,
    borderRadius: 8,
  },
  connectButtonText: {
    color: '#FFFFFF',
    fontSize: 10,
    letterSpacing: 1,
    fontWeight: '600',
  },
  sheetOptionContainer: {
    paddingVertical: 10,
    gap: 12,
    paddingBottom: 24,
  },
  sheetOption: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#2D1D1A',
    padding: 16,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: 'rgba(224, 108, 108, 0.2)',
  },
  sheetIconWrap: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: '#1D1815',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 14,
  },
  uploadOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.78)',
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 24,
    zIndex: 9999,
  },
  uploadCard: {
    width: '100%',
    maxWidth: 380,
    backgroundColor: '#161311',
    borderRadius: 20,
    padding: 22,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.08)',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 0.45,
    shadowRadius: 18,
    elevation: 10,
  },
  uploadHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 18,
  },
  uploadIconBadge: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: 'rgba(204, 123, 92, 0.15)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  progressBarTrack: {
    height: 6,
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    borderRadius: 3,
    overflow: 'hidden',
    marginBottom: 14,
  },
  progressBarFill: {
    height: '100%',
    backgroundColor: Colors.accent,
    borderRadius: 3,
  },
  uploadFooter: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
});

const viewerStyles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0A0A0A',
    justifyContent: 'center',
    alignItems: 'center',
  },
  topGradient: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    height: 150,
    zIndex: 5,
  },
  bottomGradient: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    height: 100,
    zIndex: 5,
  },
  closeButton: {
    position: 'absolute',
    top: 55,
    right: 20,
    zIndex: 10,
  },
  closeButtonInner: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: 'rgba(255,255,255,0.12)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  progressTrack: {
    position: 'absolute',
    top: 100,
    left: 24,
    right: 24,
    height: 3,
    backgroundColor: 'rgba(255,255,255,0.1)',
    borderRadius: 2,
    overflow: 'hidden',
    zIndex: 10,
  },
  progressBar: {
    height: '100%',
    backgroundColor: '#E06C6C',
    borderRadius: 2,
  },
  timerLabel: {
    position: 'absolute',
    top: 108,
    right: 24,
    zIndex: 10,
  },
  loadingContainer: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  loadingPulse: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: 'rgba(224, 108, 108, 0.1)',
    borderWidth: 1,
    borderColor: 'rgba(224, 108, 108, 0.2)',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 20,
  },
  loadingText: {
    color: '#E06C6C',
    fontSize: 12,
    letterSpacing: 3,
    marginBottom: 8,
  },
  loadingSubtext: {
    color: 'rgba(255,255,255,0.3)',
    fontSize: 13,
  },
  pausedOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0,0,0,0.5)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  pausedIcon: {
    fontSize: 48,
    color: '#fff',
    marginBottom: 12,
  },
  pausedText: {
    color: 'rgba(255,255,255,0.7)',
    fontSize: 14,
    letterSpacing: 4,
  },
  bottomHint: {
    position: 'absolute',
    bottom: 30,
    alignSelf: 'center',
    zIndex: 10,
  },
});