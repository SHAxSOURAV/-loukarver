import React, { useRef, useEffect, useMemo } from 'react';
import { View, StyleSheet, ActivityIndicator, Platform } from 'react-native';
import { WebView } from 'react-native-webview';
import { Colors } from '../../constants/colors';
import { AppText } from '../ui/AppText';
import { MapPin } from '../../types';

interface UIMapPin extends MapPin {
  creator_name?: string;
  moments?: any[];
  deletion_request?: any;
}

interface InteractiveLeafletMapProps {
  places: UIMapPin[];
  routes?: any[];
  selectedPin?: UIMapPin | null;
  onSelectPin?: (pin: UIMapPin) => void;
  onMapLongPress?: (coords: { lat: number; lng: number }) => void;
  clearTempPinTrigger?: number;
  activeFilter?: string;
  style?: any;
  showLegend?: boolean;
  focusLocation?: { lat: number; lng: number; zoom?: number } | null;
  userLocation?: { lat: number; lng: number } | null;
  resetCompassTrigger?: number;
}

const PIN_COLORS: Record<string, string> = {
  home: '#8B7355',
  together: '#C05640',
  upcoming: '#6E8B74',
  bucket: '#A89E8D',
};

export const InteractiveLeafletMap: React.FC<InteractiveLeafletMapProps> = ({
  places,
  routes = [],
  selectedPin,
  onSelectPin,
  onMapLongPress,
  clearTempPinTrigger,
  activeFilter = 'all',
  style,
  showLegend = false,
  focusLocation,
  userLocation,
  resetCompassTrigger,
}) => {
  const webViewRef = useRef<WebView>(null);
  const maptilerApiKey = process.env.EXPO_PUBLIC_MAPTILER_API_KEY || '';

  // Find center coordinates from selected pin or home pin or average
  const initialCenter = useMemo(() => {
    if (selectedPin && selectedPin.lat && selectedPin.lng) {
      return { lat: selectedPin.lat, lng: selectedPin.lng, zoom: 5 };
    }
    const validPlaces = places.filter(p => p.lat != null && p.lng != null && (p.lat !== 0 || p.lng !== 0));
    if (validPlaces.length > 0) {
      const homePin = validPlaces.find(p => p.type === 'home');
      if (homePin) return { lat: homePin.lat, lng: homePin.lng, zoom: 4 };
      return { lat: validPlaces[0].lat, lng: validPlaces[0].lng, zoom: 4 };
    }
    // Default world center
    return { lat: 25.0, lng: 15.0, zoom: 2 };
  }, []);

  // HTML + Leaflet CSS/JS bundle template
  const mapHtml = useMemo(() => {
    const validPlaces = places.filter(p => p.lat != null && p.lng != null && (p.lat !== 0 || p.lng !== 0));
    const serializedPlaces = JSON.stringify(validPlaces);
    const serializedSelectedId = JSON.stringify(selectedPin?.id || null);

    return `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
    html, body, #map { width: 100%; height: 100%; background: #F7F3EC; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    
    /* Luxury Pin Styling */
    .pin-marker {
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      transition: transform 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    }
    .pin-core {
      width: 24px;
      height: 24px;
      border-radius: 50%;
      background: #FFFFFF;
      border: 3.5px solid #C05640;
      box-shadow: 0 4px 10px rgba(0,0,0,0.22);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 10px;
      font-weight: 700;
      color: #1C1C1E;
    }
    .pin-pulse {
      position: absolute;
      width: 40px;
      height: 40px;
      border-radius: 50%;
      background: rgba(192, 86, 64, 0.25);
      animation: pulse 2s infinite ease-out;
      pointer-events: none;
    }
    @keyframes pulse {
      0% { transform: scale(0.6); opacity: 0.8; }
      100% { transform: scale(1.4); opacity: 0; }
    }
    .pin-selected .pin-core {
      transform: scale(1.25);
      border-width: 4px;
      box-shadow: 0 6px 14px rgba(192, 86, 64, 0.45);
    }

    /* Trajectory curve styling */
    .flight-arc {
      stroke: #C05640;
      stroke-width: 2.5;
      stroke-dasharray: 6, 6;
      stroke-linecap: round;
      fill: none;
      opacity: 0.85;
      animation: dash 30s linear infinite;
    }
    @keyframes dash {
      to { stroke-dashoffset: -1000; }
    }

    /* Live Location Radar Marker */
    .live-location-wrap {
      position: relative;
      width: 24px;
      height: 24px;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .live-location-dot {
      width: 14px;
      height: 14px;
      border-radius: 50%;
      background: #2A6BF2;
      border: 3px solid #FFFFFF;
      box-shadow: 0 2px 8px rgba(42, 107, 242, 0.45);
    }
    .live-location-pulse {
      position: absolute;
      width: 36px;
      height: 36px;
      border-radius: 50%;
      background: rgba(42, 107, 242, 0.3);
      animation: livePulse 2s infinite ease-out;
      pointer-events: none;
    }
    @keyframes livePulse {
      0% { transform: scale(0.5); opacity: 0.9; }
      100% { transform: scale(1.6); opacity: 0; }
    }

    /* Minimalist Map Controls */
    .leaflet-bottom.leaflet-left {
      bottom: 80px !important;
      left: 16px !important;
    }
    .leaflet-bottom.leaflet-right {
      bottom: 6px !important;
      right: 6px !important;
    }
    .leaflet-control-zoom {
      border: 1px solid #E6E0D4 !important;
      border-radius: 12px !important;
      overflow: hidden;
      box-shadow: 0 4px 12px rgba(0,0,0,0.1) !important;
    }
    .leaflet-control-zoom a {
      background: rgba(247, 243, 236, 0.95) !important;
      color: #2C221E !important;
      border-bottom: 1px solid #E6E0D4 !important;
      width: 34px !important;
      height: 34px !important;
      line-height: 34px !important;
      font-size: 16px !important;
    }
    .leaflet-control-attribution {
      font-size: 8px !important;
      background: rgba(247, 243, 236, 0.8) !important;
      color: #8C7F75 !important;
    }
  </style>
</head>
<body>
  <div id="map"></div>

  <script>
    const placesData = ${serializedPlaces};
    const routesData = ${JSON.stringify(routes)};
    let selectedId = ${serializedSelectedId};
    let currentFilter = "${activeFilter}";
    const pinColors = ${JSON.stringify(PIN_COLORS)};
    const apiKey = "${maptilerApiKey}";

    // 1. Initialize Map
    const map = L.map('map', {
      center: [${initialCenter.lat}, ${initialCenter.lng}],
      zoom: ${initialCenter.zoom},
      minZoom: 2,
      maxZoom: 17,
      zoomControl: false,
      attributionControl: true
    });
    L.control.zoom({ position: 'bottomleft' }).addTo(map);

    setTimeout(function() {
      map.invalidateSize();
    }, 250);

    // 2. MapTiler Pastel Luxury Tile Layer (With Fallback)
    const maptilerUrl = 'https://api.maptiler.com/maps/pastel/256/{z}/{x}/{y}.png?key=' + apiKey;
    const fallbackUrl = 'https://cartodb-basemaps-a.global.ssl.fastly.net/light_all/{z}/{x}/{y}.png';

    const tileLayer = L.tileLayer(apiKey ? maptilerUrl : fallbackUrl, {
      maxZoom: 18,
      attribution: '<a href="https://www.maptiler.com/copyright/" target="_blank">&copy; MapTiler</a> &copy; OpenStreetMap'
    }).addTo(map);

    tileLayer.on('tileerror', function() {
      if (tileLayer._url !== fallbackUrl) {
        tileLayer.setUrl(fallbackUrl);
      }
    });

    const markerMap = {};
    const arcLayerGroup = L.layerGroup().addTo(map);
    const markerLayerGroup = L.layerGroup().addTo(map);

    function createMarkerIcon(place, isSelected) {
      const color = pinColors[place.type] || '#C05640';
      const initial = (place.city || '?').charAt(0).toUpperCase();
      const pulseHtml = (place.type === 'together' || isSelected) ? '<div class="pin-pulse" style="background: ' + color + '33;"></div>' : '';

      return L.divIcon({
        className: 'custom-pin-wrap',
        html: '<div class="pin-marker ' + (isSelected ? 'pin-selected' : '') + '">' +
                pulseHtml +
                '<div class="pin-core" style="border-color: ' + color + '; color: ' + color + ';">' + initial + '</div>' +
              '</div>',
        iconSize: [30, 30],
        iconAnchor: [15, 15]
      });
    }

    function getCurvedPoints(start, end) {
      const lat1 = start[0], lng1 = start[1];
      const lat2 = end[0], lng2 = end[1];

      const dLat = lat2 - lat1;
      let dLng = lng2 - lng1;

      // Handle antimeridian wrapping
      if (dLng > 180) dLng -= 360;
      if (dLng < -180) dLng += 360;

      const dist = Math.sqrt(dLat * dLat + dLng * dLng);
      if (dist < 0.001) return [[lat1, lng1], [lat2, lng2]];

      const midLat = (lat1 + lat2) / 2;
      const midLng = (lng1 + lng2) / 2;

      // Perpendicular normal in geographic plane (X=lng, Y=lat)
      let perpLng = -dLat / dist;
      let perpLat = dLng / dist;

      // Arc towards the pole (North in northern hemisphere)
      if (midLat >= 0) {
        if (perpLat < 0) {
          perpLat = -perpLat;
          perpLng = -perpLng;
        }
      } else {
        if (perpLat > 0) {
          perpLat = -perpLat;
          perpLng = -perpLng;
        }
      }

      // If nearly pure North-South flight, gently bow eastward
      if (Math.abs(perpLat) < 0.15) {
        perpLng = 0.7;
      }

      // Subtle, elegant arch
      const curvature = Math.min(dist * 0.15, 8);
      const controlLat = midLat + perpLat * curvature;
      const controlLng = midLng + perpLng * curvature;

      const points = [];
      const steps = 36;
      for (let i = 0; i <= steps; i++) {
        const t = i / steps;
        const oneMinusT = 1 - t;
        const lat = oneMinusT * oneMinusT * lat1 + 2 * oneMinusT * t * controlLat + t * t * lat2;
        const lng = oneMinusT * oneMinusT * lng1 + 2 * oneMinusT * t * controlLng + t * t * lng2;
        points.push([lat, lng]);
      }
      return points;
    }

    function renderPinsAndArcs() {
      markerLayerGroup.clearLayers();
      arcLayerGroup.clearLayers();

      const homePin = placesData.find(p => p.type === 'home') || placesData[0];

      placesData.forEach(place => {
        if (place.lat == null || place.lng == null || (place.lat === 0 && place.lng === 0)) return;
        if (currentFilter !== 'all' && place.type !== currentFilter) return;

        const isSelected = selectedId === place.id;
        const marker = L.marker([place.lat, place.lng], {
          icon: createMarkerIcon(place, isSelected),
          zIndexOffset: isSelected ? 1000 : 0
        });

        marker.on('click', () => {
          selectedId = place.id;
          renderPinsAndArcs();
          map.flyTo([place.lat, place.lng], Math.max(map.getZoom(), 5), { duration: 0.8 });
          if (window.ReactNativeWebView) {
            window.ReactNativeWebView.postMessage(JSON.stringify({
              type: 'PIN_SELECTED',
              placeId: place.id
            }));
          }
        });

        markerLayerGroup.addLayer(marker);
        markerMap[place.id] = marker;
      });

      // 1. Draw Journey Routes if available
      let hasRouteArcs = false;
      if (routesData && routesData.length > 0) {
        routesData.forEach(route => {
          if (route.points && route.points.length > 1) {
            for (let i = 0; i < route.points.length - 1; i++) {
              const p1 = route.points[i];
              const p2 = route.points[i + 1];
              if (p1.lat != null && p1.lng != null && p2.lat != null && p2.lng != null) {
                const arcPoints = getCurvedPoints([p1.lat, p1.lng], [p2.lat, p2.lng]);
                const arcPolyline = L.polyline(arcPoints, {
                  className: 'flight-arc',
                  color: '#C05640'
                });
                arcLayerGroup.addLayer(arcPolyline);
                hasRouteArcs = true;
              }
            }
          }
        });
      }

      // 2. Draw arcs from homePin to destinations if no routes were drawn
      if (!hasRouteArcs && homePin) {
        placesData.forEach(place => {
          if (place.lat == null || place.lng == null || (place.lat === 0 && place.lng === 0)) return;
          if (currentFilter !== 'all' && place.type !== currentFilter) return;
          if (homePin.id !== place.id && (place.type === 'together' || place.type === 'upcoming')) {
            const arcPoints = getCurvedPoints([homePin.lat, homePin.lng], [place.lat, place.lng]);
            const arcPolyline = L.polyline(arcPoints, {
              className: 'flight-arc',
              color: pinColors[place.type] || '#C05640'
            });
            arcLayerGroup.addLayer(arcPolyline);
          }
        });
      }
    }

    renderPinsAndArcs();

    let longPressTimer = null;
    let touchStartPoint = null;
    let didTriggerLongPress = false;

    function clearLongPress() {
      if (longPressTimer) {
        clearTimeout(longPressTimer);
        longPressTimer = null;
      }
    }

    function triggerLongPress(lat, lng) {
      clearLongPress();
      didTriggerLongPress = true;

      // Drop a temporary pulse marker at the clicked location
      if (window.tempDropPin) {
        map.removeLayer(window.tempDropPin);
      }
      const dropIcon = L.divIcon({
        className: 'temp-drop-pin-wrap',
        html: '<div class="pin-marker pin-selected"><div class="pin-pulse" style="background: rgba(192, 86, 64, 0.45);"></div><div class="pin-core" style="border-color: #C05640; color: #C05640; font-size: 13px;">📍</div></div>',
        iconSize: [30, 30],
        iconAnchor: [15, 15]
      });
      window.tempDropPin = L.marker([lat, lng], { icon: dropIcon, zIndexOffset: 3000 }).addTo(map);

      if (window.ReactNativeWebView) {
        window.ReactNativeWebView.postMessage(JSON.stringify({
          type: 'MAP_LONG_PRESS',
          lat: lat,
          lng: lng
        }));
      }
    }

    window.clearTempDropPin = function() {
      if (window.tempDropPin) {
        map.removeLayer(window.tempDropPin);
        window.tempDropPin = null;
      }
    };

    map.on('mousedown touchstart', function(e) {
      didTriggerLongPress = false;
      clearLongPress();
      if (!e.latlng) return;
      const originalEvent = e.originalEvent;
      const touch = (originalEvent.touches && originalEvent.touches[0]) || originalEvent;
      touchStartPoint = { x: touch.clientX, y: touch.clientY, lat: e.latlng.lat, lng: e.latlng.lng };

      longPressTimer = setTimeout(function() {
        triggerLongPress(touchStartPoint.lat, touchStartPoint.lng);
      }, 500);
    });

    map.on('mousemove touchmove', function(e) {
      if (touchStartPoint && longPressTimer) {
        const originalEvent = e.originalEvent;
        const touch = (originalEvent.touches && originalEvent.touches[0]) || originalEvent;
        const dx = touch.clientX - touchStartPoint.x;
        const dy = touch.clientY - touchStartPoint.y;
        if (Math.sqrt(dx * dx + dy * dy) > 8) {
          clearLongPress();
        }
      }
    });

    map.on('mouseup touchend touchcancel dragstart movestart zoomstart', function() {
      clearLongPress();
    });

    map.on('contextmenu', function(e) {
      if (e.latlng && !didTriggerLongPress) {
        triggerLongPress(e.latlng.lat, e.latlng.lng);
      }
    });

    map.on('click', function(e) {
      if (didTriggerLongPress) {
        didTriggerLongPress = false;
        return;
      }
      if (window.ReactNativeWebView) {
        window.ReactNativeWebView.postMessage(JSON.stringify({
          type: 'MAP_CLICKED',
          lat: e.latlng.lat,
          lng: e.latlng.lng
        }));
      }
    });

    window.updateSelectedPin = function(pinId, lat, lng) {
      selectedId = pinId;
      renderPinsAndArcs();
      if (lat != null && lng != null && (lat !== 0 || lng !== 0)) {
        map.flyTo([lat, lng], Math.max(map.getZoom(), 6), { duration: 0.9 });
      }
    };

    window.flyToLocation = function(lat, lng, zoom) {
      if (window.searchMarker) {
        map.removeLayer(window.searchMarker);
      }
      map.flyTo([lat, lng], zoom || 10, { duration: 1.1 });
      const pulseIcon = L.divIcon({
        className: 'search-target-pin',
        html: '<div class="pin-marker pin-selected"><div class="pin-pulse" style="background: rgba(192, 86, 64, 0.45);"></div><div class="pin-core" style="border-color: #C05640; color: #C05640; font-size: 13px;">📍</div></div>',
        iconSize: [30, 30],
        iconAnchor: [15, 15]
      });
      window.searchMarker = L.marker([lat, lng], { icon: pulseIcon }).addTo(map);
    };

    window.showUserLiveLocation = function(lat, lng) {
      if (window.userLocationMarker) {
        map.removeLayer(window.userLocationMarker);
      }
      map.flyTo([lat, lng], 14, { duration: 1.2 });
      const liveIcon = L.divIcon({
        className: 'user-live-location-pin',
        html: '<div class="live-location-wrap"><div class="live-location-pulse"></div><div class="live-location-dot"></div></div>',
        iconSize: [24, 24],
        iconAnchor: [12, 12]
      });
      window.userLocationMarker = L.marker([lat, lng], { icon: liveIcon, zIndexOffset: 2000 }).addTo(map);
    };

    window.resetCompassView = function() {
      const validPins = placesData.filter(p => p.lat != null && p.lng != null && (p.lat !== 0 || p.lng !== 0));
      if (validPins.length > 1) {
        const bounds = L.latLngBounds(validPins.map(p => [p.lat, p.lng]));
        map.flyToBounds(bounds, { padding: [60, 60], duration: 1.1 });
      } else if (validPins.length === 1) {
        map.flyTo([validPins[0].lat, validPins[0].lng], 5, { duration: 1.0 });
      } else {
        map.flyTo([25.0, 15.0], 2, { duration: 1.0 });
      }
    };

    window.updateFilter = function(filter) {
      currentFilter = filter;
      renderPinsAndArcs();
    };
  </script>
</body>
</html>
    `;
  }, [places, routes, maptilerApiKey]);

  useEffect(() => {
    if (selectedPin && selectedPin.lat != null && selectedPin.lng != null) {
      const code = `if (window.updateSelectedPin) { window.updateSelectedPin(${JSON.stringify(selectedPin.id)}, ${selectedPin.lat}, ${selectedPin.lng}); }`;
      webViewRef.current?.injectJavaScript(code);
    }
  }, [selectedPin]);

  useEffect(() => {
    if (focusLocation && focusLocation.lat != null && focusLocation.lng != null) {
      const zoom = focusLocation.zoom || 10;
      const code = `if (window.flyToLocation) { window.flyToLocation(${focusLocation.lat}, ${focusLocation.lng}, ${zoom}); }`;
      webViewRef.current?.injectJavaScript(code);
    }
  }, [focusLocation]);

  useEffect(() => {
    if (userLocation && userLocation.lat != null && userLocation.lng != null) {
      const code = `if (window.showUserLiveLocation) { window.showUserLiveLocation(${userLocation.lat}, ${userLocation.lng}); }`;
      webViewRef.current?.injectJavaScript(code);
    }
  }, [userLocation]);

  useEffect(() => {
    if (resetCompassTrigger) {
      const code = `if (window.resetCompassView) { window.resetCompassView(); }`;
      webViewRef.current?.injectJavaScript(code);
    }
  }, [resetCompassTrigger]);

  useEffect(() => {
    const code = `if (window.updateFilter) { window.updateFilter(${JSON.stringify(activeFilter)}); }`;
    webViewRef.current?.injectJavaScript(code);
  }, [activeFilter]);

  useEffect(() => {
    if (clearTempPinTrigger) {
      webViewRef.current?.injectJavaScript(`if (window.clearTempDropPin) { window.clearTempDropPin(); }`);
    }
  }, [clearTempPinTrigger]);

  const handleMessage = (event: any) => {
    try {
      const data = JSON.parse(event.nativeEvent.data);
      if (data.type === 'PIN_SELECTED' && onSelectPin) {
        const found = places.find(p => p.id === data.placeId);
        if (found) {
          onSelectPin(found);
        }
      } else if (data.type === 'MAP_LONG_PRESS' && onMapLongPress) {
        onMapLongPress({ lat: data.lat, lng: data.lng });
      }
    } catch (e) {
      console.error('Leaflet WebView message error:', e);
    }
  };

  return (
    <View style={[styles.container, style]}>
      <WebView
        ref={webViewRef}
        originWhitelist={['*']}
        source={{ html: mapHtml }}
        style={styles.webView}
        javaScriptEnabled={true}
        domStorageEnabled={true}
        scalesPageToFit={Platform.OS === 'android'}
        scrollEnabled={false}
        overScrollMode="never"
        bounces={false}
        onMessage={handleMessage}
        renderLoading={() => (
          <View style={styles.loadingContainer}>
            <ActivityIndicator size="small" color={Colors.accent} />
          </View>
        )}
      />

      {/* Optional Map Legend */}
      {showLegend && (
        <View style={styles.legendBar}>
          <View style={styles.legendItem}>
            <View style={[styles.legendDot, { backgroundColor: PIN_COLORS.home }]} />
            <AppText variant="mono" style={styles.legendText}>HOME</AppText>
          </View>
          <View style={styles.legendItem}>
            <View style={[styles.legendDot, { backgroundColor: PIN_COLORS.together }]} />
            <AppText variant="mono" style={styles.legendText}>TOGETHER</AppText>
          </View>
          <View style={styles.legendItem}>
            <View style={[styles.legendDot, { backgroundColor: PIN_COLORS.upcoming }]} />
            <AppText variant="mono" style={styles.legendText}>UPCOMING</AppText>
          </View>
          <View style={styles.legendItem}>
            <View style={[styles.legendDot, { backgroundColor: PIN_COLORS.bucket }]} />
            <AppText variant="mono" style={styles.legendText}>BUCKET</AppText>
          </View>
        </View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    width: '100%',
    height: '100%',
    backgroundColor: '#F7F3EC',
    overflow: 'hidden',
  },
  webView: {
    flex: 1,
    backgroundColor: 'transparent',
  },
  loadingContainer: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#F7F3EC',
  },
  legendBar: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    alignItems: 'center',
    paddingVertical: 10,
    paddingHorizontal: 16,
    backgroundColor: '#F7F3EC',
    borderTopWidth: 1,
    borderTopColor: Colors.rule,
  },
  legendItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  legendDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  legendText: {
    fontSize: 9,
    color: Colors.muted,
    letterSpacing: 0.5,
  },
});
