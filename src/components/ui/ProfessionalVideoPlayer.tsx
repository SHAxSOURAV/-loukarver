import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  View,
  StyleSheet,
  Pressable,
  ActivityIndicator,
  Animated,
  useWindowDimensions,
  Platform,
  LayoutChangeEvent,
} from 'react-native';
import { useVideoPlayer, VideoView } from 'expo-video';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { AppText } from './AppText';
import { Colors } from '../../constants/colors';

interface ProfessionalVideoPlayerProps {
  uri: string;
  isPausedExternal?: boolean;
  onEnded?: () => void;
  style?: any;
}

const formatTime = (seconds: number): string => {
  if (isNaN(seconds) || seconds < 0) return '00:00';
  const totalSecs = Math.floor(seconds);
  const mins = Math.floor(totalSecs / 60);
  const secs = totalSecs % 60;
  const pad = (n: number) => (n < 10 ? `0${n}` : `${n}`);
  return `${pad(mins)}:${pad(secs)}`;
};

export const ProfessionalVideoPlayer: React.FC<ProfessionalVideoPlayerProps> = ({
  uri,
  isPausedExternal = false,
  onEnded,
  style,
}) => {
  const { width: windowWidth } = useWindowDimensions();

  // Player state
  const [isPlaying, setIsPlaying] = useState<boolean>(true);
  const [isBuffering, setIsBuffering] = useState<boolean>(true);
  const [isMuted, setIsMuted] = useState<boolean>(false);
  const [hasEnded, setHasEnded] = useState<boolean>(false);
  const [currentTime, setCurrentTime] = useState<number>(0);
  const [duration, setDuration] = useState<number>(0);
  const [showControls, setShowControls] = useState<boolean>(true);
  const [trackWidth, setTrackWidth] = useState<number>(windowWidth - 140);
  const [isSeeking, setIsSeeking] = useState<boolean>(false);
  const [seekPreviewTime, setSeekPreviewTime] = useState<number>(0);
  const [seekFeedback, setSeekFeedback] = useState<'-10s' | '+10s' | null>(null);
  const [hasError, setHasError] = useState<boolean>(false);

  // Animation values
  const controlsOpacity = useRef(new Animated.Value(1)).current;
  const hideTimerRef = useRef<any>(null);
  const lastTapRef = useRef<number>(0);
  const seekFeedbackTimerRef = useRef<any>(null);

  // Initialize expo-video player directly with the remote streaming URI
  const player = useVideoPlayer(uri, (p) => {
    p.loop = false;
    p.timeUpdateEventInterval = 0.25;
    p.play();
  });

  // Track player events
  useEffect(() => {
    if (!player) return;

    // Set initial state if player is already ready
    if (player.duration > 0) {
      setDuration(player.duration);
    }
    if (player.status === 'readyToPlay') {
      setIsBuffering(false);
      if (!isPausedExternal && !player.playing) {
        player.play();
      }
    } else if (player.status === 'error') {
      setIsBuffering(false);
      setHasError(true);
    }
    setIsPlaying(player.playing);

    const subPlaying = player.addListener('playingChange', (event) => {
      setIsPlaying(event.isPlaying);
      if (event.isPlaying) {
        setHasEnded(false);
      }
    });

    const subStatus = player.addListener('statusChange', (event) => {
      if (event.status === 'loading') {
        setIsBuffering(true);
      } else if (event.status === 'readyToPlay') {
        setIsBuffering(false);
        if (player.duration > 0) {
          setDuration(player.duration);
        }
        if (!isPausedExternal && !player.playing) {
          player.play();
        }
      } else if (event.status === 'error') {
        setIsBuffering(false);
        setHasError(true);
      }
    });

    const subSourceLoad = player.addListener('sourceLoad', (event) => {
      if (event.duration > 0) {
        setDuration(event.duration);
      }
      if (!isPausedExternal && !player.playing) {
        player.play();
      }
    });

    const subTime = player.addListener('timeUpdate', (event) => {
      if (!isSeeking) {
        setCurrentTime(event.currentTime);
      }
      if (player.duration > 0 && duration <= 0) {
        setDuration(player.duration);
      }
    });

    const subEnd = player.addListener('playToEnd', () => {
      setHasEnded(true);
      setIsPlaying(false);
      showControlsWithTimeout();
      if (onEnded) onEnded();
    });

    const subMuted = player.addListener('mutedChange', (event) => {
      setIsMuted(event.muted);
    });

    // Fallback interval to capture duration as soon as native player finishes buffering
    const durationInterval = setInterval(() => {
      if (player && player.duration > 0) {
        setDuration((prev) => (prev <= 0 ? player.duration : prev));
      }
    }, 500);

    return () => {
      clearInterval(durationInterval);
      subPlaying.remove();
      subStatus.remove();
      subSourceLoad.remove();
      subTime.remove();
      subEnd.remove();
      subMuted.remove();
    };
  }, [player, isSeeking, duration, onEnded, isPausedExternal]);

  // Sync external pause (e.g. modal state)
  useEffect(() => {
    if (!player) return;
    if (isPausedExternal) {
      player.pause();
    }
  }, [isPausedExternal, player]);

  // Controls Auto-Hide Logic
  const resetHideTimer = useCallback(() => {
    if (hideTimerRef.current) {
      clearTimeout(hideTimerRef.current);
    }
    hideTimerRef.current = setTimeout(() => {
      if (player.playing && !hasEnded) {
        Animated.timing(controlsOpacity, {
          toValue: 0,
          duration: 300,
          useNativeDriver: true,
        }).start(() => setShowControls(false));
      }
    }, 3500);
  }, [player, hasEnded, controlsOpacity]);

  const showControlsWithTimeout = useCallback(() => {
    setShowControls(true);
    Animated.timing(controlsOpacity, {
      toValue: 1,
      duration: 200,
      useNativeDriver: true,
    }).start();
    resetHideTimer();
  }, [controlsOpacity, resetHideTimer]);

  const toggleControls = useCallback(() => {
    if (showControls) {
      if (hideTimerRef.current) clearTimeout(hideTimerRef.current);
      Animated.timing(controlsOpacity, {
        toValue: 0,
        duration: 250,
        useNativeDriver: true,
      }).start(() => setShowControls(false));
    } else {
      showControlsWithTimeout();
    }
  }, [showControls, controlsOpacity, showControlsWithTimeout]);

  // Handle Double-Tap (Left = -10s, Right = +10s) and Single-Tap (Toggle controls)
  const handleScreenPress = (event: any) => {
    const now = Date.now();
    const DOUBLE_TAP_DELAY = 300;
    const touchX = event.nativeEvent.locationX;

    if (now - lastTapRef.current < DOUBLE_TAP_DELAY) {
      // Double tap detected
      const isLeftSide = touchX < windowWidth * 0.4;
      const isRightSide = touchX > windowWidth * 0.6;

      if (isLeftSide) {
        seekByRelative(-10);
      } else if (isRightSide) {
        seekByRelative(10);
      }
      lastTapRef.current = 0;
    } else {
      lastTapRef.current = now;
      toggleControls();
    }
  };

  const seekByRelative = (seconds: number) => {
    if (!player) return;
    const newTime = Math.max(0, Math.min(duration || 240, currentTime + seconds));
    player.seekBy(seconds);
    setCurrentTime(newTime);
    setHasEnded(false);

    // Show temporary pill feedback
    setSeekFeedback(seconds < 0 ? '-10s' : '+10s');
    if (seekFeedbackTimerRef.current) clearTimeout(seekFeedbackTimerRef.current);
    seekFeedbackTimerRef.current = setTimeout(() => {
      setSeekFeedback(null);
    }, 800);

    showControlsWithTimeout();
  };

  // Play / Pause / Replay toggle
  const handlePlayPause = () => {
    if (!player) return;
    if (hasEnded) {
      player.replay();
      setHasEnded(false);
      setIsPlaying(true);
    } else if (player.playing) {
      player.pause();
      setIsPlaying(false);
    } else {
      player.play();
      setIsPlaying(true);
    }
    showControlsWithTimeout();
  };

  // Mute / Unmute
  const handleToggleMute = () => {
    if (!player) return;
    player.muted = !player.muted;
    setIsMuted(player.muted);
    showControlsWithTimeout();
  };

  // Scrubber Pan/Touch Handling
  const handleScrubberTouch = (touchX: number) => {
    if (trackWidth <= 0 || duration <= 0) return;
    const clampedX = Math.max(0, Math.min(touchX, trackWidth));
    const targetProgress = clampedX / trackWidth;
    const targetSeconds = targetProgress * duration;
    setSeekPreviewTime(targetSeconds);
  };

  const onScrubberGrant = (evt: any) => {
    setIsSeeking(true);
    handleScrubberTouch(evt.nativeEvent.locationX);
    if (hideTimerRef.current) clearTimeout(hideTimerRef.current);
  };

  const onScrubberMove = (evt: any) => {
    handleScrubberTouch(evt.nativeEvent.locationX);
  };

  const onScrubberRelease = () => {
    if (!player) return;
    player.currentTime = seekPreviewTime;
    setCurrentTime(seekPreviewTime);
    setIsSeeking(false);
    setHasEnded(false);
    resetHideTimer();
  };

  // Layout for scrubber track width
  const onTrackLayout = (event: LayoutChangeEvent) => {
    const { width } = event.nativeEvent.layout;
    if (width > 0) setTrackWidth(width);
  };

  const activeTime = isSeeking ? seekPreviewTime : currentTime;
  const progressRatio = duration > 0 ? Math.min(1, Math.max(0, activeTime / duration)) : 0;

  return (
    <View style={[styles.container, style]}>
      {/* Native Video View */}
      <VideoView
        style={StyleSheet.absoluteFill}
        player={player}
        contentFit="contain"
        nativeControls={false}
        surfaceType={Platform.OS === 'android' ? 'textureView' : undefined}
      />

      {/* Main Touch Area for controls toggle & double-tap skip */}
      <Pressable
        style={StyleSheet.absoluteFill}
        onPress={handleScreenPress}
      >
        {/* Double-tap seek feedback overlay */}
        {seekFeedback && (
          <View style={styles.seekFeedbackOverlay} pointerEvents="none">
            <View style={styles.seekFeedbackPill}>
              <Ionicons
                name={seekFeedback === '-10s' ? 'play-back' : 'play-forward'}
                size={20}
                color="#fff"
              />
              <AppText variant="mono" size={13} color="#fff" style={{ fontWeight: '700', marginLeft: 6 }}>
                {seekFeedback}
              </AppText>
            </View>
          </View>
        )}
      </Pressable>

      {/* Center Buffering Spinner */}
      {isBuffering && !hasError && (
        <View style={styles.bufferingContainer} pointerEvents="none">
          <ActivityIndicator size="large" color="#E06C6C" />
          <AppText variant="mono" size={11} color="rgba(255,255,255,0.7)" style={{ marginTop: 8 }}>
            BUFFERING...
          </AppText>
        </View>
      )}

      {/* Error state */}
      {hasError && (
        <View style={styles.errorContainer}>
          <Ionicons name="alert-circle-outline" size={40} color="#E06C6C" />
          <AppText variant="heading" size={16} color="#fff" style={{ marginTop: 10 }}>
            Playback Error
          </AppText>
          <AppText variant="serifItalic" size={12} color="rgba(255,255,255,0.7)" style={{ marginTop: 4, textAlign: 'center' }}>
            Unable to stream this video. Please tap to retry.
          </AppText>
          <Pressable
            style={styles.retryButton}
            onPress={() => {
              setHasError(false);
              player.replay();
            }}
          >
            <AppText variant="mono" size={11} color="#fff">RETRY</AppText>
          </Pressable>
        </View>
      )}

      {/* ─── Controls Overlay ─── */}
      {showControls && (
        <Animated.View
          style={[styles.controlsOverlay, { opacity: controlsOpacity }]}
          pointerEvents={showControls ? 'box-none' : 'none'}
        >
          {/* Top Bar */}
          <LinearGradient
            colors={['rgba(0,0,0,0.75)', 'transparent']}
            style={styles.topGradientBar}
          >
            <View style={styles.topControlsRow}>
              <View style={styles.confidentialBadge}>
                <Ionicons name="lock-closed" size={11} color="#E06C6C" />
                <AppText variant="mono" size={10} color="#E8B4A0" style={{ letterSpacing: 1, marginLeft: 4 }}>
                  CONFIDENTIAL STREAM
                </AppText>
              </View>

              {/* Mute Button */}
              <Pressable
                onPress={handleToggleMute}
                style={styles.iconCircleButton}
                hitSlop={12}
              >
                <Ionicons
                  name={isMuted ? 'volume-mute' : 'volume-high'}
                  size={18}
                  color="#fff"
                />
              </Pressable>
            </View>
          </LinearGradient>

          {/* Center Playback Controls */}
          <View style={styles.centerControlsRow} pointerEvents="box-none">
            {/* -10s Rewind */}
            <Pressable
              onPress={() => seekByRelative(-10)}
              style={styles.skipButton}
              hitSlop={10}
            >
              <Ionicons name="play-back" size={24} color="#fff" />
              <AppText variant="mono" size={9} color="#fff" style={{ marginTop: 2, fontWeight: '700' }}>
                -10s
              </AppText>
            </Pressable>

            {/* Play / Pause / Replay Button */}
            <Pressable
              onPress={handlePlayPause}
              style={styles.mainPlayPauseButton}
              hitSlop={10}
            >
              <Ionicons
                name={hasEnded ? 'reload' : isPlaying ? 'pause' : 'play'}
                size={34}
                color="#fff"
                style={{ marginLeft: (!isPlaying && !hasEnded) ? 4 : 0 }}
              />
            </Pressable>

            {/* +10s Forward */}
            <Pressable
              onPress={() => seekByRelative(10)}
              style={styles.skipButton}
              hitSlop={10}
            >
              <Ionicons name="play-forward" size={24} color="#fff" />
              <AppText variant="mono" size={9} color="#fff" style={{ marginTop: 2, fontWeight: '700' }}>
                +10s
              </AppText>
            </Pressable>
          </View>

          {/* Bottom Controls Bar (Timeline & Timers) */}
          <LinearGradient
            colors={['transparent', 'rgba(0,0,0,0.85)']}
            style={styles.bottomGradientBar}
          >
            <View style={styles.timelineRow}>
              {/* Current Time */}
              <AppText variant="mono" size={11} color="#fff" style={styles.timeText}>
                {formatTime(activeTime)}
              </AppText>

              {/* Scrubber Bar Container */}
              <View
                style={styles.scrubberTouchTarget}
                onLayout={onTrackLayout}
                onStartShouldSetResponder={() => true}
                onMoveShouldSetResponder={() => true}
                onResponderGrant={onScrubberGrant}
                onResponderMove={onScrubberMove}
                onResponderRelease={onScrubberRelease}
              >
                {/* Background Track */}
                <View style={styles.scrubberTrackBackground}>
                  {/* Filled Track */}
                  <View
                    style={[
                      styles.scrubberTrackFill,
                      { width: `${progressRatio * 100}%` },
                    ]}
                  />
                </View>

                {/* Thumb Knob */}
                <View
                  style={[
                    styles.scrubberThumb,
                    { left: `${progressRatio * 100}%` },
                    isSeeking && styles.scrubberThumbActive,
                  ]}
                />
              </View>

              {/* Total Duration */}
              <AppText variant="mono" size={11} color="rgba(255,255,255,0.7)" style={styles.timeText}>
                {formatTime(duration)}
              </AppText>
            </View>
          </LinearGradient>
        </Animated.View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    width: '100%',
    height: '100%',
    backgroundColor: '#000',
    justifyContent: 'center',
    alignItems: 'center',
    overflow: 'hidden',
  },
  controlsOverlay: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: 'space-between',
  },
  topGradientBar: {
    paddingTop: Platform.OS === 'ios' ? 44 : 20,
    paddingHorizontal: 20,
    paddingBottom: 25,
  },
  topControlsRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  confidentialBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(224, 108, 108, 0.15)',
    borderWidth: 1,
    borderColor: 'rgba(224, 108, 108, 0.35)',
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 14,
  },
  iconCircleButton: {
    width: 38,
    height: 38,
    borderRadius: 19,
    backgroundColor: 'rgba(0, 0, 0, 0.55)',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.15)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  centerControlsRow: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    gap: 36,
  },
  skipButton: {
    width: 52,
    height: 52,
    borderRadius: 26,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.12)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  mainPlayPauseButton: {
    width: 72,
    height: 72,
    borderRadius: 36,
    backgroundColor: 'rgba(224, 108, 108, 0.85)',
    borderWidth: 2,
    borderColor: 'rgba(255, 255, 255, 0.3)',
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#E06C6C',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.45,
    shadowRadius: 10,
    elevation: 8,
  },
  bottomGradientBar: {
    paddingHorizontal: 16,
    paddingTop: 30,
    paddingBottom: Platform.OS === 'ios' ? 40 : 25,
  },
  timelineRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  timeText: {
    minWidth: 46,
    textAlign: 'center',
    letterSpacing: 0.5,
  },
  scrubberTouchTarget: {
    flex: 1,
    height: 34,
    justifyContent: 'center',
    marginHorizontal: 10,
    position: 'relative',
  },
  scrubberTrackBackground: {
    height: 4,
    borderRadius: 2,
    backgroundColor: 'rgba(255, 255, 255, 0.25)',
    overflow: 'hidden',
    width: '100%',
  },
  scrubberTrackFill: {
    height: '100%',
    backgroundColor: '#E06C6C',
    borderRadius: 2,
  },
  scrubberThumb: {
    position: 'absolute',
    top: 10,
    width: 14,
    height: 14,
    borderRadius: 7,
    backgroundColor: '#fff',
    marginLeft: -7,
    borderWidth: 2,
    borderColor: '#E06C6C',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.5,
    shadowRadius: 3,
    elevation: 4,
  },
  scrubberThumbActive: {
    transform: [{ scale: 1.35 }],
    backgroundColor: '#E8B4A0',
  },
  bufferingContainer: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(0, 0, 0, 0.45)',
  },
  errorContainer: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(0, 0, 0, 0.85)',
    paddingHorizontal: 30,
  },
  retryButton: {
    marginTop: 16,
    backgroundColor: '#E06C6C',
    paddingHorizontal: 20,
    paddingVertical: 8,
    borderRadius: 16,
  },
  seekFeedbackOverlay: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: 'center',
    alignItems: 'center',
  },
  seekFeedbackPill: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(0, 0, 0, 0.75)',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.2)',
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 20,
  },
});
