import AsyncStorage from '@react-native-async-storage/async-storage';

const PREFIX = 'avc-';

export const StorageService = {
  async get<T>(key: string): Promise<T | null> {
    try {
      const raw = await AsyncStorage.getItem(PREFIX + key);
      if (raw === null) return null;
      return JSON.parse(raw) as T;
    } catch {
      return null;
    }
  },

  async set<T>(key: string, value: T): Promise<boolean> {
    try {
      await AsyncStorage.setItem(PREFIX + key, JSON.stringify(value));
      return true;
    } catch {
      return false;
    }
  },

  async delete(key: string): Promise<boolean> {
    try {
      await AsyncStorage.removeItem(PREFIX + key);
      return true;
    } catch {
      return false;
    }
  },

  async clear(): Promise<void> {
    try {
      const keys = await AsyncStorage.getAllKeys();
      const appKeys = keys.filter(k => k.startsWith(PREFIX));
      await AsyncStorage.multiRemove(appKeys);
    } catch {
      // silent
    }
  },
};