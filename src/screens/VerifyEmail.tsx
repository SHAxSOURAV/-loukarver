import { SafeAreaView } from 'react-native-safe-area-context';
import React, { useState } from 'react';
import { View, StyleSheet, Alert, Pressable, Platform } from 'react-native';
import { KeyboardAwareScrollView } from 'react-native-keyboard-controller';
import { useNavigation, useRoute, RouteProp, NavigationProp } from '@react-navigation/native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Colors } from '../constants/colors';
import { AppText } from '../components/ui/AppText';
import { AppButton } from '../components/ui/AppButton';
import { AppTextInput } from '../components/ui/AppTextInput';
import { RootStackParamList } from '../types';
import { verifyEmail, resendOtp } from '../services/authApi';

type VerifyEmailRouteProp = RouteProp<RootStackParamList, 'VerifyEmail'>;

const VerifyEmail = () => {
  const [otp, setOtp] = useState('');
  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const navigation = useNavigation<NavigationProp<RootStackParamList>>();
  const route = useRoute<VerifyEmailRouteProp>();
  const email = route.params.email;



  const handleVerify = async () => {
    setErrorMsg('');
    const cleanEmail = (email || '').trim().toLowerCase();
    const cleanOtp = otp.trim();
    if (!cleanOtp) {
      setErrorMsg('Please enter the verification code.');
      return;
    }
    try {
      setLoading(true);
      const data = await verifyEmail(cleanEmail, cleanOtp);
      await AsyncStorage.setItem('access_token', data.access_token);
      await AsyncStorage.setItem('refresh_token', data.refresh_token);

      const { clearMeCache, getMe } = require('../services/authApi');
      const api = require('../services/api').default;
      api.defaults.headers.common['Authorization'] = `Bearer ${data.access_token}`;
      clearMeCache();

      try {
        const Constants = require('expo-constants').default;
        const ExecutionEnvironment = require('expo-constants').ExecutionEnvironment;
        const isExpoGo = Constants.executionEnvironment === ExecutionEnvironment?.StoreClient || Constants.appOwnership === 'expo';
        
        let uid = data?.user?.id || data?.user?._id;
        if (!uid) {
          const user = await getMe(true);
          uid = user?.id || user?._id;
        }
        if (uid && Platform.OS !== 'web' && !isExpoGo) {
          const { OneSignal } = require('react-native-onesignal');
          OneSignal.login(String(uid));
        }
      } catch (e) {
        console.log("Failed to login to OneSignal in VerifyEmail:", e);
      }

      navigation.reset({
        index: 0,
        routes: [{ name: 'ModeSelector' }],
      });
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || error.message || 'Verification failed.';
      setErrorMsg(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    setErrorMsg('');
    try {
      setResending(true);
      await resendOtp(email);
      Alert.alert('Code Sent', 'A new verification code has been sent to your email.');
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to resend code.';
      setErrorMsg(errorMessage);
    } finally {
      setResending(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe}>
        <KeyboardAwareScrollView
          contentContainerStyle={[
            styles.container,
            { paddingBottom: 40 }
          ]}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
          bounces={false}
          bottomOffset={20}
        >
          <View style={styles.content}>
            <AppText variant="smallCaps" color={Colors.accent} style={{ marginBottom: 14 }}>
              ALMOST THERE
            </AppText>
            <AppText variant="display" size={42} style={{ lineHeight: 42, marginBottom: 14 }}>
              Verify Email
            </AppText>
            <AppText variant="serifItalic" size={18} color={Colors.muted} style={{ marginBottom: 36, lineHeight: 27 }}>
              We sent a 6-digit code to {email}.
            </AppText>

            <View style={{ marginBottom: 20 }}>
              <AppTextInput
                placeholder="000000"
                value={otp}
                onChangeText={(t) => { setOtp(t); setErrorMsg(''); }}
                keyboardType="number-pad"
                maxLength={6}
                returnKeyType="go"
                onSubmitEditing={handleVerify}
              />
              {errorMsg ? (
                <AppText color="red" style={{ marginTop: 8, fontSize: 13 }}>
                  {errorMsg}
                </AppText>
              ) : null}
            </View>
          </View>

          <View style={styles.actions}>
            <AppButton variant="solid" size="lg" onPress={handleVerify} disabled={loading} style={{ width: '100%', marginBottom: 16 }}>
              {loading ? 'Verifying...' : 'Verify →'}
            </AppButton>
            
            <Pressable onPress={handleResend} disabled={resending} style={{ paddingVertical: 12 }}>
              <AppText variant="smallCaps" color={Colors.ink} style={{ textAlign: 'center' }}>
                Didn't receive it? <AppText variant="smallCaps" color={Colors.accent}>{resending ? 'Sending...' : 'Resend Code'}</AppText>
              </AppText>
            </Pressable>
          </View>
        </KeyboardAwareScrollView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Colors.bone },
  container: { flexGrow: 1, paddingHorizontal: 32, paddingTop: 20, justifyContent: 'space-between' },
  content: { flex: 1, justifyContent: 'center', minHeight: 320 },
  actions: { paddingTop: 20, paddingBottom: 20 },
});

export default VerifyEmail;
