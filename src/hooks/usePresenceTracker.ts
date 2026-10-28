import { useEffect, useRef } from 'react';
import { AppState, DeviceEventEmitter } from 'react-native';
import * as Location from 'expo-location';
import { logPresence } from '../services/notificationApi';

export const usePresenceTracker = () => {
  const appState = useRef(AppState.currentState);
  const lastTrackedAt = useRef<number>(0);
  const isTracking = useRef<boolean>(false);

  const trackPresence = async (force = false) => {
    const now = Date.now();
    if (isTracking.current) return;
    // Throttle to once every 2 minutes unless explicitly forced
    if (!force && now - lastTrackedAt.current < 2 * 60 * 1000) {
      return;
    }

    isTracking.current = true;
    try {
      let latitude: number | null = null;
      let longitude: number | null = null;
      let city: string | null = null;

      try {
        // Check current permission status
        let perm = await Location.getForegroundPermissionsAsync();
        let status = perm.status;

        // If not granted, request permission
        if (status !== 'granted') {
          if (perm.canAskAgain) {
            const req = await Location.requestForegroundPermissionsAsync();
            status = req.status;
          }
        }

        if (status === 'granted') {
          // 1. Get fast last known position first (instant fallback)
          let location = await Location.getLastKnownPositionAsync().catch(() => null);

          // 2. Fetch fresh high-accuracy position with safe 6s timeout
          const freshLocation = await Promise.race([
            Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.High }),
            new Promise<null>((resolve) => setTimeout(() => resolve(null), 6000)),
          ]).catch(() => null);

          if (freshLocation && freshLocation.coords) {
            location = freshLocation;
          }

          if (location && location.coords) {
            latitude = location.coords.latitude;
            longitude = location.coords.longitude;

            try {
              const reverseGeocode = await Promise.race([
                Location.reverseGeocodeAsync({ latitude, longitude }),
                new Promise<null>((resolve) => setTimeout(() => resolve(null), 4000)),
              ]).catch(() => null);

              if (reverseGeocode && reverseGeocode.length > 0) {
                const place = reverseGeocode[0];
                city =
                  place.city ||
                  place.subregion ||
                  place.district ||
                  place.region ||
                  place.name ||
                  null;
              }
            } catch (e) {
              console.log('Reverse geocode error:', e);
            }
          }
        } else {
          DeviceEventEmitter.emit('LOCATION_PERMISSION_STATUS', { granted: false, canAskAgain: perm.canAskAgain });
        }
      } catch (locErr) {
        console.log('Location tracking error:', locErr);
      }

      let timezone = 'UTC';
      try {
        timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
      } catch (e) {
        timezone = 'UTC';
      }

      await logPresence({
        timezone,
        latitude,
        longitude,
        city,
      });

      lastTrackedAt.current = Date.now();
      // Notify components to refresh with the newly logged city and timezone
      DeviceEventEmitter.emit('PRESENCE_TRACKED', { city, timezone });
    } catch (e) {
      console.log('Failed to track presence:', e);
    } finally {
      isTracking.current = false;
    }
  };

  useEffect(() => {
    // Track immediately on mount
    trackPresence(true);

    // Track every 4 minutes while the app is active
    const interval = setInterval(() => {
      if (AppState.currentState === 'active') {
        trackPresence();
      }
    }, 4 * 60 * 1000);

    // Track on app resume
    const subscription = AppState.addEventListener('change', (nextAppState) => {
      if (appState.current.match(/inactive|background/) && nextAppState === 'active') {
        trackPresence(true);
      }
      appState.current = nextAppState;
    });

    // Support explicit re-tracking triggered from UI (e.g. pull-to-refresh)
    const subEvent = DeviceEventEmitter.addListener('TRACK_LOCATION_NOW', () => {
      trackPresence(true);
    });

    return () => {
      clearInterval(interval);
      subscription.remove();
      subEvent.remove();
    };
  }, []);
};
