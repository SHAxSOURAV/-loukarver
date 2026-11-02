import React from 'react';
import { View, StyleSheet, Pressable, Dimensions } from 'react-native';
import Svg, { Path, Circle, G, Line, Rect, Text as SvgText } from 'react-native-svg';
import { Colors } from '../../constants/colors';
import { AppText } from '../ui/AppText';
import { MapPin } from '../../types';

interface WorldMapSvgProps {
  places: MapPin[];
  selectedPin?: MapPin | null;
  onSelectPin?: (pin: MapPin) => void;
}

const MAP_WIDTH = 1000;
const MAP_HEIGHT = 500;

// Projection helper: maps lat (-90..90) & lng (-180..180) to SVG canvas (1000x500)
export function projectCoordinates(lat: number, lng: number): { x: number; y: number } {
  // Longitude: -180 to 180 => 0 to 1000
  const x = ((lng + 180) / 360) * MAP_WIDTH;
  
  // Latitude: Mercator projection clipped to -75..75
  const clampedLat = Math.max(-75, Math.min(75, lat));
  const latRad = (clampedLat * Math.PI) / 180;
  const mercN = Math.log(Math.tan(Math.PI / 4 + latRad / 2));
  // Offsets and scales for 1000x500 canvas
  const y = MAP_HEIGHT / 2 - (MAP_WIDTH * mercN) / (2 * Math.PI) * 0.85 + 20;

  return {
    x: Math.max(20, Math.min(MAP_WIDTH - 20, x)),
    y: Math.max(20, Math.min(MAP_HEIGHT - 20, y))
  };
}

// Minimalist Continent SVG Paths matching warm organic luxury aesthetic
const CONTINENTS = [
  // North America
  {
    d: "M 140,75 C 170,60 260,50 320,65 C 340,90 320,130 300,160 C 270,180 250,220 220,250 C 190,260 170,220 150,200 C 130,170 100,150 90,120 Z",
  },
  // Greenland
  {
    d: "M 320,30 C 350,20 400,25 410,50 C 400,80 360,90 330,75 Z",
  },
  // South America
  {
    d: "M 250,270 C 290,260 350,300 360,340 C 350,400 310,470 280,480 C 260,460 250,390 240,340 C 230,300 240,280 250,270 Z",
  },
  // Europe & UK
  {
    d: "M 480,100 C 530,80 600,90 620,120 C 590,150 560,170 510,160 C 480,150 470,120 480,100 Z",
  },
  // Africa
  {
    d: "M 470,180 C 540,170 610,220 620,280 C 600,340 560,420 520,410 C 480,390 460,300 450,240 Z",
  },
  // Asia
  {
    d: "M 620,80 C 720,50 870,70 910,120 C 890,200 820,260 760,250 C 700,240 640,180 620,80 Z",
  },
  // Australia & Oceania
  {
    d: "M 780,330 C 860,320 900,360 890,420 C 840,440 790,430 770,390 Z",
  }
];

const PIN_COLORS = {
  home: '#8B7355',
  together: '#C05640',
  upcoming: '#6E8B74',
  bucket: '#D3C9B8',
};

