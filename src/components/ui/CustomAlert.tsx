import React, { useState, useEffect } from 'react';
import { View, Modal, StyleSheet, DeviceEventEmitter } from 'react-native';
import { AppText } from './AppText';
import { Colors } from '../../constants/colors';
import { AppButton } from './AppButton';

export interface AlertButton {
  text: string;
  onPress?: () => void;
  style?: 'default' | 'cancel' | 'destructive';
}

interface AlertConfig {
  title: string;
  message?: string;
  buttons?: AlertButton[];
}

export const CustomAlert = () => {
  const [visible, setVisible] = useState(false);
  const [config, setConfig] = useState<AlertConfig | null>(null);

  useEffect(() => {
    const sub = DeviceEventEmitter.addListener('SHOW_CUSTOM_ALERT', (alertConfig: AlertConfig) => {
      setConfig(alertConfig);
      setVisible(true);
    });
    return () => sub.remove();
  }, []);

  const handlePress = (button?: AlertButton) => {
    setVisible(false);
    setTimeout(() => {
      if (button?.onPress) {
        button.onPress();
      }
    }, 150); // slight delay to allow modal close animation
  };

  if (!config) return null;

  const buttons = config.buttons || [{ text: 'OK' }];

  return (
    <Modal visible={visible} transparent animationType="fade">
      <View style={styles.overlay}>
        <View style={styles.alertBox}>
          <AppText variant="heading" size={20} color={Colors.ink} style={styles.title}>
            {config.title}
          </AppText>
          {config.message && (
            <AppText color={Colors.ink} style={styles.message}>
              {config.message}
            </AppText>
          )}

          <View style={styles.buttonContainer}>
            {buttons.map((btn, index) => {
              const isDestructive = btn.style === 'destructive';
              const isCancel = btn.style === 'cancel';
              
              if (buttons.length === 1) {
                // Single button layout
                return (
                  <AppButton
                    key={index}
                    variant={isDestructive ? 'solid' : 'solid'}
                    full
                    style={isDestructive ? { backgroundColor: '#D9534F' } : { backgroundColor: Colors.ink }}
                    onPress={() => handlePress(btn)}
                  >
                    {btn.text}
                  </AppButton>
                );
              }

              // Multiple buttons layout
              return (
                <AppButton
                  key={index}
                  variant={isCancel ? 'outline' : 'solid'}
                  style={{
                    flex: 1,
                    ...(isDestructive ? { backgroundColor: '#D9534F' } : !isCancel ? { backgroundColor: Colors.ink } : {})
                  }}
                  onPress={() => handlePress(btn)}
                >
                  {btn.text}
                </AppButton>
              );
            })}
          </View>
        </View>
      </View>
    </Modal>
  );
};

CustomAlert.alert = (title: string, message?: string, buttons?: AlertButton[]) => {
  DeviceEventEmitter.emit('SHOW_CUSTOM_ALERT', { title, message, buttons });
};

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 24,
  },
  alertBox: {
    backgroundColor: Colors.cream,
    borderRadius: 16,
    padding: 24,
    width: '100%',
    maxWidth: 400,
    elevation: 5,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.15,
    shadowRadius: 12,
  },
  title: {
    marginBottom: 12,
    textAlign: 'center',
  },
  message: {
    textAlign: 'center',
    marginBottom: 24,
    lineHeight: 22,
  },
  buttonContainer: {
    flexDirection: 'row',
    gap: 12,
    justifyContent: 'center',
  },
  flexButton: {
    flex: 1,
  },
});
