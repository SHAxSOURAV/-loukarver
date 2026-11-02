import React, { useState } from 'react';
import { View, StyleSheet, ActivityIndicator, Pressable, Platform } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { WebView } from 'react-native-webview';
import { useNavigation, useRoute, RouteProp } from '@react-navigation/native';
import { RootStackParamList } from '../types';
import { Colors } from '../constants/colors';
import { AppText } from '../components/ui/AppText';

// Use the backend URL from env, fallback to localhost
const API_BASE = process.env.EXPO_PUBLIC_BACKEND_URL || 'http://localhost:8002';

type LegalScreenRouteProp = RouteProp<RootStackParamList, 'Legal'>;

export const LegalScreen: React.FC = () => {
  const navigation = useNavigation();
  const route = useRoute<LegalScreenRouteProp>();
  const [loading, setLoading] = useState(true);

  // Default to 'privacy' if type is not provided
  const type = route.params?.type || 'privacy';
  const url = `${API_BASE}/legal/${type}`;

  const title = type === 'privacy' ? 'Privacy Policy' : 'Terms of Conditions';

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.header}>
        <Pressable onPress={() => navigation.goBack()} style={styles.backButton}>
          <AppText variant="mono" color={Colors.accent} style={{ fontSize: 12 }}>
            ← BACK
          </AppText>
        </Pressable>
        <AppText variant="smallCaps" color={Colors.ink}>{title}</AppText>
        <View style={{ width: 60 }} />
      </View>
      
      <View style={styles.container}>
        {Platform.OS === 'web' ? (
          <iframe 
            src={url} 
            style={{ flex: 1, width: '100%', height: '100%', border: 'none' }}
            onLoad={() => setLoading(false)}
          />
        ) : (
          <WebView
            source={{ uri: url }}
            style={{ flex: 1, backgroundColor: Colors.bone }}
            onLoadEnd={() => setLoading(false)}
            showsVerticalScrollIndicator={false}
          />
        )}
        
        {loading && (
          <View style={styles.loader}>
            <ActivityIndicator size="large" color={Colors.accent} />
          </View>
        )}
      </View>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: Colors.bone,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingVertical: 15,
    borderBottomWidth: 1,
    borderBottomColor: Colors.rule,
  },
  backButton: {
    paddingVertical: 5,
    width: 60,
  },
  container: {
    flex: 1,
    position: 'relative',
  },
  loader: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: Colors.bone,
  },
});

export default LegalScreen;