export const WorldMapSvg: React.FC<WorldMapSvgProps> = ({ places, selectedPin, onSelectPin }) => {
  // Find Home & Together pins for trajectory arc calculation
  const homePin = places.find(p => p.type === 'home') || places[0];
  const togetherPins = places.filter(p => (p.type === 'together' || p.type === 'upcoming') && p.id !== homePin?.id);

  // Generate Trajectory Arcs
  const arcs = togetherPins.map(targetPin => {
    if (!homePin || !targetPin.lat || !targetPin.lng) return null;
    const start = projectCoordinates(homePin.lat, homePin.lng);
    const end = projectCoordinates(targetPin.lat, targetPin.lng);

    // Control point for smooth curved Bezier arc
    const midX = (start.x + end.x) / 2;
    const midY = (start.y + end.y) / 2 - 50; // curve upwards

    const pathData = `M ${start.x} ${start.y} Q ${midX} ${midY} ${end.x} ${end.y}`;
    
    // City initials label (e.g. L -> A)
    const startInitial = (homePin.city || 'H').charAt(0).toUpperCase();
    const endInitial = (targetPin.city || 'T').charAt(0).toUpperCase();
    const label = `- - - ${startInitial} → ${endInitial}`;

    return { id: targetPin.id, pathData, label, start, end };
  }).filter(Boolean);

  const activeLabel = arcs.length > 0 ? arcs[0]?.label : null;

  return (
    <View style={styles.container}>
      <View style={styles.svgWrapper}>
        <Svg viewBox={`0 0 ${MAP_WIDTH} ${MAP_HEIGHT}`} style={styles.svg}>
          {/* Map Background Canvas */}
          <Rect x="0" y="0" width={MAP_WIDTH} height={MAP_HEIGHT} fill="#F7F3EC" rx="16" />

          {/* Dotted Grid Lines */}
          <Line x1="0" y1="250" x2="1000" y2="250" stroke="#E6E0D4" strokeDasharray="3 3" strokeWidth="1" />
          <Line x1="500" y1="0" x2="500" y2="500" stroke="#E6E0D4" strokeDasharray="3 3" strokeWidth="1" />

          {/* Continents */}
          {CONTINENTS.map((c, i) => (
            <Path
              key={i}
              d={c.d}
              fill="#EAE3D6"
              stroke="#D8CFBE"
              strokeWidth="1.5"
              strokeLinejoin="round"
            />
          ))}

          {/* Trajectory Arcs */}
          {arcs.map((arc, i) => arc && (
            <G key={`arc-${i}`}>
              <Path
                d={arc.pathData}
                fill="none"
                stroke={Colors.accent}
                strokeWidth="2.5"
                strokeDasharray="6 4"
                opacity={0.85}
              />
            </G>
          ))}

          {/* Dynamic Map Pins */}
          {places.map((place) => {
            if (place.lat == null || place.lng == null) return null;
            const { x, y } = projectCoordinates(place.lat, place.lng);
            const isSelected = selectedPin?.id === place.id;
            const pinColor = PIN_COLORS[place.type] || Colors.accent;

            return (
              <G
                key={place.id}
                onPress={() => onSelectPin && onSelectPin(place)}
              >
                {/* Hit Area */}
                <Circle cx={x} cy={y} r="20" fill="transparent" />

                {/* Pulse Ring for Selected */}
                {isSelected && (
                  <Circle
                    cx={x}
                    cy={y}
                    r="14"
                    fill="none"
                    stroke={pinColor}
                    strokeWidth="2"
                    opacity={0.5}
                  />
                )}

                {/* Outer Ring */}
                <Circle
                  cx={x}
                  cy={y}
                  r="7"
                  fill="#FFF"
                  stroke={pinColor}
                  strokeWidth="2.5"
                />

                {/* Inner Core Dot */}
                <Circle
                  cx={x}
                  cy={y}
                  r="3.5"
                  fill={pinColor}
                />
              </G>
            );
          })}
        </Svg>
      </View>

      {/* Legend & Route Footer */}
      <View style={styles.legendContainer}>
        <View style={styles.legendRow}>
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

        {activeLabel && (
          <AppText variant="mono" style={styles.routeText}>
            {activeLabel}
          </AppText>
        )}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: '#F5F0E8',
    borderRadius: 20,
    borderWidth: 1,
    borderColor: Colors.rule,
    overflow: 'hidden',
    marginBottom: 20,
  },
  svgWrapper: {
    width: '100%',
    aspectRatio: 2, // 1000x500 standard ratio
    backgroundColor: '#F7F3EC',
  },
  svg: {
    width: '100%',
    height: '100%',
  },
  legendContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderTopWidth: 1,
    borderTopColor: Colors.rule,
    backgroundColor: '#FAF7F2',
  },
  legendRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  legendItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
  },
  legendDot: {
    width: 7,
    height: 7,
    borderRadius: 3.5,
  },
  legendText: {
    fontSize: 9,
    color: Colors.muted,
    letterSpacing: 0.8,
  },
  routeText: {
    fontSize: 10,
    color: Colors.accent,
    letterSpacing: 1,
  },
});
