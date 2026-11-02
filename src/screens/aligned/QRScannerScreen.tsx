import React, { useEffect } from 'react';
import { View, StyleSheet, Platform, Pressable, DeviceEventEmitter } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useNavigation, useRoute } from '@react-navigation/native';
import { AppText } from '../../components/ui/AppText';
import { Colors } from '../../constants/colors';
import { Ionicons } from '@expo/vector-icons';

let CameraView: any = null;
let useCameraPermissions: any = () => [null, async () => {}];
if (Platform.OS !== 'web') {
  const ExpoCamera = require('expo-camera');
  CameraView = ExpoCamera.CameraView;
  useCameraPermissions = ExpoCamera.useCameraPermissions;
}

export const QRScannerScreen = () => {
  const nav = useNavigation();
  const route = useRoute<any>();
  const [permission, requestPermission] = useCameraPermissions();
  const [scanned, setScanned] = React.useState(false);

  useEffect(() => {
    if (!permission?.granted) {
      requestPermission();
    }
  }, [permission]);

  const handleScan = ({ data }: any) => {
    if (scanned) return;
    setScanned(true);
    DeviceEventEmitter.emit('QR_CODE_SCANNED', data);
    if (route.params?.onScan && typeof route.params.onScan === 'function') {
      route.params.onScan(data);
    }
    nav.goBack();
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: '#000' }}>
      <View style={{ flex: 1 }}>
        <Pressable onPress={() => nav.goBack()} style={styles.closeBtn}>
          <Ionicons name="close" size={32} color="#fff" />
        </Pressable>
        
        {Platform.OS === 'web' ? (
          <AppText color={Colors.muted} style={{ textAlign: 'center', marginTop: 100 }}>
            Camera not supported on web.
          </AppText>
        ) : !permission ? (
          <AppText color={Colors.muted} style={{ textAlign: 'center', marginTop: 100 }}>
            Requesting camera permission...
          </AppText>
        ) : !permission.granted ? (
          <AppText color={Colors.muted} style={{ textAlign: 'center', marginTop: 100 }}>
            No access to camera
          </AppText>
        ) : (
          <CameraView
            style={StyleSheet.absoluteFillObject}
            barcodeScannerSettings={{ barcodeTypes: ["qr"] }}
            onBarcodeScanned={handleScan}
          />
        )}
        
        {/* Overlay */}
        <View style={styles.overlay}>
          <View style={styles.unfocusedContainer}>
            <AppText variant="serifItalic" size={18} color="#fff" style={{ textAlign: 'center', marginTop: 60 }}>
              Scan your partner's code
            </AppText>
          </View>
          <View style={styles.middleContainer}>
            <View style={styles.unfocusedContainer} />
            <View style={styles.focusedContainer}>
              <View style={[styles.corner, styles.topLeft]} />
              <View style={[styles.corner, styles.topRight]} />
              <View style={[styles.corner, styles.bottomLeft]} />
              <View style={[styles.corner, styles.bottomRight]} />
            </View>
            <View style={styles.unfocusedContainer} />
          </View>
          <View style={styles.unfocusedContainer} />
        </View>
      </View>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  closeBtn: {
    position: 'absolute',
    top: 20,
    right: 20,
    zIndex: 10,
    padding: 10,
  },
  overlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    zIndex: 1,
  },
  unfocusedContainer: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.6)',
  },
  middleContainer: {
    flexDirection: 'row',
    height: 250,
  },
  focusedContainer: {
    width: 250,
    height: 250,
    backgroundColor: 'transparent',
    position: 'relative',
  },
  corner: {
    position: 'absolute',
    width: 30,
    height: 30,
    borderColor: Colors.accent,
  },
  topLeft: {
    top: 0,
    left: 0,
    borderTopWidth: 3,
    borderLeftWidth: 3,
  },
  topRight: {
    top: 0,
    right: 0,
    borderTopWidth: 3,
    borderRightWidth: 3,
  },
  bottomLeft: {
    bottom: 0,
    left: 0,
    borderBottomWidth: 3,
    borderLeftWidth: 3,
  },
  bottomRight: {
    bottom: 0,
    right: 0,
    borderBottomWidth: 3,
    borderRightWidth: 3,
  },
});
